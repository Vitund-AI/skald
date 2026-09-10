"""HTTP API against a live server on a random port, plus daemon management."""
import json
import os
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from skald import server as srv
from skald.registry import UserConfig, ensure_token, read_token, rotate_token

from .helpers import SkaldTestCase, git


class ServerTestCase(SkaldTestCase):
    def setUp(self):
        super().setUp()
        self.token = ensure_token(self.home)
        self.httpd = srv.SkaldServer(("127.0.0.1", 0), home=self.home, quiet=True)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        t.start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def call(self, method, path, body=None, headers=None, auth=True):
        data = json.dumps(body).encode() if body is not None else None
        req = Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if auth:
            req.add_header("Authorization", f"Bearer {self.token}")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urlopen(req) as res:
                raw = res.read()
                return res.status, (json.loads(raw) if raw else None)
        except HTTPError as e:
            raw = e.read()
            return e.code, (json.loads(raw) if raw else None)


class TestAPI(ServerTestCase):
    def test_index_health_projects_404(self):
        with urlopen(self.base + "/") as res:
            self.assertEqual(res.status, 200)
            self.assertIn(b"<title>Skald</title>", res.read())
        status, data = self.call("GET", "/api/health")
        self.assertEqual((status, data["ok"]), (200, True))
        status, data = self.call("GET", "/api/projects")
        self.assertEqual([p["name"] for p in data["projects"]], ["alpha"])
        self.assertIn("stale_days", data["settings"])
        self.assertEqual(self.call("GET", "/nope")[0], 404)
        self.assertEqual(self.call("GET", "/api/nope")[0], 404)
        self.assertEqual(self.call("GET", "/api/projects/nope/board")[0], 404)
        with urlopen(self.base + "/favicon.ico") as res:
            self.assertEqual(res.status, 204)

    def test_help_reference_matches_parser(self):
        from skald.cli import build_parser, command_reference

        status, data = self.call("GET", "/api/help")
        self.assertEqual(status, 200)
        names = [c["name"] for c in data["commands"]]
        parser_names = [n for a in build_parser()._actions if hasattr(a, "choices") and isinstance(a.choices, dict) for n in a.choices]
        self.assertEqual(names, [n for n in parser_names if n != "mv"])
        self.assertIn("move", names)
        self.assertNotIn("mv", names)  # hidden alias
        self.assertEqual(data["commands"], command_reference())
        new = next(c for c in data["commands"] if c["name"] == "new")
        self.assertEqual(new["help"], "create a story")
        self.assertTrue(new["usage"].startswith("skald new "))
        self.assertNotIn("[-h]", new["usage"])
        flags = [a["flags"][0] for a in new["arguments"]]
        self.assertIn("title", flags)
        self.assertIn("--tags TAGS", flags)
        server = next(c for c in data["commands"] if c["name"] == "server")
        self.assertEqual([s["name"] for s in server["subcommands"]], ["server start", "server stop", "server status", "server token"])
        self.assertTrue(all(s["help"] for s in server["subcommands"]))
        render = next(c for c in data["commands"] if c["name"] == "render")
        fmt = next(a for a in render["arguments"] if a["flags"][0].startswith("--format"))
        self.assertEqual(fmt["choices"], ["md", "html"])

    def test_crud_flow(self):
        P = "/api/projects/alpha"
        status, data = self.call("POST", f"{P}/stories", {"title": "First", "tags": ["x"], "body": "- [ ] a\n"})
        self.assertEqual(status, 201)
        a = data["story"]["id"]
        self.assertEqual(data["story"]["checklist"], {"done": 0, "total": 1})
        status, data = self.call("POST", f"{P}/stories", {"title": "Second", "status": "ready", "blocked_by": [a]})
        b = data["story"]["id"]
        self.assertTrue(data["story"]["blocked"])
        self.assertEqual(len(data["warnings"]), 1)

        status, board = self.call("GET", f"{P}/board")
        self.assertEqual(status, 200)
        self.assertEqual(board["facets"], {})
        self.assertEqual([c["key"] for c in board["columns"]][0], "backlog")
        self.assertEqual([s["id"] for s in board["stories"]], [a, b])
        self.assertEqual(board["stories"][1]["deps"][0]["state"], "backlog")
        self.assertEqual(board["identity"], "Alpha Tester")
        self.assertTrue(board["git"]["available"])
        self.assertTrue(len(board["git"]["changes"]) >= 2)
        version = board["version"]
        status, v = self.call("GET", f"{P}/version")
        self.assertEqual(v["version"], version)

        status, one = self.call("GET", f"{P}/stories/{a[:4]}")
        self.assertEqual(one["body"], "## Requirements\n\n- [ ] a\n")

        status, data = self.call("PATCH", f"{P}/stories/{a}", {"status": "ready", "order": [a, b]})
        self.assertEqual(data["story"]["rank"], 10)
        status, board = self.call("GET", f"{P}/board")
        self.assertEqual([(s["id"], s["rank"]) for s in board["stories"]], [(a, 10), (b, 20)])
        self.assertNotEqual(board["version"], version)

        status, data = self.call("PATCH", f"{P}/stories/{b}", {"status": "in_progress", "tags": ["y", "epic:one"], "assignee": "me"})
        self.assertEqual((data["story"]["tags"], data["story"]["assignee"]), (["epic:one", "y"], "me"))
        status, board = self.call("GET", f"{P}/board")
        self.assertEqual(board["facets"]["epic"]["one"]["total"], 1)
        self.assertIn("unmet dependencies", data["warnings"][0])
        self.assertEqual(self.call("PATCH", f"{P}/stories/{b}", {"bogus": 1})[0], 400)
        self.assertEqual(self.call("PATCH", f"{P}/stories/{b}", {"status": "bogus"})[0], 400)

        status, data = self.call("PUT", f"{P}/stories/{a}/body", {"body": "edited\n", "base_sha256": one["body_sha256"]})
        self.assertEqual(status, 200)
        status, data = self.call("PUT", f"{P}/stories/{a}/body", {"body": "stale\n", "base_sha256": one["body_sha256"]})
        self.assertEqual(status, 409)

        status, data = self.call("POST", f"{P}/stories/{a}/notes", {"text": "hello"})
        self.assertEqual(status, 201)
        self.assertIn("## [Alpha Tester] ", data["body"])
        status, data = self.call("POST", f"{P}/stories/{a}/notes", {"text": "hi", "author": "bot"})
        self.assertIn("## [bot] ", data["body"])
        self.assertEqual(self.call("POST", f"{P}/stories/{a}/notes", {"text": ""})[0], 400)

        status, data = self.call("POST", f"{P}/stories/{a}/claim", {})
        self.assertEqual((data["story"]["assignee"], data["story"]["status"]), ("Alpha Tester", "in_progress"))

        status, data = self.call("GET", f"{P}/stories/{a}/history")
        self.assertEqual((data["history"], data["commits"]), ([], []))
        self.assertEqual(self.call("DELETE", f"{P}/stories/{a}")[0], 409)
        self.assertEqual(self.call("DELETE", f"{P}/stories/{a}?force=1")[0], 204)
        self.assertEqual(self.call("GET", f"{P}/stories/{a}")[0], 404)

    def test_git_endpoints(self):
        P = "/api/projects/alpha"
        self.call("POST", f"{P}/stories", {"title": "x"})
        status, info = self.call("GET", f"{P}/git")
        self.assertTrue(info["available"])
        self.assertFalse(info["push_enabled"])
        self.assertTrue(any(c["path"].endswith(".md") for c in info["changes"]))
        status, data = self.call("POST", f"{P}/git/commit", {"message": "from board", "push": True})
        self.assertEqual(status, 200)
        self.assertFalse(data["pushed"])  # push disabled in user config
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s").strip(), "from board")
        status, info = self.call("GET", f"{P}/git")
        self.assertEqual(info["changes"], [])
        status, data = self.call("POST", f"{P}/git/commit", {})
        self.assertEqual(status, 500)
        self.assertIn("nothing to commit", data["error"])
        UserConfig(self.home).set("author", "Board User")
        self.call("POST", f"{P}/stories", {"title": "y"})
        status, board = self.call("GET", f"{P}/board")
        self.assertEqual(board["identity"], "Board User")

    def test_ready_across_projects_and_archive(self):
        self.make_repo("beta")
        self.call("POST", "/api/projects/alpha/stories", {"title": "a", "status": "ready"})
        status, data = self.call("POST", "/api/projects/beta/stories", {"title": "b", "status": "ready"})
        b = data["story"]["id"]
        status, data = self.call("GET", "/api/ready")
        self.assertEqual(sorted(s["project"] for s in data["stories"]), ["alpha", "beta"])
        self.call("PATCH", f"/api/projects/beta/stories/{b}", {"status": "done"})
        status, data = self.call("POST", "/api/projects/beta/archive", {})
        self.assertEqual(data["archived"], [b])
        status, data = self.call("POST", "/api/projects/alpha/stories", {"title": "x", "status": "done"})
        x = data["story"]["id"]
        status, data = self.call("POST", "/api/projects/alpha/stories", {"title": "y", "status": "ready"})
        y = data["story"]["id"]
        self.assertEqual(self.call("POST", "/api/projects/alpha/archive", {"ids": [x, y]})[0], 400)
        self.assertEqual(self.call("POST", "/api/projects/alpha/archive", {"ids": "x"})[0], 400)
        status, data = self.call("POST", "/api/projects/alpha/archive", {"ids": [x]})
        self.assertEqual((status, data["archived"]), (200, [x]))
        status, data = self.call("GET", "/api/projects/beta/templates")
        self.assertEqual(data["templates"], [])

    def test_bad_json(self):
        req = Request(self.base + "/api/projects/alpha/stories", data=b"{not json", method="POST",
                      headers={"Authorization": f"Bearer {self.token}"})
        req.add_header("Content-Type", "application/json")
        with self.assertRaises(HTTPError) as cm:
            urlopen(req)
        self.assertEqual(cm.exception.code, 400)

    def test_board_reports_corrupt_files(self):
        self.write_raw("bad000-x.md", "nope")
        status, board = self.call("GET", "/api/projects/alpha/board")
        self.assertEqual(len(board["warnings"]), 1)


