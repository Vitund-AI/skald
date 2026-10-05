"""The 1.x compatibility contract (SPEC, Compatibility): what scripts and agents build on stays put.

``tests/contract.json`` is the baseline. For every stable surface it holds the field paths
(``stories[].id``), names, or flags that 1.x promises. The test fails if any of them
disappears or is renamed; additions pass. After adding a field on purpose, record it with

    SKALD_CONTRACT_UPDATE=1 python -m unittest tests.test_contract

which rewrites the baseline only when nothing in it was lost.

Covered: the ``--json`` output of every CLI command that has one, ``export``, every CLI
command name and flag, MCP tool names and arguments (a new required argument is a break),
and the HTTP data plane (docs/api.md). Paths through maps keyed by data, such as story
ids or facet values, are collapsed to ``{}`` so the data never becomes part of the contract.
"""
import argparse
import json
import os
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from skald import cli, mcp
from skald import server as srv
from skald.registry import ensure_token

from .helpers import SkaldTestCase, git

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tests" / "contract.json"
UPDATE = os.environ.get("SKALD_CONTRACT_UPDATE") == "1"

# Paths whose keys are data (column keys, facet keys and values), not field names.
MAPS = {
    "status": {"counts", "lanes"},
    "facets": {"", "{}"},
    "epics": {"", "{}"},
    "export": {"[].facets"},
}
# Fields a stable route returns but docs/api.md marks *(internal)*.
EXCLUDE = {"http GET /api/projects": ("settings",)}
# The data-plane routes (tests/test_api_docs.py STABLE) and the output that pins each one.
HTTP_ROUTES = {
    ("GET", "/api/health"): "http GET /api/health",
    ("GET", "/api/projects"): "http GET /api/projects",
    ("GET", "/api/ready"): "http GET /api/ready",
    ("GET", "/api/projects/<p>/version"): "http GET version",
    ("GET", "/api/projects/<p>/events"): "http GET events hello",
    ("POST", "/api/projects/<p>/stories"): "http POST stories",
    ("GET", "/api/projects/<p>/stories/<id>"): "http GET story",
    ("PATCH", "/api/projects/<p>/stories/<id>"): "http PATCH story",
    ("PUT", "/api/projects/<p>/stories/<id>/body"): "http PUT body",
    ("POST", "/api/projects/<p>/stories/<id>/notes"): "http POST notes",
    ("POST", "/api/projects/<p>/stories/<id>/claim"): "http POST claim",
    ("DELETE", "/api/projects/<p>/stories/<id>"): None,  # 204, no body: the status is the contract
}


def shape_of(name: str, obj) -> set[str]:
    paths = shape(obj, frozenset(MAPS.get(name, ())))
    return {p for p in paths if not p.startswith(EXCLUDE.get(name, ("\0",)))}


def shape(obj, maps=frozenset(), prefix="") -> set[str]:
    out = set()
    if isinstance(obj, dict):
        if prefix in maps or (prefix == "" and "" in maps):
            key = f"{prefix}{{}}" if prefix else "{}"
            out.add(key)
            for v in obj.values():
                out |= shape(v, maps, key)
            return out
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            out.add(p)
            out |= shape(v, maps, p)
    elif isinstance(obj, list):
        for v in obj:
            out |= shape(v, maps, f"{prefix}[]")
    return out


