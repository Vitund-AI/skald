"""The local HTTP server behind the board, plus background-server management."""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

from . import __version__, gitutil
from .errors import GitError, NotFoundError, SkaldError
from .registry import Registry, UserConfig, Workspace
from .store import Store, facets as compute_facets
from .util import sha256_text

SSE_INTERVAL = 0.5  # seconds between change checks on an open event stream


def index_html() -> str:
    from importlib import resources

    return resources.files("skald").joinpath("web/index.html").read_text(encoding="utf-8")


class SkaldServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, home: Optional[Path] = None, quiet: bool = True):
        super().__init__(addr, Handler)
        self.home = home
        self.quiet = quiet
        self._html: Optional[str] = None
        self._snapshots: dict = {}
        self._snap_lock = threading.Lock()

    def snapshot(self, store: Store, ref: str):
        """A read-only snapshot of ``store`` at ``ref``, cached by the commit it resolves to."""
        repo = gitutil.root(store.dir)
        if repo is None:
            raise SkaldError("this project is not inside a git repository")
        sha = gitutil.rev_parse(repo, ref)
        if sha is None:
            raise NotFoundError(f"unknown git ref '{ref}'")
        key = (str(store.dir), sha)
        with self._snap_lock:
            snap = self._snapshots.get(key)
        if snap is None:
            snap = store.snapshot(ref)
            with self._snap_lock:
                if len(self._snapshots) > 64:
                    self._snapshots.clear()
                self._snapshots[key] = snap
        return snap

    def workspace(self) -> Workspace:
        # A fresh workspace per request picks up projects registered or config edited since the last one.
        registry = Registry(self.home)
        return Workspace(registry, UserConfig(registry.home))

    def html(self) -> str:
        if self._html is None:
            self._html = index_html()
        return self._html