class TestDaemon(SkaldTestCase):
    def test_start_status_stop(self):
        self.assertIsNone(srv.server_status(self.home))
        state = srv.start_server(self.home, "127.0.0.1", 0)
        try:
            self.assertTrue(state["port"] > 0)
            self.assertEqual(srv.server_status(self.home)["pid"], state["pid"])
            again = srv.start_server(self.home, "127.0.0.1", 0)
            self.assertEqual(again["pid"], state["pid"])
            self.assertIsNotNone(srv.health("127.0.0.1", state["port"]))
            code, out, _ = self.run_cli("server", "status")
            self.assertEqual(code, 0)
            self.assertIn(f"pid {state['pid']}", out)
        finally:
            self.assertTrue(srv.stop_server(self.home))
        deadline = time.time() + 5
        while time.time() < deadline and srv.pid_alive(state["pid"]):
            time.sleep(0.1)
        self.assertFalse(srv.pid_alive(state["pid"]))
        self.assertIsNone(srv.server_status(self.home))
        self.assertFalse(srv.stop_server(self.home))
        code, out, _ = self.run_cli("server", "status")
        self.assertEqual((code, out.strip()), (1, "not running"))

    def test_stale_state_file_is_ignored(self):
        self.home.mkdir(parents=True, exist_ok=True)
        srv.state_path(self.home).write_text(json.dumps({"pid": 999999999, "host": "127.0.0.1", "port": 1}))
        self.assertIsNone(srv.server_status(self.home))