class ContractFixture(SkaldTestCase):
    """One project rich enough that every optional field appears at least once."""

    def build(self):
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "root")
        self.root = git(self.repo, "rev-parse", "HEAD").strip()
        a = self.new("Login form", "--status", "ready", "--tags", "epic:auth,area:web,lane:ui",
                     "--body", "Build it.\n\n## Acceptance\n\n- [ ] renders\n- [x] styled\n\n## Changelog\n\nA login form.")
        b = self.new("Session cookie", "--status", "ready", "--blocked-by", a, "--tags", "epic:auth")
        c = self.new("Form validation", "--parent", a)
        d = self.new("Old work", "--status", "done", "--tags", "release:9.9.9")
        self.run_cli("note", b, "Cookie or token?", "--as", "claude", "--kind", "question")
        self.run_cli("note", a, "Use the shared button", "--as", "claude", "--kind", "decision")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "stories", "-m", f"Skald-Story: {a}")
        self.run_cli("claim", c, "--as", "claude")
        self.run_cli("note", c, "Done: x. Next: y.", "--as", "claude", "--kind", "handoff")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "work", "-m", f"Skald-Story: {c}")
        self.ids = {"a": a, "b": b, "c": c, "d": d}

    def cli_json(self, *argv):
        code, out, err = self.run_cli(*argv)
        self.assertEqual(code, 0, f"skald {' '.join(argv)}: {err}")
        return json.loads(out)

    def cli_outputs(self) -> dict:
        a, c = self.ids["a"], self.ids["c"]
        out = {
            "ls": self.cli_json("ls", "--all", "--json"),
            "ls --compact": self.cli_json("ls", "--all", "--json", "--compact"),
            "next": self.cli_json("next", "--json"),
            "next --compact": self.cli_json("next", "--json", "--compact"),
            "context": self.cli_json("context", "--as", "claude", "--json"),
            "resume": self.cli_json("resume", c, "--json"),
            "show": self.cli_json("show", a, "--json"),
            "branches": self.cli_json("branches", "--json"),
            "log": self.cli_json("log", a, "--json"),
            "check": self.cli_json("check", "--json"),
            "migrate": self.cli_json("migrate", "--check", "--json"),
            "status": self.cli_json("status", "--json"),
            "commits": self.cli_json("commits", a, "--json"),
            "diff": self.cli_json("diff", "--since", self.root, "--json"),
            "activity": self.cli_json("activity", "--since", self.root, "--json"),
            "digest": self.cli_json("digest", "--since", "1w", "--json"),
            "changelog": self.cli_json("changelog", "--since", self.root, "--json"),
            "columns": self.cli_json("columns", "--json"),
            "facets": self.cli_json("facets", "--json"),
            "epics": self.cli_json("epics", "--json"),
            "projects": self.cli_json("projects", "--json"),
            "doctor": self.cli_json("doctor", "--json"),
            "export": self.cli_json("export", "--format", "json"),
            "audit": self.cli_json("audit", a, "--json"),
            "new": self.cli_json("new", "Late idea", "--json"),
        }
        return out

    def http_outputs(self) -> dict:
        token = ensure_token(self.home)
        httpd = srv.SkaldServer(("127.0.0.1", 0), home=self.home, quiet=True)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        base = f"http://127.0.0.1:{httpd.server_address[1]}"

        def call(method, path, body=None):
            data = json.dumps(body).encode() if body is not None else None
            req = Request(base + path, data=data, method=method)
            req.add_header("Authorization", f"Bearer {token}")
            if data is not None:
                req.add_header("Content-Type", "application/json")
            with urlopen(req) as res:
                raw = res.read()
                return json.loads(raw) if raw else None

        p = "/api/projects/alpha"
        a, b = self.ids["a"], self.ids["b"]
        story = call("GET", f"{p}/stories/{a}")
        out = {
            "http GET /api/health": call("GET", "/api/health"),
            "http GET /api/projects": call("GET", "/api/projects"),
            "http GET /api/ready": call("GET", "/api/ready"),
            "http GET version": call("GET", f"{p}/version"),
            "http POST stories": call("POST", f"{p}/stories", {"title": "From HTTP", "parent": a}),
            "http GET story": story,
            "http PATCH story": call("PATCH", f"{p}/stories/{b}", {"assignee": "bot"}),
            "http PUT body": call("PUT", f"{p}/stories/{a}/body",
                                  {"body": story["body"] + "\nMore.", "base_sha256": story["body_sha256"]}),
            "http POST notes": call("POST", f"{p}/stories/{b}/notes", {"text": "Token.", "question": 1}),
            "http POST claim": call("POST", f"{p}/stories/{b}/claim", {"author": "bot"}),
            "http GET events hello": self.first_event(httpd, token),
        }
        return out

    def first_event(self, httpd, token) -> dict:
        import socket

        host, port = httpd.server_address
        sock = socket.create_connection((host, port), timeout=5)
        self.addCleanup(sock.close)
        sock.sendall(f"GET /api/projects/alpha/events HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                     f"Authorization: Bearer {token}\r\n\r\n".encode())
        buf = b""
        while b"event: hello\ndata: " not in buf or not buf.rstrip().endswith(b"}"):
            buf += sock.recv(4096)
        return json.loads(buf.split(b"event: hello\ndata: ", 1)[1].split(b"\n", 1)[0])


def cli_surface() -> dict:
    """Every command and its flags, from the parser itself."""
    parser = cli.build_parser()
    out = {}

    def walk(p, name):
        for action in p._actions:
            if isinstance(action, argparse._SubParsersAction):
                for sub, sp in action.choices.items():
                    key = f"{name} {sub}".strip()
                    out[key] = sorted(o for a in sp._actions for o in a.option_strings if o.startswith("--"))
                    walk(sp, key)

    walk(parser, "")
    return out


def mcp_surface() -> dict:
    return {t["name"]: {"arguments": sorted(t["inputSchema"].get("properties", {})),
                        "required": sorted(t["inputSchema"].get("required", []))} for t in mcp.TOOLS}


def current_contract(fixture: ContractFixture) -> dict:
    fixture.build()
    outputs = {**fixture.cli_outputs(), **fixture.http_outputs()}
    return {"json": {k: sorted(shape_of(k, v)) for k, v in sorted(outputs.items())},
            "cli": cli_surface(), "mcp": mcp_surface()}


def breaks(baseline: dict, current: dict) -> list[str]:
    """Everything the baseline promises that the current build no longer keeps (only the parts ``current`` has)."""
    out = []
    for name, paths in (baseline.get("json", {}) if "json" in current else {}).items():
        lost = sorted(set(paths) - set(current["json"].get(name, [])))
        out += [f"{name}: field {p} is gone" for p in lost]
    for cmd, flags in (baseline.get("cli", {}) if "cli" in current else {}).items():
        if cmd not in current["cli"]:
            out.append(f"command `skald {cmd}` is gone")
            continue
        out += [f"skald {cmd}: flag {f} is gone" for f in sorted(set(flags) - set(current["cli"][cmd]))]
    for tool, spec in (baseline.get("mcp", {}) if "mcp" in current else {}).items():
        now = current["mcp"].get(tool)
        if now is None:
            out.append(f"MCP tool {tool} is gone")
            continue
        out += [f"MCP {tool}: argument {a} is gone" for a in sorted(set(spec["arguments"]) - set(now["arguments"]))]
        out += [f"MCP {tool}: argument {a} became required" for a in sorted(set(now["required"]) - set(spec["required"]))]
    return out


def load_baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}


