"""``skald mcp``: expose the store as Model Context Protocol tools over stdio.

Newline-delimited JSON-RPC 2.0, as the MCP stdio transport specifies. Only
the ``tools`` capability is offered. Standard library only.

Register with Claude Code from inside a project:  ``claude mcp add skald -- skald mcp``
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable, Optional

from . import __version__
from .errors import SkaldError
from .registry import Workspace
from .store import Store, normalise_tags, split_ref

PROTOCOL_VERSION = "2024-11-05"


def _schema(props: dict, required: Optional[list] = None) -> dict:
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}


PROJECT_PROP = {"project": {"type": "string", "description": "Registered project name. Defaults to the project of the current directory."}}
ID_PROP = {"id": {"type": "string", "description": "Story id or unique prefix."}}
AS_PROP = {"as": {"type": "string", "description": "Who is acting (default: agent)."}}

TOOLS: list[dict] = [
    {"name": "skald_status", "description": "Project name, columns with counts, ready-and-unblocked count, uncommitted story files.",
     "inputSchema": _schema({**PROJECT_PROP})},
    {"name": "skald_columns", "description": "This project's columns with their roles and limits.",
     "inputSchema": _schema({**PROJECT_PROP})},
    {"name": "skald_list", "description": "List stories. Terminal columns are hidden unless all=true.",
     "inputSchema": _schema({**PROJECT_PROP,
                             "status": {"type": "string"}, "tag": {"type": "string"}, "assignee": {"type": "string"},
                             "unblocked": {"type": "boolean"}, "all": {"type": "boolean"}})},
    {"name": "skald_next", "description": "The first ready, unblocked story available to the caller, or null.",
     "inputSchema": _schema({**PROJECT_PROP, **AS_PROP})},
    {"name": "skald_show", "description": "One story with its body and dependency states.",
     "inputSchema": _schema({**PROJECT_PROP, **ID_PROP}, ["id"])},
    {"name": "skald_new", "description": "Create a story. Returns it.",
     "inputSchema": _schema({**PROJECT_PROP,
                             "title": {"type": "string"}, "status": {"type": "string"}, "body": {"type": "string"},
                             "tags": {"type": "array", "items": {"type": "string"}},
                             "blocked_by": {"type": "array", "items": {"type": "string"}, "description": "ids, or project:id"},
                             "assignee": {"type": "string"}, "template": {"type": "string"}}, ["title"])},
    {"name": "skald_move", "description": "Change a story's status. Warnings are advisory.",
     "inputSchema": _schema({**PROJECT_PROP, **ID_PROP, "status": {"type": "string"}}, ["id", "status"])},
    {"name": "skald_claim", "description": "Assign a story to the caller and move it into the first active column.",
     "inputSchema": _schema({**PROJECT_PROP, **ID_PROP, **AS_PROP}, ["id"])},
    {"name": "skald_note", "description": "Append a timestamped note to a story's body. kind=handoff for end-of-session state, decision, or blocker.",
     "inputSchema": _schema({**PROJECT_PROP, **ID_PROP, **AS_PROP, "text": {"type": "string"},
                             "kind": {"type": "string", "description": "handoff, decision, blocker, or another short word"}}, ["id", "text"])},
    {"name": "skald_context", "description": "Orientation for the caller: assigned stories with last notes, the next unblocked story, blocked ready stories, claims on other branches, uncommitted story files.",
     "inputSchema": _schema({**PROJECT_PROP, **AS_PROP})},
    {"name": "skald_resume", "description": "A story's requirements (the ## Requirements section when there is one), the other sections' headings and sizes, checklist and acceptance state, dependencies, decisions, and its latest handoff note. Pass section to read one section, or full for the whole body.",
     "inputSchema": _schema({**PROJECT_PROP, **ID_PROP, "section": {"type": "string"}, "full": {"type": "boolean"}}, ["id"])},
    {"name": "skald_set", "description": "Update title, rank, tags, blocked_by, or assignee.",
     "inputSchema": _schema({**PROJECT_PROP, **ID_PROP,
                             "title": {"type": "string"}, "rank": {"type": "integer"},
                             "tags": {"type": "array", "items": {"type": "string"}},
                             "blocked_by": {"type": "array", "items": {"type": "string"}},
                             "assignee": {"type": "string"}}, ["id"])},
    {"name": "skald_tag", "description": "Add and remove tags.",
     "inputSchema": _schema({**PROJECT_PROP, **ID_PROP,
                             "add": {"type": "array", "items": {"type": "string"}},
                             "remove": {"type": "array", "items": {"type": "string"}}}, ["id"])},
    {"name": "skald_block", "description": "Add and remove dependencies (ids, or project:id).",
     "inputSchema": _schema({**PROJECT_PROP, **ID_PROP,
                             "add": {"type": "array", "items": {"type": "string"}},
                             "remove": {"type": "array", "items": {"type": "string"}}}, ["id"])},
    {"name": "skald_check", "description": "Validate every story file. Returns problems and warnings.",
     "inputSchema": _schema({**PROJECT_PROP})},
]


class McpServer:
    def __init__(self, workspace: Optional[Workspace] = None):
        self.ws = workspace
        self.initialized = False

    # -- helpers ---------------------------------------------------------

    def _ws(self) -> Workspace:
        if self.ws is None:
            self.ws = Workspace()
        return self.ws

    def _store(self, args: dict) -> Store:
        return self._ws().current(args.get("project") or None)

    def _actor(self, args: dict) -> str:
        from .cli import cli_identity

        return cli_identity(args.get("as"))

    def _with_warnings(self, store: Store, story, warnings) -> dict:
        return {"story": store.story_dict(story), "warnings": list(warnings)}

    # -- tools -----------------------------------------------------------

    def tool_skald_status(self, args: dict) -> Any:
        from . import gitutil

        store = self._store(args)
        stories, warnings = store.load_all()
        idx = {s.id: s for s in stories}
        counts = {c.key: sum(1 for s in stories if s.status == c.key) for c in store.config.columns}
        repo = gitutil.root(store.dir)
        uncommitted = []
        if repo:
            try:
                uncommitted = [c["path"] for c in gitutil.changes(repo, str(store.dir.relative_to(repo)))]
            except Exception:
                uncommitted = []
        return {
            "project": store.name, "path": str(store.dir), "branch": gitutil.branch(repo) if repo else None,
            "columns": [dict(c.to_dict(), count=counts[c.key]) for c in store.config.columns],
            "ready_unblocked": sum(1 for s in stories if store.config.role(s.status) == "ready" and not store.unmet(s, idx)),
            "uncommitted": uncommitted, "warnings": warnings,
        }

    def tool_skald_columns(self, args: dict) -> Any:
        store = self._store(args)
        return [c.to_dict() for c in store.config.columns]

    def tool_skald_list(self, args: dict) -> Any:
        store = self._store(args)
        stories, _ = store.load_all()
        idx = {s.id: s for s in stories}
        rows = stories
        if args.get("status"):
            rows = [s for s in rows if s.status == args["status"]]
        elif not args.get("all"):
            rows = [s for s in rows if not store.config.is_terminal(s.status)]
        if args.get("tag"):
            rows = [s for s in rows if args["tag"].lower() in s.tags]
        if args.get("assignee"):
            rows = [s for s in rows if s.assignee == args["assignee"]]
        if args.get("unblocked"):
            rows = [s for s in rows if not store.unmet(s, idx)]
        return [store.story_dict(s, idx) for s in rows]

    def tool_skald_next(self, args: dict) -> Any:
        store = self._store(args)
        notes: list[str] = []
        s = store.next_story(for_author=self._actor(args), stale_days=self._ws().user.get("stale_days"),
                             elsewhere=store.claims_elsewhere(), warnings=notes)
        return {"story": store.story_dict(s, compact=True) if s else None, "warnings": notes}

    def tool_skald_show(self, args: dict) -> Any:
        store = self._store(args)
        story = store.get(args["id"])
        d = store.story_dict(story)
        d["body"] = story.body
        return d

    def tool_skald_new(self, args: dict) -> Any:
        store = self._store(args)
        story, warnings = store.create(
            args.get("title", ""), args.get("status"), args.get("tags", []), args.get("blocked_by", []),
            args.get("body", ""), args.get("assignee", ""), args.get("template"),
        )
        return self._with_warnings(store, story, warnings)

    def tool_skald_move(self, args: dict) -> Any:
        store = self._store(args)
        return self._with_warnings(store, *store.update(args["id"], status=args["status"]))

    def tool_skald_claim(self, args: dict) -> Any:
        store = self._store(args)
        return self._with_warnings(store, *store.claim(args["id"], self._actor(args), self._ws().user.get("stale_days"),
                                                       store.claims_elsewhere()))

    def tool_skald_context(self, args: dict) -> Any:
        from .cli import build_context

        store = self._store(args)
        return build_context(self._ws(), store, self._actor(args))

    def tool_skald_resume(self, args: dict) -> Any:
        import argparse

        from .cli import _resume_extras

        store = self._store(args)
        story = store.get(args["id"])
        idx = store.index()
        d = store.story_dict(story, idx, compact=True)
        notes = story.notes()
        d.update(_resume_extras(story, argparse.Namespace(section=args.get("section"), full=bool(args.get("full")))))
        d["deps"] = [x.to_dict() for x in store.dep_states(story, idx)]
        d["latest"] = story.last_note("handoff") or (notes[-1] if notes else None)
        d["decisions"] = [n for n in notes if n["kind"] == "decision"]
        d["blockers"] = [n for n in notes if n["kind"] == "blocker"]
        d["note_count"] = len(notes)
        return d

    def tool_skald_note(self, args: dict) -> Any:
        store = self._store(args)
        story = store.append_note(args["id"], args.get("text", ""), self._actor(args), args.get("kind"))
        d = store.story_dict(story)
        d["body"] = story.body
        return d

    def tool_skald_set(self, args: dict) -> Any:
        store = self._store(args)
        fields = {k: args[k] for k in ("title", "rank", "tags", "blocked_by", "assignee") if k in args}
        if not fields:
            raise SkaldError("nothing to set")
        return self._with_warnings(store, *store.update(args["id"], **fields))

    def tool_skald_tag(self, args: dict) -> Any:
        store = self._store(args)
        story = store.get(args["id"])
        tags = (set(story.tags) | set(normalise_tags(args.get("add", [])))) - set(normalise_tags(args.get("remove", [])))
        return self._with_warnings(store, *store.update(story.id, tags=sorted(tags)))

    def tool_skald_block(self, args: dict) -> Any:
        store = self._store(args)
        story = store.get(args["id"])
        current = set(story.blocked_by)
        for r in args.get("remove", []):
            project, sid = split_ref(r.lower())
            if project is None or project == store.name:
                current.discard(store.resolve(sid))
            else:
                current.discard(r.lower())
        current |= {a.lower() for a in args.get("add", [])}
        return self._with_warnings(store, *store.update(story.id, blocked_by=sorted(current)))

    def tool_skald_check(self, args: dict) -> Any:
        store = self._store(args)
        problems, warnings = store.check()
        return {"ok": not problems, "problems": problems, "warnings": warnings}

    # -- protocol --------------------------------------------------------

    def handle(self, message: dict) -> Optional[dict]:
        """Handle one JSON-RPC message. Returns a response, or None for notifications."""
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}
        is_notification = "id" not in message

        def result(payload):
            return None if is_notification else {"jsonrpc": "2.0", "id": msg_id, "result": payload}

        def error(code, text):
            return None if is_notification else {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": text}}

        if method == "initialize":
            self.initialized = True
            return result({
                "protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "skald", "version": __version__},
            })
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return result({})
        if method == "tools/list":
            return result({"tools": TOOLS})
        if method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments") or {}
            fn: Optional[Callable] = getattr(self, f"tool_{name}", None) if name.startswith("skald_") else None
            if fn is None:
                return error(-32602, f"unknown tool '{name}'")
            try:
                payload = fn(args)
                text = json.dumps(payload, indent=2)
                return result({"content": [{"type": "text", "text": text}], "isError": False})
            except SkaldError as e:
                return result({"content": [{"type": "text", "text": f"ERROR: {e}"}], "isError": True})
            except (KeyError, TypeError, ValueError) as e:
                return result({"content": [{"type": "text", "text": f"ERROR: bad arguments: {e}"}], "isError": True})
        if method and method.startswith("notifications/"):
            return None
        return error(-32601, f"method not found: {method}")

    def serve(self, inp=None, out=None) -> int:
        inp = inp or sys.stdin
        out = out or sys.stdout
        for line in inp:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                out.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}) + "\n")
                out.flush()
                continue
            if isinstance(message, list):
                responses = [r for r in (self.handle(m) for m in message if isinstance(m, dict)) if r is not None]
                if responses:
                    out.write(json.dumps(responses) + "\n")
                    out.flush()
                continue
            if not isinstance(message, dict):
                continue
            response = self.handle(message)
            if response is not None:
                out.write(json.dumps(response) + "\n")
                out.flush()
        return 0
