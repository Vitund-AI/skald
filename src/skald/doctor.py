"""``skald doctor``: check the environment and the wiring, one line each with the fix.

Scope is everything ``check`` cannot: the prerequisites, the config file, the registry,
the server, and the agent hooks, much of it before a story file even loads (a broken
``config.json`` is the case nothing else catches, because the store never opens). It reads
state Skald already owns and never changes anything; it prints the fix to run. It ends by
running ``check`` so one command, and one exit code, covers setup and data.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from . import __version__, gitutil
from .config import FORMAT, ProjectConfig
from .errors import ConfigError
from .registry import Registry, config_home, find_skald_dir, token_path

MIN_PYTHON = (3, 10)

OK, INFO, WARN, FAIL = "ok", "info", "warn", "fail"


def _r(name: str, level: str, detail: str, fix: str = "") -> dict:
    return {"name": name, "level": level, "detail": detail, "fix": fix}


def _python(results: list[dict]) -> None:
    v = sys.version_info
    cur = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) < MIN_PYTHON:
        results.append(_r("python", FAIL, f"Python {cur}; Skald needs {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer",
                          f"run Skald under Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+"))
    else:
        results.append(_r("python", OK, f"Python {cur}"))


def _git(results: list[dict], repo: Optional[Path]) -> None:
    if not gitutil.available():
        results.append(_r("git", FAIL, "git is not on PATH", "install git"))
        return
    if repo is None:
        results.append(_r("git", WARN, "not inside a git repository",
                          "run Skald in a repository so stories are versioned with the code"))
        return
    results.append(_r("git", OK, f"repository at {repo}"))
    name, email = gitutil.user_name(repo), gitutil.user_email(repo)
    missing = [k for k, val in (("user.name", name), ("user.email", email)) if not val]
    if missing:
        results.append(_r("git identity", FAIL, f"git {' and '.join(missing)} not set; commits, release, and hooks will fail",
                          'git config user.name "You" && git config user.email you@example.com'))
    else:
        results.append(_r("git identity", OK, f"{name} <{email}>"))


def _project(results: list[dict], skald_dir: Optional[Path], reg: Registry) -> Optional[ProjectConfig]:
    if skald_dir is None:
        results.append(_r("project", FAIL, "no .skald directory found from here", "run `skald init` in a repository"))
        return None
    results.append(_r("project", OK, f".skald at {skald_dir}"))
    cfg = None
    try:
        cfg = ProjectConfig.load(skald_dir / "config.json")
        results.append(_r("config.json", OK, f"valid; {len(cfg.columns)} columns, format {FORMAT}"))
    except ConfigError as e:
        detail = str(e)
        fix = "upgrade skald-kanban" if "newer than this version" in detail else "fix config.json"
        results.append(_r("config.json", FAIL, detail, fix))
    stories = skald_dir / "stories"
    if not stories.is_dir():
        results.append(_r("stories dir", FAIL, f"{stories} is missing", "run `skald init`"))
    elif not os.access(stories, os.W_OK):
        results.append(_r("stories dir", FAIL, f"{stories} is not writable", "check the file permissions"))
    else:
        results.append(_r("stories dir", OK, "present and writable"))
    return cfg


def _registry(results: list[dict], skald_dir: Optional[Path], reg: Registry) -> None:
    entries = reg.entries()
    gone = [e for e in entries if not e["exists"]]
    for e in gone:
        results.append(_r("registry", WARN, f"project '{e['name']}' path is gone: {e['path']}",
                          f"skald projects rm {e['name']}"))
    seen: dict[str, str] = {}
    for e in entries:
        other = seen.get(e["path"])
        if other:
            results.append(_r("registry", WARN, f"projects '{other}' and '{e['name']}' point at the same path", ""))
        seen[e["path"]] = e["name"]
    if skald_dir is not None:
        name = reg.name_for_path(skald_dir)
        if name is None:
            results.append(_r("registry", WARN, "the .skald here is not a registered project",
                              "skald projects use ."))
        else:
            results.append(_r("registry", OK, f"registered as '{name}'; {len(entries)} project(s)"))
    elif not gone:
        results.append(_r("registry", OK, f"{len(entries)} project(s)"))


def _server(results: list[dict], home: Path) -> None:
    from . import server as srv

    state = srv.read_state(home)
    if state is None:
        results.append(_r("server", OK, "not running"))
    else:
        pid, host, port = state.get("pid", 0), state.get("host", "127.0.0.1"), state.get("port", 0)
        if not srv.pid_alive(int(pid or 0)):
            results.append(_r("server", WARN, f"server.json names pid {pid}, which is not running",
                              "skald server stop"))
        else:
            info = srv.health(host, int(port or 0))
            if info is None:
                results.append(_r("server", WARN, f"process {pid} is alive but not answering on {host}:{port}",
                                  "skald server stop, then skald open"))
            elif info.get("version") != __version__:
                results.append(_r("server", WARN, f"server is version {info.get('version')}, package is {__version__}",
                                  "restart it: skald server stop, then skald open"))
            else:
                results.append(_r("server", OK, f"running on {host}:{port} (version {__version__})"))
    tp = token_path(home)
    if tp.exists() and not sys.platform.startswith("win"):
        mode = tp.stat().st_mode
        if mode & 0o077:
            results.append(_r("token", WARN, f"{tp} is readable by others (mode {oct(mode & 0o777)})",
                              f"chmod 600 {tp}  (or skald server token --rotate)"))
        else:
            results.append(_r("token", OK, "board token is private"))


def _agent_wiring(results: list[dict], repo: Optional[Path], skald_dir: Optional[Path]) -> None:
    base = repo or (skald_dir.parent if skald_dir else None)
    if base is None:
        return
    settings = base / ".claude" / "settings.json"
    if not settings.exists():
        results.append(_r("claude hooks", WARN, "no .claude/settings.json; Claude Code is not wired up",
                          "skald hooks claude --install --as <name>"))
    else:
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
        except (ValueError, OSError) as e:
            results.append(_r("claude hooks", FAIL, f"{settings} is not valid JSON ({e})", "fix .claude/settings.json"))
            data = None
        if data is not None:
            cmds = [h.get("command", "") for entries in data.get("hooks", {}).values()
                    for entry in entries for h in entry.get("hooks", [])]
            skald_cmds = [c for c in cmds if c.startswith("skald ")]
            if not skald_cmds:
                results.append(_r("claude hooks", WARN, "Claude Code hooks are installed but none run skald",
                                  "skald hooks claude --install --as <name>"))
            elif not any("--as" in c for c in skald_cmds):
                results.append(_r("claude hooks", WARN, "the SessionStart hook has no --as; notes will be authored 'agent'",
                                  "skald hooks claude --install --as <name>"))
            else:
                results.append(_r("claude hooks", OK, "SessionStart runs skald with an author"))
    # The contract copies drift when skald is upgraded without re-running hooks.
    from .cli import agents_template, claude_skill

    for label, path, want in (("AGENTS.md", (skald_dir / "AGENTS.md") if skald_dir else None, agents_template()),
                              ("SKILL.md", base / ".claude" / "skills" / "skald" / "SKILL.md", claude_skill())):
        if path is None or not path.exists():
            continue
        try:
            current = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if current != want:
            results.append(_r("contract", WARN, f"{label} differs from this version's template",
                              "re-copy it: skald hooks claude --install (SKILL.md) or copy the template over .skald/AGENTS.md"))
        else:
            results.append(_r("contract", OK, f"{label} matches the template"))


def _context(results: list[dict], home: Path) -> None:
    where = []
    if os.environ.get("SKALD_HOME"):
        where.append(f"SKALD_HOME={os.environ['SKALD_HOME']}")
    if os.environ.get("SKALD_DIR"):
        where.append(f"SKALD_DIR={os.environ['SKALD_DIR']}")
    if os.environ.get("SKALD_AUTHOR"):
        where.append(f"SKALD_AUTHOR={os.environ['SKALD_AUTHOR']}")
    results.append(_r("home", INFO, f"config home {home}" + (f"; {', '.join(where)}" if where else "")))


def run(cwd: Optional[Path] = None) -> list[dict]:
    """Every check as ``{name, level, detail, fix}``. Never changes anything."""
    cwd = Path(cwd or Path.cwd())
    home = config_home()
    reg = Registry(home)
    skald_dir = find_skald_dir(cwd)
    repo = gitutil.root(cwd)
    results: list[dict] = []
    _context(results, home)
    _python(results)
    _git(results, repo)
    _project(results, skald_dir, reg)
    _registry(results, skald_dir, reg)
    _server(results, home)
    _agent_wiring(results, repo, skald_dir)
    return results