class TestContract(ContractFixture):
    MESSAGE = "a 1.x promise was broken (SPEC, Compatibility); restore it, or deprecate it and keep it until 2.0"

    # The parser and the tool list need no fixture, so a crash in a command cannot hide a lost flag.
    def test_commands_and_flags_stay(self):
        self.assertEqual(breaks(load_baseline(), {"cli": cli_surface()}), [], self.MESSAGE)

    def test_mcp_tools_and_arguments_stay(self):
        self.assertEqual(breaks(load_baseline(), {"mcp": mcp_surface()}), [], self.MESSAGE)

    def test_nothing_promised_has_gone(self):
        current = current_contract(self)
        baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
        problems = breaks(baseline, current)
        if UPDATE and not problems:
            BASELINE.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        self.assertTrue(baseline or UPDATE, "no tests/contract.json; create it with SKALD_CONTRACT_UPDATE=1")
        self.assertEqual(problems, [], self.MESSAGE)

    def test_every_json_command_and_data_plane_route_is_covered(self):
        from .test_api_docs import STABLE

        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        covered = {name.split()[0] for name in baseline["json"] if not name.startswith("http ")}
        with_json = {cmd.split()[0] for cmd, flags in cli_surface().items() if "--json" in flags}
        self.assertEqual(sorted(with_json - covered), [],
                         "add these --json commands to ContractFixture.cli_outputs, then update the baseline")
        self.assertEqual(sorted(f"{m} {p}" for m, p in STABLE - set(HTTP_ROUTES)), [],
                         "add these data-plane routes to HTTP_ROUTES and http_outputs")
        pinned = {v for v in HTTP_ROUTES.values() if v}
        self.assertEqual(sorted(pinned - set(baseline["json"])), [], "update the baseline for these routes")