class TestEvents(ServerTestCase):
    def test_event_stream_reports_changes(self):
        import socket

        srv.SSE_INTERVAL = 0.05
        self.addCleanup(setattr, srv, "SSE_INTERVAL", 0.5)
        host, port = self.httpd.server_address
        sock = socket.create_connection((host, port), timeout=5)
        sock.sendall(f"GET /api/projects/alpha/events HTTP/1.1\r\nHost: 127.0.0.1\r\nAuthorization: Bearer {self.token}\r\n\r\n".encode())
        buf = b""
        while b"event: hello" not in buf:
            buf += sock.recv(4096)
        self.assertIn(b"text/event-stream", buf)
        self.call("POST", "/api/projects/alpha/stories", {"title": "trigger"})
        while b"event: change" not in buf:
            buf += sock.recv(4096)
        self.assertIn(b'"version"', buf)
        sock.close()


class TestBranchAPI(ServerTestCase):
    def test_branches_and_readonly_board(self):
        P = "/api/projects/alpha"
        status, data = self.call("POST", f"{P}/stories", {"title": "base", "status": "ready"})
        a = data["story"]["id"]
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "checkout", "-qb", "feature")
        status, data = self.call("POST", f"{P}/stories", {"title": "feature only"})
        b = data["story"]["id"]
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "feature")
        git(self.repo, "checkout", "-q", "master")

        status, data = self.call("GET", f"{P}/branches")
        self.assertEqual((status, data["current"], data["elsewhere"]), (200, "master", [b]))
        feature = next(x for x in data["branches"] if x["name"] == "feature")
        self.assertEqual((feature["stories"], feature["only_there"], feature["differ"]), (2, 1, 0))

        status, board = self.call("GET", f"{P}/board?ref=feature")
        self.assertEqual((status, board["readonly"], board["ref"]), (200, True, "feature"))
        self.assertEqual(sorted(s["id"] for s in board["stories"]), sorted([a, b]))
        status, again = self.call("GET", f"{P}/board?ref=feature")
        self.assertEqual(again["version"], board["version"])  # cached by sha, stable
        status, one = self.call("GET", f"{P}/stories/{b}?ref=feature")
        self.assertEqual((status, one["ref"], one["title"]), (200, "feature", "feature only"))
        self.assertIn("body_sha256", one)
        self.assertEqual(self.call("GET", f"{P}/stories/{b}")[0], 404)
        self.assertEqual(self.call("GET", f"{P}/board?ref=nope")[0], 404)
        status, board = self.call("GET", f"{P}/board")
        self.assertNotIn("readonly", board)
        self.assertEqual([s["id"] for s in board["stories"]], [a])

    def test_checkouts_worktree_view_and_claims(self):
        P = "/api/projects/alpha"
        status, data = self.call("POST", f"{P}/stories", {"title": "shared", "status": "ready"})
        a = data["story"]["id"]
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        wt = self.tmp / "alpha-wt"
        git(self.repo, "worktree", "add", "-q", "-b", "feature", str(wt))

        status, cos = self.call("GET", f"{P}/checkouts")
        self.assertEqual(status, 200)
        self.assertEqual([(c["primary"], c["worktree"], c["branch"]) for c in cos["checkouts"]],
                         [(True, False, "master"), (False, True, "feature")])
        self.assertEqual(cos["current"], cos["checkouts"][0]["id"])
        wt_id = cos["checkouts"][1]["id"]
        self.assertNotIn("/", wt_id)

        # The worktree's board is its own working tree, editable; the primary is untouched.
        status, board = self.call("GET", f"{P}/board?checkout={wt_id}")
        self.assertEqual((status, board["checkout"]["primary"], board["git"]["branch"]), (200, False, "feature"))
        self.assertEqual(board["path"], str((wt / ".skald").resolve()))
        status, data = self.call("POST", f"{P}/stories/{a}/claim?checkout={wt_id}", {"author": "worker"})
        self.assertEqual(status, 200)
        self.assertEqual(self.call("GET", f"{P}/stories/{a}?checkout={wt_id}")[1]["assignee"], "worker")
        self.assertEqual(self.call("GET", f"{P}/stories/{a}")[1]["assignee"], "")
        status, cos = self.call("GET", f"{P}/checkouts")
        self.assertEqual(cos["checkouts"][1]["changes"], 1)
        # From the primary, the uncommitted claim in the worktree is a claim elsewhere.
        status, data = self.call("GET", f"{P}/branches")
        self.assertEqual(data["claims"][a], [{"branch": "feature", "assignee": "worker", "status": "in_progress",
                                             "checkout": str((wt / ".skald").resolve())}])
        # Ids only: an unknown id is 404, and a path is not an id.
        self.assertEqual(self.call("GET", f"{P}/board?checkout=nope")[0], 404)
        self.assertEqual(self.call("GET", f"{P}/board?checkout={wt / '.skald'}")[0], 404)
        status, cos = self.call("GET", f"{P}/checkouts?checkout={wt_id}")
        self.assertEqual(cos["current"], wt_id)