class Handler(BaseHTTPRequestHandler):
    server_version = f"Skald/{__version__}"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if not getattr(self.server, "quiet", True):
            super().log_message(fmt, *args)

    # -- plumbing --------------------------------------------------------

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, obj) -> None:
        self._send(status, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise SkaldError("request body is not valid JSON")
        if not isinstance(data, dict):
            raise SkaldError("request body must be a JSON object")
        return data

    def _route(self, method: str) -> None:
        try:
            url = urlparse(self.path)
            parts = [p for p in url.path.split("/") if p]
            query = parse_qs(url.query)
            self._dispatch(method, parts, query)
        except SkaldError as e:
            self._json(e.http_status, {"error": str(e)})
        except Exception as e:  # pragma: no cover - last resort
            self._json(500, {"error": f"internal error: {e}"})

    def do_GET(self):
        self._route("GET")

    def do_HEAD(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def do_PATCH(self):
        self._route("PATCH")

    def do_PUT(self):
        self._route("PUT")

    def do_DELETE(self):
        self._route("DELETE")

    # -- helpers ---------------------------------------------------------

    def _project(self, ws: Workspace, name: str) -> Store:
        store = ws.open(name)
        if store is None:
            raise NotFoundError(f"project '{name}' is not registered on this machine")
        return store

    def _identity(self, ws: Workspace, store: Store) -> str:
        from .cli import human_identity

        return human_identity(ws.user, gitutil.root(store.dir))

    def _story_json(self, ws: Workspace, store: Store, story, body: bool = False) -> dict:
        d = store.story_dict(story, None, ws.user.get("stale_days"))
        if body:
            d["body"] = story.body
            d["body_sha256"] = store.body_sha(story)
        return d

    def _git_info(self, store: Store) -> dict:
        repo = gitutil.root(store.dir)
        if repo is None:
            return {"available": False, "branch": None, "changes": []}
        try:
            rel = str(store.dir.relative_to(repo))
            changes = gitutil.changes(repo, rel)
        except (GitError, ValueError):
            changes = []
        return {"available": True, "branch": gitutil.branch(repo), "changes": changes}

    def _version_hash(self, store: Store) -> str:
        h = hashlib.sha1()
        for directory in (store.stories_dir, store.archive_dir):
            if directory.is_dir():
                for p in sorted(directory.iterdir()):
                    try:
                        st = p.stat()
                    except OSError:
                        continue
                    h.update(f"{p.name}:{st.st_mtime_ns}:{st.st_size};".encode())
        cfg = store.dir / "config.json"
        if cfg.exists():
            st = cfg.stat()
            h.update(f"config:{st.st_mtime_ns}:{st.st_size};".encode())
        return h.hexdigest()[:16]

    def _events(self, store: Store) -> None:
        """Server-sent events: one ``change`` event whenever any story file changes."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        last = self._version_hash(store)
        try:
            self.wfile.write(f"event: hello\ndata: {json.dumps({'version': last})}\n\n".encode())
            self.wfile.flush()
            ticks = 0
            while True:
                time.sleep(SSE_INTERVAL)
                ticks += 1
                current = self._version_hash(store)
                if current != last:
                    last = current
                    self.wfile.write(f"event: change\ndata: {json.dumps({'version': current})}\n\n".encode())
                    self.wfile.flush()
                elif ticks % 30 == 0:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    # -- routes ----------------------------------------------------------

    def _dispatch(self, method: str, parts: list[str], query: dict) -> None:
        if method == "GET" and parts in ([], ["index.html"]):
            self._send(200, self.server.html().encode("utf-8"), "text/html; charset=utf-8")
            return
        if parts == ["favicon.ico"]:
            self._send(204, b"", "image/x-icon")
            return
        if not parts or parts[0] != "api":
            self._json(404, {"error": "not found"})
            return
        rest = parts[1:]
        ws = self.server.workspace()

        if rest == ["health"] and method == "GET":
            self._json(200, {"ok": True, "version": __version__, "pid": os.getpid()})
            return

        if rest == ["projects"] and method == "GET":
            entries = ws.registry.entries()
            self._json(200, {"projects": entries, "settings": ws.user.all()})
            return

        if rest == ["ready"] and method == "GET":
            stores, warnings = ws.open_all()
            out = []
            for st in stores:
                stories, w = st.load_all()
                warnings.extend(w)
                idx = {s.id: s for s in stories}
                ready = set(st.config.keys_with_role("ready"))
                for s in stories:
                    if s.status in ready and not st.unmet(s, idx):
                        out.append(st.story_dict(s, idx, ws.user.get("stale_days")))
            self._json(200, {"stories": out, "warnings": warnings})
            return

        if len(rest) >= 2 and rest[0] == "projects":
            name, tail = rest[1], rest[2:]
            store = self._project(ws, name)

            ref = (query.get("ref") or [""])[0].strip()
            if tail == ["board"] and method == "GET" and ref:
                snap = self.server.snapshot(store, ref)
                stories, warnings = snap.load_all()
                idx = {s.id: s for s in stories}
                self._json(200, {
                    "project": store.name, "path": str(store.dir),
                    "columns": [c.to_dict() for c in snap.config.columns],
                    "stories": [snap.story_dict(s, idx) for s in stories],
                    "facets": compute_facets(stories, snap.config),
                    "warnings": warnings, "git": {"available": True, "branch": ref, "changes": []},
                    "identity": self._identity(ws, store), "settings": ws.user.all(),
                    "version": snap.sha, "readonly": True, "ref": ref, "sha": snap.sha,
                })
                return
            if tail == ["branches"] and method == "GET":
                repo = gitutil.root(store.dir)
                if repo is None:
                    self._json(200, {"available": False, "current": None, "branches": [], "elsewhere": []})
                    return
                current = gitutil.branch(repo)
                out, elsewhere, claims = [], set(), {}
                for b in gitutil.branches(repo):
                    snap = self.server.snapshot(store, b["name"])
                    diff = store.branch_diff(snap)
                    is_current = b["name"] == current
                    if not is_current:
                        elsewhere.update(x.id for x in diff["only_there"])
                        if not b["remote"]:
                            for st in snap.load_all()[0]:
                                if st.assignee and snap.config.role(st.status) == "active":
                                    claims.setdefault(st.id, []).append({"branch": b["name"], "assignee": st.assignee, "status": st.status})
                    out.append({
                        "name": b["name"], "sha": b["sha"][:7], "remote": b["remote"], "current": is_current,
                        "stories": len(snap.load_all(include_archived=True)[0]),
                        "only_there": len(diff["only_there"]), "only_here": len(diff["only_here"]),
                        "differ": len(diff["differ"]),
                    })
                self._json(200, {"available": True, "current": current, "branches": out, "elsewhere": sorted(elsewhere), "claims": claims})
                return
            if tail == ["board"] and method == "GET":
                stories, warnings = store.load_all()
                idx = {s.id: s for s in stories}
                git = self._git_info(store)
                self._json(200, {
                    "project": store.name,
                    "path": str(store.dir),
                    "columns": [c.to_dict() for c in store.config.columns],
                    "stories": [store.story_dict(s, idx, ws.user.get("stale_days")) for s in stories],
                    "facets": compute_facets(stories, store.config),
                    "warnings": warnings + ws.notices,
                    "git": git,
                    "identity": self._identity(ws, store),
                    "settings": ws.user.all(),
                    "version": self._version_hash(store),
                })
                return
            if tail == ["version"] and method == "GET":
                self._json(200, {"version": self._version_hash(store)})
                return
            if tail == ["events"] and method == "GET":
                self._events(store)
                return
            if tail == ["templates"] and method == "GET":
                self._json(200, {"templates": store.templates()})
                return
            if tail == ["archive"] and method == "POST":
                moved = store.archive()
                self._json(200, {"archived": [s.id for s in moved]})
                return
            if tail == ["git"] and method == "GET":
                info = self._git_info(store)
                info["push_enabled"] = bool(ws.user.get("push"))
                info["identity"] = self._identity(ws, store)
                self._json(200, info)
                return
            if tail == ["git", "commit"] and method == "POST":
                data = self._read_json()
                repo = gitutil.root(store.dir)
                if repo is None:
                    raise GitError("this project is not inside a git repository")
                from .cli import auto_render

                rel = str(store.dir.relative_to(repo))
                rendered = auto_render(store, repo)
                paths = [rel] + ([rendered] if rendered and not rendered.startswith(rel + "/") else [])
                changes = [c for p in paths for c in gitutil.changes(repo, p)]
                message = (data.get("message") or "").strip() or f"skald: update {len(changes)} story file(s)"
                sha = gitutil.commit_path(repo, paths, message)
                pushed, output = False, ""
                if data.get("push") and ws.user.get("push"):
                    output = gitutil.push(repo)
                    pushed = True
                self._json(200, {"sha": sha, "message": message, "pushed": pushed, "output": output})
                return
            if tail == ["stories"] and method == "POST":
                data = self._read_json()
                story, warnings = store.create(
                    data.get("title", ""), data.get("status"), data.get("tags", []),
                    data.get("blocked_by", []), data.get("body", ""), data.get("assignee", ""),
                    data.get("template"),
                )
                self._json(201, {"story": self._story_json(ws, store, story), "warnings": warnings})
                return
            if len(tail) >= 2 and tail[0] == "stories":
                ref, sub = tail[1], tail[2:]
                if not sub and method == "GET":
                    git_ref = (query.get("ref") or [""])[0].strip()
                    if git_ref:
                        snap = self.server.snapshot(store, git_ref)
                        story = snap.get(ref)
                        d = snap.story_dict(story)
                        d["body"] = story.body
                        d["body_sha256"] = sha256_text(story.body)
                        self._json(200, d)
                        return
                    story = store.get(ref)
                    self._json(200, self._story_json(ws, store, story, body=True))
                    return
                if not sub and method == "PATCH":
                    data = self._read_json()
                    allowed = {"title", "status", "rank", "tags", "blocked_by", "assignee", "order"}
                    unknown = set(data) - allowed
                    if unknown:
                        raise SkaldError(f"unknown fields: {', '.join(sorted(unknown))}")
                    story, warnings = store.update(ref, **data)
                    self._json(200, {"story": self._story_json(ws, store, story), "warnings": warnings})
                    return
                if not sub and method == "DELETE":
                    force = query.get("force", ["0"])[0] in ("1", "true", "yes")
                    store.delete(ref, force=force)
                    self._send(204, b"", "application/json")
                    return
                if sub == ["body"] and method == "PUT":
                    data = self._read_json()
                    story = store.write_body(ref, data.get("body"), data.get("base_sha256"))
                    self._json(200, self._story_json(ws, store, story, body=True))
                    return
                if sub == ["notes"] and method == "POST":
                    data = self._read_json()
                    author = (data.get("author") or "").strip() or self._identity(ws, store)
                    story = store.append_note(ref, data.get("text", ""), author)
                    self._json(201, self._story_json(ws, store, story, body=True))
                    return
                if sub == ["history"] and method == "GET":
                    story = store.get(ref)
                    repo = gitutil.root(store.dir)
                    entries = gitutil.log_file(repo, story.path) if repo else []
                    self._json(200, {"history": entries})
                    return
                if sub == ["claim"] and method == "POST":
                    data = self._read_json()
                    author = (data.get("author") or "").strip() or self._identity(ws, store)
                    story, warnings = store.claim(ref, author)
                    self._json(200, {"story": self._story_json(ws, store, story), "warnings": warnings})
                    return

        self._json(404, {"error": "not found"})


# --------------------------------------------------------------------------
# Running and managing the server
# --------------------------------------------------------------------------


def state_path(home: Path) -> Path:
    return home / "server.json"


def read_state(home: Path) -> Optional[dict]:
    p = state_path(home)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def health(host: str, port: int, timeout: float = 1.0) -> Optional[dict]:
    try:
        with urlopen(f"http://{host}:{port}/api/health", timeout=timeout) as res:
            return json.loads(res.read().decode("utf-8"))
    except (URLError, OSError, ValueError):
        return None


def _pid_alive_windows(pid: int) -> bool:  # pragma: no cover - exercised on Windows CI only
    import ctypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        # os.kill(pid, 0) would *terminate* the process on Windows.
        return _pid_alive_windows(pid)
    if hasattr(os, "waitpid"):
        try:
            reaped, _ = os.waitpid(pid, os.WNOHANG)  # reap it if it is our own finished child
            if reaped == pid:
                return False
        except ChildProcessError:
            pass
        except OSError:
            pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def serve(home: Path, host: str, port: int, open_browser: bool = False, quiet: bool = True) -> int:
    httpd = SkaldServer((host, port), home=home, quiet=quiet)
    actual_port = httpd.server_address[1]
    url = f"http://{host}:{actual_port}/"
    home.mkdir(parents=True, exist_ok=True)
    state_path(home).write_text(json.dumps({
        "pid": os.getpid(), "host": host, "port": actual_port, "started_at": time.time(), "version": __version__,
    }), encoding="utf-8")
    print(f"Skald board at {url}  (Ctrl+C to stop)", flush=True)

    def _stop(signum, frame):  # pragma: no cover - signal driven
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _stop)
        except (ValueError, OSError):  # pragma: no cover - not main thread / platform
            pass
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        httpd.server_close()
        try:
            current = read_state(home)
            if current and current.get("pid") == os.getpid():
                state_path(home).unlink()
        except OSError:
            pass
    return 0


def server_status(home: Path) -> Optional[dict]:
    """Return the running server's state, or None."""
    state = read_state(home)
    if not state:
        return None
    if not pid_alive(int(state.get("pid", 0))):
        return None
    if health(state["host"], state["port"]) is None:
        return None
    return state


def start_server(home: Path, host: str, port: int, log_path: Optional[Path] = None) -> dict:
    running = server_status(home)
    if running:
        return running
    home.mkdir(parents=True, exist_ok=True)
    log_path = log_path or home / "server.log"
    log = open(log_path, "ab")
    kwargs: dict = {}
    if sys.platform.startswith("win"):  # pragma: no cover
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    env = dict(os.environ)
    env["SKALD_HOME"] = str(home)
    # Make sure the child can import this very package, even from a source checkout.
    pkg_parent = str(Path(__file__).resolve().parent.parent)
    env["PYTHONPATH"] = pkg_parent + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.Popen(
        [sys.executable, "-m", "skald", "serve", "--host", host, "--port", str(port)],
        stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=env, close_fds=True, **kwargs,
    )
    log.close()
    deadline = time.time() + 5
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SkaldError(f"server exited immediately (exit {proc.returncode}); see {log_path}")
        state = read_state(home)
        if state and state.get("pid") == proc.pid and health(host, state["port"]):
            return state
        time.sleep(0.1)
    raise SkaldError(f"server did not come up within 5s; see {log_path}")


def stop_server(home: Path) -> bool:
    state = read_state(home)
    if not state:
        return False
    pid = int(state.get("pid", 0))
    if pid and pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        deadline = time.time() + 5
        while time.time() < deadline and pid_alive(pid):
            time.sleep(0.1)
    try:
        state_path(home).unlink()
    except OSError:
        pass
    return True


# --------------------------------------------------------------------------
# CLI entry points
# --------------------------------------------------------------------------


def _host_port(ws: Workspace, args) -> tuple[str, int]:
    host = getattr(args, "host", None) or ws.user.get("host")
    port = getattr(args, "port", None) or int(ws.user.get("port"))
    return host, port


def cmd_serve(ws: Workspace, args) -> int:
    host, port = _host_port(ws, args)
    return serve(ws.registry.home, host, port, open_browser=args.open)


def cmd_server(ws: Workspace, args) -> int:
    home = ws.registry.home
    if args.server_cmd == "start":
        host, port = _host_port(ws, args)
        state = start_server(home, host, port)
        print(f"server running at http://{state['host']}:{state['port']}/ (pid {state['pid']})")
        return 0
    if args.server_cmd == "stop":
        if stop_server(home):
            print("server stopped")
        else:
            print("server is not running")
        return 0
    if args.server_cmd == "status":
        state = server_status(home)
        if state:
            print(f"running at http://{state['host']}:{state['port']}/ (pid {state['pid']}, version {state.get('version', '?')})")
            return 0
        print("not running")
        return 1
    print("usage: skald server start|stop|status", file=sys.stderr)
    return 1


def cmd_open(ws: Workspace, store: Store) -> int:
    home = ws.registry.home
    state = server_status(home)
    if not state:
        state = start_server(home, ws.user.get("host"), int(ws.user.get("port")))
        print(f"started server at http://{state['host']}:{state['port']}/ (pid {state['pid']})")
    url = f"http://{state['host']}:{state['port']}/?project={store.name}"
    print(url)
    webbrowser.open(url)
    return 0