class TestHostPort(SkaldTestCase):
    def test_port_zero_is_not_unset(self):
        import argparse

        ws = self.workspace()
        ws.user.set("port", "9123")
        ws.user.set("host", "127.0.0.1")
        self.assertEqual(srv._host_port(ws, argparse.Namespace(host=None, port=None)), ("127.0.0.1", 9123))
        self.assertEqual(srv._host_port(ws, argparse.Namespace(host=None, port=0)), ("127.0.0.1", 0))
        self.assertEqual(srv._host_port(ws, argparse.Namespace(host="0.0.0.0", port=8000)), ("0.0.0.0", 8000))
        self.assertEqual(srv._host_port(ws, argparse.Namespace()), ("127.0.0.1", 9123))


class TestAuth(ServerTestCase):
    def test_token_required_except_health(self):
        self.assertEqual(self.call("GET", "/api/health", auth=False)[0], 200)
        status, data = self.call("GET", "/api/projects", auth=False)
        self.assertEqual(status, 401)
        self.assertIn("skald open", data["error"])
        self.assertEqual(self.call("GET", "/api/projects", auth=False, headers={"Authorization": "Bearer nope"})[0], 401)
        self.assertEqual(self.call("POST", "/api/projects/alpha/stories", {"title": "x"}, auth=False)[0], 401)
        self.assertEqual(self.call("GET", "/api/projects")[0], 200)
        with urlopen(self.base + "/") as res:  # the page itself is public; it shows the lock message
            self.assertEqual(res.status, 200)

    def test_session_cookie_flow(self):
        status, data = self.call("POST", "/api/session", {"token": "wrong"}, auth=False)
        self.assertEqual(status, 401)
        req = Request(self.base + "/api/session", data=json.dumps({"token": self.token}).encode(), method="POST",
                      headers={"Content-Type": "application/json"})
        with urlopen(req) as res:
            cookie = res.headers.get("Set-Cookie")
        self.assertIn("skald_session=", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        value = cookie.split(";")[0]
        self.assertEqual(self.call("GET", "/api/projects", auth=False, headers={"Cookie": value})[0], 200)
        req = Request(self.base + "/api/session", method="DELETE", headers={"Cookie": value})
        with urlopen(req) as res:
            self.assertIn("Max-Age=0", res.headers.get("Set-Cookie"))

    def test_host_header_must_be_local(self):
        status, data = self.call("GET", "/api/projects", headers={"Host": "evil.example.com"})
        self.assertEqual(status, 403)
        self.assertEqual(self.call("GET", "/api/projects", headers={"Host": "localhost:9"})[0], 200)
        self.assertEqual(self.call("GET", "/api/projects", headers={"Host": "127.0.0.1"})[0], 200)
        self.assertEqual(self.call("POST", "/api/session", {"token": self.token}, auth=False, headers={"Host": "evil.example.com"})[0], 403)

    def test_rotate_invalidates_and_cli_prints(self):
        old = self.token
        code, out, _ = self.run_cli("server", "token")
        self.assertEqual((code, out.strip()), (0, old))
        code, out, err = self.run_cli("server", "token", "--rotate")
        new = out.strip()
        self.assertNotEqual(new, old)
        self.assertEqual(read_token(self.home), new)
        self.assertEqual(self.call("GET", "/api/projects")[0], 401)  # old token in self.token
        self.assertEqual(self.call("GET", "/api/projects", auth=False, headers={"Authorization": f"Bearer {new}"})[0], 200)
        if os.name != "nt":
            self.assertEqual(oct(srv.token_path(self.home).stat().st_mode & 0o777), "0o600")

    def test_board_url_carries_key_in_fragment(self):
        url = srv.board_url("127.0.0.1", 8321, "abc", "alpha")
        self.assertEqual(url, "http://127.0.0.1:8321/?project=alpha#key=abc")
        self.assertEqual(srv.board_url("127.0.0.1", 8321, None), "http://127.0.0.1:8321/")
