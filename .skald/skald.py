#!/usr/bin/env python3
"""Skald: a file-system-native Kanban backlog for AI coding agents.

This single file is the whole tool: the agent CLI, the local HTTP server,
the embedded web board, and the embedded agent contract. It depends on the
Python standard library only (3.9+).

Usage:  python3 .skald/skald.py <command> [args]
        python3 .skald/skald.py --help
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

VERSION = "0.1.0"
STATUSES = ["backlog", "ready", "in_progress", "review", "done"]
WARN_ON = {"ready", "in_progress", "review", "done"}
KNOWN_FIELDS = ["title", "status", "rank", "tags", "blocked_by", "created_at", "updated_at"]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8321
RANK_STEP = 10

ID_RE = re.compile(r"^[0-9a-f]{6}$")
FILENAME_RE = re.compile(r"^([0-9a-f]{6})(?:-[a-z0-9-]*)?\.md$")
FM_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*): (.*)$")
CONFLICT_RE = re.compile(r"^(<{7}|={7}|>{7})( |$)", re.M)


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class SkaldError(Exception):
    exit_code = 1
    http_status = 400


class NotFoundError(SkaldError):
    http_status = 404


class CorruptStoryError(SkaldError):
    exit_code = 2
    http_status = 422


class ConflictError(SkaldError):
    http_status = 409


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def note_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def slugify(title: str) -> str:
    ascii_title = title.encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")
    return slug[:50].rstrip("-")


def git_root(start: Path | None = None) -> Path | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(start or Path.cwd()),
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if out.returncode != 0:
        return None
    return Path(out.stdout.strip()).resolve()


def default_skald_dir() -> Path:
    """Resolve the data directory. See SPEC.md section 2.2."""
    env = os.environ.get("SKALD_DIR")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve().parent
    if here.name == ".skald":
        return here
    root = git_root()
    if root:
        return root / ".skald"
    return here


def normalise_tags(tags) -> list[str]:
    if not isinstance(tags, (list, tuple)):
        raise SkaldError("tags must be a list of strings")
    out = set()
    for t in tags:
        if not isinstance(t, str):
            raise SkaldError("tags must be a list of strings")
        t = t.strip().lower()
        if t:
            out.add(t)
    return sorted(out)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".skald-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


# --------------------------------------------------------------------------
# Story model and file format
# --------------------------------------------------------------------------


class Story:
    __slots__ = ("id", "path", "fields", "body")

    def __init__(self, story_id: str, path: Path, fields: dict, body: str):
        self.id = story_id
        self.path = path
        self.fields = fields
        self.body = body

    @property
    def title(self) -> str:
        return self.fields["title"]

    @property
    def status(self) -> str:
        return self.fields["status"]

    @property
    def rank(self) -> int:
        return self.fields["rank"]

    @property
    def tags(self) -> list[str]:
        return self.fields["tags"]

    @property
    def blocked_by(self) -> list[str]:
        return self.fields["blocked_by"]

    @property
    def created_at(self) -> str:
        return self.fields["created_at"]

    def sort_key(self):
        return (STATUSES.index(self.status), self.rank, self.created_at, self.id)

    def to_dict(self, unmet: list[str] | None = None) -> dict:
        d = {"id": self.id, "filename": self.path.name}
        d.update(self.fields)
        if unmet is not None:
            d["unmet"] = unmet
            d["blocked"] = bool(unmet)
        return d


def validate_fields(fields: dict, where: str) -> dict:
    """Validate and normalise parsed frontmatter. Returns a new dict."""
    out = dict(fields)
    title = out.get("title")
    if not isinstance(title, str) or not title.strip():
        raise CorruptStoryError(f"{where}: 'title' must be a non-empty string")
    out["title"] = title.strip()
    status = out.get("status")
    if status not in STATUSES:
        raise CorruptStoryError(
            f"{where}: 'status' must be one of {', '.join(STATUSES)}, got {status!r}"
        )
    rank = out.get("rank", 0)
    if isinstance(rank, bool) or not isinstance(rank, int):
        raise CorruptStoryError(f"{where}: 'rank' must be an integer, got {rank!r}")
    out["rank"] = rank
    try:
        out["tags"] = normalise_tags(out.get("tags", []))
    except SkaldError as e:
        raise CorruptStoryError(f"{where}: {e}") from None
    blocked_by = out.get("blocked_by", [])
    if not isinstance(blocked_by, list) or not all(isinstance(b, str) for b in blocked_by):
        raise CorruptStoryError(f"{where}: 'blocked_by' must be a list of strings")
    out["blocked_by"] = sorted(set(b.strip() for b in blocked_by if b.strip()))
    for key in ("created_at", "updated_at"):
        val = out.get(key, "")
        if not isinstance(val, str):
            raise CorruptStoryError(f"{where}: '{key}' must be a string")
        out[key] = val
    return out


def parse_story_text(text: str, where: str = "<text>") -> tuple[dict, str]:
    """Split a story file into (fields, body). Raises CorruptStoryError."""
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r") != "---":
        raise CorruptStoryError(f"{where}: line 1: expected '---' frontmatter fence")
    fields: dict = {}
    body = None
    for i in range(1, len(lines)):
        line = lines[i].rstrip("\r")
        if line == "---":
            body = "\n".join(lines[i + 1 :])
            break
        if not line.strip():
            continue
        m = FM_LINE_RE.match(line)
        if not m:
            raise CorruptStoryError(
                f"{where}: line {i + 1}: expected 'key: value', got {line!r}"
            )
        key, raw = m.groups()
        try:
            value = json.loads(raw)
        except ValueError:
            raise CorruptStoryError(
                f"{where}: line {i + 1}: value for '{key}' is not a JSON literal: {raw!r}"
            ) from None
        if key in fields:
            raise CorruptStoryError(f"{where}: line {i + 1}: duplicate field '{key}'")
        fields[key] = value
    if body is None:
        raise CorruptStoryError(f"{where}: closing '---' fence not found")
    return validate_fields(fields, where), body


def serialise_story(fields: dict, body: str) -> str:
    out = ["---\n"]
    for key in KNOWN_FIELDS:
        if key in fields:
            out.append(f"{key}: {json.dumps(fields[key], ensure_ascii=False)}\n")
    for key, value in fields.items():
        if key not in KNOWN_FIELDS:
            out.append(f"{key}: {json.dumps(value, ensure_ascii=False)}\n")
    out.append("---\n")
    out.append(body)
    return "".join(out)


def id_from_filename(name: str) -> str | None:
    m = FILENAME_RE.match(name)
    return m.group(1) if m else None


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------


class Store:
    """All reads and writes of .skald/stories go through here."""

    def __init__(self, skald_dir: Path):
        self.dir = Path(skald_dir)
        self.stories_dir = self.dir / "stories"

    # -- reading ---------------------------------------------------------

    def _paths(self) -> list[Path]:
        if not self.stories_dir.is_dir():
            return []
        return sorted(p for p in self.stories_dir.iterdir() if p.suffix == ".md" and p.is_file())

    def _read(self, path: Path) -> Story:
        story_id = id_from_filename(path.name)
        if story_id is None:
            raise CorruptStoryError(f"{path.name}: filename must look like <6 hex>-<slug>.md")
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                text = fh.read()
        except OSError as e:
            raise CorruptStoryError(f"{path.name}: {e}") from None
        fields, body = parse_story_text(text, path.name)
        return Story(story_id, path, fields, body)

    def load_all(self) -> tuple[list[Story], list[str]]:
        """Return (stories in sort order, warnings about files that were skipped)."""
        stories, warnings = [], []
        for path in self._paths():
            try:
                stories.append(self._read(path))
            except CorruptStoryError as e:
                warnings.append(f"skipping corrupt story {e}")
        stories.sort(key=Story.sort_key)
        return stories, warnings

    def index(self) -> dict[str, Story]:
        stories, _ = self.load_all()
        return {s.id: s for s in stories}

    def resolve(self, ref: str) -> str:
        """Turn an id or unique prefix into a full id."""
        ref = (ref or "").strip().lower()
        if not ref:
            raise SkaldError("story id is required")
        matches = sorted(
            {sid for sid in (id_from_filename(p.name) for p in self._paths()) if sid and sid.startswith(ref)}
        )
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise NotFoundError(f"no story matches '{ref}'")
        raise SkaldError(f"'{ref}' is ambiguous: {', '.join(matches)}")

    def get(self, ref: str) -> Story:
        story_id = self.resolve(ref)
        for path in self._paths():
            if id_from_filename(path.name) == story_id:
                return self._read(path)
        raise NotFoundError(f"no story matches '{ref}'")  # pragma: no cover

    def unmet(self, story: Story, idx: dict[str, Story]) -> list[str]:
        return [b for b in story.blocked_by if b not in idx or idx[b].status != "done"]

    def unmet_warning(self, story: Story, idx: dict[str, Story]) -> str | None:
        unmet = self.unmet(story, idx)
        if not unmet:
            return None
        parts = [f"{b} ({idx[b].status if b in idx else 'missing'})" for b in unmet]
        return f"{story.id} has unmet dependencies: {', '.join(parts)}"

    def body_sha(self, story: Story) -> str:
        return sha256_text(story.body)

    # -- writing ---------------------------------------------------------

    def _write(self, story: Story) -> None:
        story.fields = validate_fields(story.fields, story.path.name)
        story.fields["updated_at"] = now_iso()
        atomic_write(story.path, serialise_story(story.fields, story.body))

    def _new_id(self) -> str:
        existing = {id_from_filename(p.name) for p in self._paths()}
        while True:
            candidate = secrets.token_hex(3)
            if candidate not in existing:
                return candidate

    def _bottom_rank(self, status: str, stories: list[Story]) -> int:
        ranks = [s.rank for s in stories if s.status == status]
        return (max(ranks) + RANK_STEP) if ranks else RANK_STEP

    def _resolve_blockers(self, story_id: str | None, blocked_by) -> list[str]:
        if not isinstance(blocked_by, (list, tuple)):
            raise SkaldError("blocked_by must be a list of story ids")
        out = set()
        for ref in blocked_by:
            if not isinstance(ref, str):
                raise SkaldError("blocked_by must be a list of story ids")
            full = self.resolve(ref)
            if full == story_id:
                raise SkaldError(f"{full} cannot block itself")
            out.add(full)
        return sorted(out)

    def _cycle_through(self, story_id: str, blocked_by: list[str], idx: dict[str, Story]) -> list[str] | None:
        """Return a dependency path that leads from a blocker back to story_id, or None."""
        graph = {sid: s.blocked_by for sid, s in idx.items()}
        graph[story_id] = blocked_by
        seen = set()

        def dfs(node, path):
            for dep in graph.get(node, []):
                if dep == story_id:
                    return path + [dep]
                if dep in seen:
                    continue
                seen.add(dep)
                found = dfs(dep, path + [dep])
                if found:
                    return found
            return None

        return dfs(story_id, [story_id])

    def create(self, title: str, status: str = "backlog", tags=(), blocked_by=(), body: str = "") -> tuple[Story, list[str]]:
        title = (title or "").strip()
        if not title:
            raise SkaldError("title is required")
        if status not in STATUSES:
            raise SkaldError(f"invalid status '{status}' (expected one of {', '.join(STATUSES)})")
        blockers = self._resolve_blockers(None, list(blocked_by or []))
        stories, _ = self.load_all()
        story_id = self._new_id()
        slug = slugify(title)
        filename = f"{story_id}-{slug}.md" if slug else f"{story_id}.md"
        body = body or ""
        if body and not body.endswith("\n"):
            body += "\n"
        full_body = "## Requirements\n\n" + body
        stamp = now_iso()
        fields = {
            "title": title,
            "status": status,
            "rank": self._bottom_rank(status, stories),
            "tags": normalise_tags(list(tags or [])),
            "blocked_by": blockers,
            "created_at": stamp,
            "updated_at": stamp,
        }
        story = Story(story_id, self.stories_dir / filename, fields, full_body)
        self._write(story)
        warnings = []
        if status in WARN_ON:
            w = self.unmet_warning(story, {s.id: s for s in stories})
            if w:
                warnings.append(w)
        return story, warnings

    def update(self, ref: str, *, title=None, status=None, rank=None, tags=None, blocked_by=None, order=None) -> tuple[Story, list[str]]:
        story = self.get(ref)
        stories, _ = self.load_all()
        idx = {s.id: s for s in stories}
        warnings: list[str] = []
        status_changed = False
        deps_changed = False

        if title is not None:
            if not isinstance(title, str) or not title.strip():
                raise SkaldError("title must be a non-empty string")
            story.fields["title"] = title.strip()
        if status is not None:
            if status not in STATUSES:
                raise SkaldError(f"invalid status '{status}' (expected one of {', '.join(STATUSES)})")
            if status != story.status:
                story.fields["status"] = status
                story.fields["rank"] = self._bottom_rank(status, stories)
                status_changed = True
        if rank is not None:
            if isinstance(rank, bool) or not isinstance(rank, int):
                raise SkaldError("rank must be an integer")
            story.fields["rank"] = rank
        if tags is not None:
            story.fields["tags"] = normalise_tags(tags)
        if blocked_by is not None:
            new_blockers = self._resolve_blockers(story.id, blocked_by)
            if new_blockers != story.blocked_by:
                deps_changed = True
                cycle = self._cycle_through(story.id, new_blockers, idx)
                if cycle:
                    warnings.append(f"dependency cycle: {' -> '.join(cycle)}")
                story.fields["blocked_by"] = new_blockers

        self._write(story)
        idx[story.id] = story

        if order is not None:
            self.reorder(story.status, order)
            story = self.get(story.id)

        if story.status in WARN_ON and (status_changed or deps_changed):
            w = self.unmet_warning(story, idx)
            if w:
                warnings.append(w)
        return story, warnings

    def reorder(self, status: str, ids) -> list[Story]:
        if status not in STATUSES:
            raise SkaldError(f"invalid status '{status}'")
        if not isinstance(ids, (list, tuple)):
            raise SkaldError("order must be a list of story ids")
        stories, _ = self.load_all()
        column = [s for s in stories if s.status == status]
        by_id = {s.id: s for s in column}
        ordered: list[Story] = []
        seen = set()
        for ref in ids:
            full = self.resolve(ref)
            if full not in by_id:
                raise SkaldError(f"{full} is not in the '{status}' column")
            if full in seen:
                continue
            seen.add(full)
            ordered.append(by_id[full])
        ordered.extend(s for s in column if s.id not in seen)
        changed = []
        for i, s in enumerate(ordered):
            new_rank = (i + 1) * RANK_STEP
            if s.rank != new_rank:
                s.fields["rank"] = new_rank
                self._write(s)
                changed.append(s)
        return changed

    def append_note(self, ref: str, text: str, author: str = "agent") -> Story:
        text = (text or "").strip()
        if not text:
            raise SkaldError("note text is required")
        author = (author or "").strip() or "agent"
        if re.search(r"[\[\]\n]", author):
            raise SkaldError("author may not contain brackets or newlines")
        story = self.get(ref)
        body = story.body.rstrip("\n")
        body = body + "\n\n" if body.strip() else ""
        body += f"## [{author}] {note_stamp()}\n{text}\n"
        story.body = body
        self._write(story)
        return story

    def write_body(self, ref: str, body: str, base_sha256: str | None) -> Story:
        if not isinstance(body, str):
            raise SkaldError("body must be a string")
        story = self.get(ref)
        current = self.body_sha(story)
        if base_sha256 is not None and base_sha256 != current:
            raise ConflictError("body has changed on disk since it was loaded")
        story.body = body
        self._write(story)
        return story

    def dependents(self, story_id: str) -> list[Story]:
        stories, _ = self.load_all()
        return [s for s in stories if story_id in s.blocked_by]

    def delete(self, ref: str, force: bool = False) -> Story:
        story = self.get(ref)
        deps = self.dependents(story.id)
        if deps and not force:
            raise ConflictError(
                f"{story.id} is a dependency of {', '.join(d.id for d in deps)}; use --force to delete anyway"
            )
        os.unlink(story.path)
        return story

    # -- checks ----------------------------------------------------------

    def check(self) -> list[str]:
        problems: list[str] = []
        stories: list[Story] = []
        seen_ids: dict[str, str] = {}
        for path in self._paths():
            try:
                with open(path, encoding="utf-8", newline="") as fh:
                    raw = fh.read()
            except OSError as e:
                problems.append(f"{path.name}: {e}")
                continue
            if CONFLICT_RE.search(raw):
                problems.append(f"{path.name}: contains git conflict markers")
                continue
            try:
                story = self._read(path)
            except CorruptStoryError as e:
                problems.append(str(e))
                continue
            if story.id in seen_ids:
                problems.append(f"{path.name}: duplicate id {story.id} (also {seen_ids[story.id]})")
                continue
            seen_ids[story.id] = path.name
            stories.append(story)
        idx = {s.id: s for s in stories}
        for s in stories:
            for b in s.blocked_by:
                if b == s.id:
                    problems.append(f"{s.path.name}: blocked by itself")
                elif b not in idx:
                    problems.append(f"{s.path.name}: blocked_by references missing story {b}")
        reported = set()
        for s in stories:
            cycle = self._cycle_through(s.id, s.blocked_by, idx)
            if cycle:
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    problems.append(f"dependency cycle: {' -> '.join(cycle)}")
        return problems

    # -- init ------------------------------------------------------------

    def init(self, self_path: Path | None = None) -> list[str]:
        """Create the layout. Returns human-readable lines describing what happened."""
        lines = []
        self.stories_dir.mkdir(parents=True, exist_ok=True)
        keep = self.stories_dir / ".gitkeep"
        if not keep.exists():
            keep.write_text("")
        lines.append(f"stories directory: {self.stories_dir}")

        agents = self.dir / "AGENTS.md"
        if agents.exists():
            lines.append(f"kept existing {agents}")
        else:
            agents.write_text(AGENTS_MD, encoding="utf-8")
            lines.append(f"wrote {agents}")

        target = self.dir / "skald.py"
        if self_path is not None and self_path.resolve() != target.resolve():
            if target.exists():
                lines.append(f"kept existing {target}")
            else:
                shutil.copyfile(self_path, target)
                lines.append(f"vendored {target}")

        root = git_root(self.dir)
        if root and (root / ".skald").resolve() == self.dir.resolve():
            existing = subprocess.run(
                ["git", "config", "--get", "alias.skald"],
                cwd=str(root), capture_output=True, text=True, check=False,
            )
            if existing.returncode == 0 and existing.stdout.strip():
                lines.append(f"kept existing git alias: skald = {existing.stdout.strip()}")
            else:
                subprocess.run(
                    ["git", "config", "alias.skald", "!python3 .skald/skald.py"],
                    cwd=str(root), capture_output=True, text=True, check=False,
                )
                lines.append("configured git alias: `git skald ...` now works in this clone")
        lines.append("")
        lines.append("Add this line to your repository's CLAUDE.md or AGENTS.md:")
        lines.append("  This repository tracks work with Skald. Read .skald/AGENTS.md before starting any task.")
        return lines


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _warn(warnings: list[str]) -> None:
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)


def _story_dicts(store: Store, stories: list[Story], idx: dict[str, Story]) -> list[dict]:
    return [s.to_dict(store.unmet(s, idx)) for s in stories]


def _print_table(store: Store, stories: list[Story], idx: dict[str, Story]) -> None:
    rows = []
    for s in stories:
        unmet = store.unmet(s, idx)
        rows.append([s.id, s.status, str(s.rank), ",".join(unmet) or "-", ",".join(s.tags) or "-", s.title])
    headers = ["ID", "STATUS", "RANK", "BLOCKED", "TAGS", "TITLE"]
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row[:-1]):
            widths[i] = max(widths[i], len(cell))
    fmt = "  ".join("{:<%d}" % w for w in widths[:-1]) + "  {}"
    print(fmt.format(*headers))
    for row in rows:
        print(fmt.format(*row))


def _read_text_arg(value: str | None) -> str:
    if value == "-":
        return sys.stdin.read()
    return value or ""


def _parse_plus_minus(args: list[str], what: str) -> tuple[list[str], list[str]]:
    add, remove = [], []
    for a in args:
        if a.startswith("+") and len(a) > 1:
            add.append(a[1:])
        elif a.startswith("-") and len(a) > 1:
            remove.append(a[1:])
        else:
            raise SkaldError(f"expected +{what} or -{what}, got '{a}'")
    if not add and not remove:
        raise SkaldError(f"nothing to do: give at least one +{what} or -{what}")
    return add, remove


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="skald", description="File-system-native Kanban for AI coding agents.")
    p.add_argument("--version", action="version", version=f"skald {VERSION}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("init", help="create .skald/ layout, AGENTS.md, and the git alias")

    ls = sub.add_parser("ls", help="list stories")
    ls.add_argument("--status", choices=STATUSES)
    ls.add_argument("--tag")
    ls.add_argument("--unblocked", action="store_true", help="only stories with no unmet dependencies")
    ls.add_argument("--all", action="store_true", help="include done stories")
    ls.add_argument("--json", action="store_true")

    nx = sub.add_parser("next", help="print the story an agent should pick up next")
    nx.add_argument("--json", action="store_true")

    sh = sub.add_parser("show", help="print a story file")
    sh.add_argument("id")
    sh.add_argument("--json", action="store_true")

    new = sub.add_parser("new", help="create a story")
    new.add_argument("title")
    new.add_argument("--status", choices=STATUSES, default="backlog")
    new.add_argument("--tags", default="", help="comma-separated")
    new.add_argument("--blocked-by", default="", help="comma-separated story ids")
    new.add_argument("--body", default="", help="requirements text, or - to read stdin")
    new.add_argument("--json", action="store_true")

    mv = sub.add_parser("mv", help="change a story's status")
    mv.add_argument("id")
    mv.add_argument("status", choices=STATUSES)

    st = sub.add_parser("set", help="set title=... or rank=N")
    st.add_argument("id")
    st.add_argument("assignments", nargs="+", metavar="key=value")

    sub.add_parser("tag", help="tag <id> +tag -tag ...")
    sub.add_parser("block", help="block <id> +id -id ...")

    note = sub.add_parser("note", help="append a note to a story")
    note.add_argument("id")
    note.add_argument("text", help="note text, or - to read stdin")
    note.add_argument("--as", dest="author", default="agent", help="author label (default: agent)")

    rm = sub.add_parser("rm", help="delete a story")
    rm.add_argument("id")
    rm.add_argument("--force", action="store_true")

    ck = sub.add_parser("check", help="validate every story file")
    ck.add_argument("--json", action="store_true")

    sv = sub.add_parser("serve", help="start the web board")
    sv.add_argument("--host", default=DEFAULT_HOST)
    sv.add_argument("--port", type=int, default=DEFAULT_PORT)
    sv.add_argument("--open", action="store_true", help="open the board in a browser")
    return p


def run(argv: list[str], store: Store | None = None) -> int:
    store = store or Store(default_skald_dir())

    # `tag` and `block` take +x/-y arguments that argparse would treat as options.
    if argv and argv[0] in ("tag", "block"):
        if len(argv) < 2:
            raise SkaldError(f"usage: skald {argv[0]} <id> +item -item ...")
        ref, rest = argv[1], argv[2:]
        story = store.get(ref)
        if argv[0] == "tag":
            add, remove = _parse_plus_minus(rest, "tag")
            tags = set(story.tags) | set(normalise_tags(add))
            tags -= set(normalise_tags(remove))
            story, warnings = store.update(story.id, tags=sorted(tags))
            _warn(warnings)
            print(f"{story.id} tags: {', '.join(story.tags) or '-'}")
        else:
            add, remove = _parse_plus_minus(rest, "id")
            blockers = set(story.blocked_by) | {store.resolve(a) for a in add}
            blockers -= {store.resolve(r) for r in remove}
            story, warnings = store.update(story.id, blocked_by=sorted(blockers))
            _warn(warnings)
            print(f"{story.id} blocked_by: {', '.join(story.blocked_by) or '-'}")
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    if args.command == "init":
        for line in store.init(self_path=Path(__file__).resolve()):
            print(line)
        return 0

    if args.command == "serve":
        return serve(store, args.host, args.port, args.open)

    if args.command == "check":
        problems = store.check()
        if args.json:
            print(json.dumps({"ok": not problems, "problems": problems}, indent=2))
        elif problems:
            for pr in problems:
                print(f"PROBLEM: {pr}")
        else:
            print("ok")
        return 2 if problems else 0

    if args.command == "new":
        tags = [t for t in args.tags.split(",") if t.strip()]
        blockers = [b for b in args.blocked_by.split(",") if b.strip()]
        body = _read_text_arg(args.body)
        story, warnings = store.create(args.title, args.status, tags, blockers, body)
        _warn(warnings)
        if args.json:
            print(json.dumps(story.to_dict(store.unmet(story, store.index())), indent=2))
        else:
            print(story.id)
        return 0

    stories, load_warnings = store.load_all()
    idx = {s.id: s for s in stories}
    _warn(load_warnings)

    if args.command == "ls":
        rows = stories
        if args.status:
            rows = [s for s in rows if s.status == args.status]
        elif not args.all:
            rows = [s for s in rows if s.status != "done"]
        if args.tag:
            tag = args.tag.strip().lower()
            rows = [s for s in rows if tag in s.tags]
        if args.unblocked:
            rows = [s for s in rows if not store.unmet(s, idx)]
        if args.json:
            print(json.dumps(_story_dicts(store, rows, idx), indent=2))
        else:
            _print_table(store, rows, idx)
        return 0

    if args.command == "next":
        for s in stories:
            if s.status == "ready" and not store.unmet(s, idx):
                if args.json:
                    print(json.dumps(s.to_dict([]), indent=2))
                else:
                    _print_table(store, [s], idx)
                return 0
        print("no ready, unblocked stories", file=sys.stderr)
        return 1

    if args.command == "show":
        story = store.get(args.id)
        if args.json:
            d = story.to_dict(store.unmet(story, idx))
            d["body"] = story.body
            d["body_sha256"] = store.body_sha(story)
            print(json.dumps(d, indent=2))
        else:
            sys.stdout.write(serialise_story(story.fields, story.body))
        return 0

    if args.command == "mv":
        story, warnings = store.update(args.id, status=args.status)
        _warn(warnings)
        print(f"moved {story.id} to {story.status}")
        return 0

    if args.command == "set":
        kwargs = {}
        for a in args.assignments:
            if "=" not in a:
                raise SkaldError(f"expected key=value, got '{a}'")
            key, value = a.split("=", 1)
            key = key.strip()
            if key == "title":
                kwargs["title"] = value
            elif key == "rank":
                try:
                    kwargs["rank"] = int(value)
                except ValueError:
                    raise SkaldError(f"rank must be an integer, got '{value}'") from None
            else:
                raise SkaldError(f"cannot set '{key}' (use mv, tag, or block for status, tags, blocked_by)")
        story, warnings = store.update(args.id, **kwargs)
        _warn(warnings)
        print(f"updated {story.id}")
        return 0

    if args.command == "note":
        story = store.append_note(args.id, _read_text_arg(args.text), args.author)
        print(f"noted on {story.id}")
        return 0

    if args.command == "rm":
        story = store.delete(args.id, force=args.force)
        print(f"deleted {story.id} ({story.path.name})")
        return 0

    parser.print_help()  # pragma: no cover
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        return run(argv)
    except SkaldError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return e.exit_code
    except KeyboardInterrupt:
        return 130


# --------------------------------------------------------------------------
# HTTP server
# --------------------------------------------------------------------------


class SkaldServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, store: Store, quiet: bool = True):
        super().__init__(addr, Handler)
        self.store = store
        self.quiet = quiet


class Handler(BaseHTTPRequestHandler):
    server_version = f"Skald/{VERSION}"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # noqa: D401
        if not getattr(self.server, "quiet", True):
            super().log_message(fmt, *args)

    @property
    def store(self) -> Store:
        return self.server.store  # type: ignore[attr-defined]

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

    # -- routes ----------------------------------------------------------

    def _dispatch(self, method: str, parts: list[str], query: dict) -> None:
        store = self.store
        if method == "GET" and parts in ([], ["index.html"]):
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parts == ["favicon.ico"]:
            self._send(204, b"", "image/x-icon")
            return
        if not parts or parts[0] != "api":
            self._json(404, {"error": "not found"})
            return
        rest = parts[1:]

        if rest == ["board"] and method == "GET":
            stories, warnings = store.load_all()
            idx = {s.id: s for s in stories}
            self._json(200, {"statuses": STATUSES, "stories": _story_dicts(store, stories, idx), "warnings": warnings})
            return

        if rest == ["stories"] and method == "POST":
            data = self._read_json()
            story, warnings = store.create(
                data.get("title", ""),
                data.get("status", "backlog"),
                data.get("tags", []),
                data.get("blocked_by", []),
                data.get("body", ""),
            )
            self._json(201, {"story": story.to_dict(store.unmet(story, store.index())), "warnings": warnings})
            return

        if len(rest) >= 2 and rest[0] == "stories":
            ref = rest[1]
            tail = rest[2:]
            if not tail and method == "GET":
                story = store.get(ref)
                d = story.to_dict(store.unmet(story, store.index()))
                d["body"] = story.body
                d["body_sha256"] = store.body_sha(story)
                self._json(200, d)
                return
            if not tail and method == "PATCH":
                data = self._read_json()
                allowed = {"title", "status", "rank", "tags", "blocked_by", "order"}
                unknown = set(data) - allowed
                if unknown:
                    raise SkaldError(f"unknown fields: {', '.join(sorted(unknown))}")
                story, warnings = store.update(ref, **{k: data[k] for k in data})
                self._json(200, {"story": story.to_dict(store.unmet(story, store.index())), "warnings": warnings})
                return
            if not tail and method == "DELETE":
                force = query.get("force", ["0"])[0] in ("1", "true", "yes")
                store.delete(ref, force=force)
                self._send(204, b"", "application/json")
                return
            if tail == ["body"] and method == "PUT":
                data = self._read_json()
                story = store.write_body(ref, data.get("body"), data.get("base_sha256"))
                d = story.to_dict(store.unmet(story, store.index()))
                d["body_sha256"] = store.body_sha(story)
                self._json(200, d)
                return
            if tail == ["notes"] and method == "POST":
                data = self._read_json()
                story = store.append_note(ref, data.get("text", ""), data.get("author") or "human")
                d = story.to_dict(store.unmet(story, store.index()))
                d["body"] = story.body
                d["body_sha256"] = store.body_sha(story)
                self._json(201, d)
                return

        self._json(404, {"error": "not found"})


def serve(store: Store, host: str, port: int, open_browser: bool = False, quiet: bool = True) -> int:
    if not store.stories_dir.is_dir():
        raise SkaldError(f"{store.stories_dir} does not exist; run `skald init` first")
    httpd = SkaldServer((host, port), store, quiet=quiet)
    url = f"http://{host}:{httpd.server_address[1]}/"
    print(f"Skald board at {url}  (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


# --------------------------------------------------------------------------
# Embedded agent contract (written to .skald/AGENTS.md by `init`)
# --------------------------------------------------------------------------

AGENTS_MD = """# Working with Skald

This repository tracks its backlog with Skald. Stories are Markdown files in
`.skald/stories/`. The tool is `python3 .skald/skald.py`, which works from
any directory in the repository. `git skald ...` may also work on machines
where `skald init` has been run, but do not rely on it. The examples below
abbreviate the command to `skald`.

## Workflow

1. **Orient.** Run `skald ls` at the start of a session to see the board.
2. **Pick work.** Run `skald next --json`. It prints the first `ready`,
   unblocked story in rank order. If it prints nothing, run `skald ls --json`
   and either pick an unblocked `ready` story or ask the human.
3. **Claim it.** Run `skald mv <id> in_progress`. Then run `skald show <id>`
   and read the whole file, including any notes from humans.
4. **Warnings are advisory.** If `mv` prints a `WARNING:` about unmet
   dependencies, decide whether to stub the missing piece or work the blocker
   first. Record your decision with a note.
5. **Record progress.** Use `skald note <id> "text"` (or `skald note <id> -`
   with the text on stdin) for progress, decisions, and checklists.
6. **Discovered work.** When you find work outside the current story, create
   a story for it with `skald new "title" --body "..."` and link it with
   `--blocked-by <id>` or `skald block <id> +<other>` where a real dependency
   exists. Do not silently expand the scope of the story you are on.
7. **Finish.** Run `skald mv <id> review` with a closing note that says what
   changed and how it was verified. A human moves stories to `done`. If the
   human has told you to close stories yourself, move to `done` instead.
8. **Commit together.** Story file changes go in the same commit as the code
   they describe. Never leave `.skald/` changes uncommitted at the end of a
   task.

## Rules

- Never edit the lines between the two `---` fences of a story file by hand,
  and never create story files by hand. Use `skald new`, `skald mv`,
  `skald set`, `skald tag`, and `skald block`.
- You may edit the body of a story (everything after the second `---`) with
  any tool. Prefer `skald note` for appending.
- Any command that takes an id accepts a unique prefix: `skald show a3f`.
- Prefer `--json` output when you need to parse results.
- Exit codes: 0 success (warnings on stderr), 1 usage error or not found,
  2 corrupt story file. Run `skald check` if something looks wrong.

## Command reference

```
skald ls [--status S] [--tag T] [--unblocked] [--all] [--json]
skald next [--json]
skald show <id> [--json]
skald new "<title>" [--status S] [--tags a,b] [--blocked-by id,id] [--body TEXT | --body -]
skald mv <id> <backlog|ready|in_progress|review|done>
skald set <id> title="..." rank=N
skald tag <id> +tag -tag
skald block <id> +id -id
skald note <id> "<text>" | -   [--as LABEL]
skald rm <id> [--force]
skald check [--json]
skald serve [--port 8321] [--open]
```
"""

# --------------------------------------------------------------------------
# Embedded web board
# --------------------------------------------------------------------------

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skald</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  .card.dragging { opacity: .4; }
  .placeholder { height: 0.5rem; border-radius: .25rem; background: #93c5fd; margin: .25rem 0; }
  .col-list { min-height: 4rem; }
  textarea { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
</style>
</head>
<body class="bg-slate-100 text-slate-800 h-screen flex flex-col">

<header class="flex items-center gap-4 px-4 py-2 bg-white border-b border-slate-200">
  <h1 class="text-lg font-semibold tracking-tight">Skald</h1>
  <input id="search" type="search" placeholder="Filter by title, id, or tag" class="flex-1 max-w-md rounded border border-slate-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300">
  <span id="conn" class="text-xs text-slate-400"></span>
  <button id="new-btn" class="ml-auto rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700">New story</button>
</header>

<main id="board" class="flex-1 flex gap-3 p-3 overflow-x-auto"></main>

<div id="toasts" class="fixed bottom-4 right-4 flex flex-col gap-2 z-50"></div>

<div id="modal" class="fixed inset-0 bg-black/40 hidden items-center justify-center p-4 z-40">
  <div class="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-full overflow-y-auto">
    <div class="flex items-center gap-3 px-5 py-3 border-b border-slate-200">
      <span id="m-id" class="font-mono text-xs text-slate-400"></span>
      <span id="m-meta" class="text-xs text-slate-400"></span>
      <button id="m-close" class="ml-auto text-slate-400 hover:text-slate-700 text-xl leading-none" title="Close (Esc)">&times;</button>
    </div>
    <div class="px-5 py-4 grid gap-4">
      <label class="grid gap-1 text-sm">
        <span class="text-slate-500">Title</span>
        <input id="m-title" class="rounded border border-slate-300 px-2 py-1.5 text-base font-medium">
      </label>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
        <label class="grid gap-1"><span class="text-slate-500">Status</span>
          <select id="m-status" class="rounded border border-slate-300 px-2 py-1.5"></select></label>
        <label class="grid gap-1"><span class="text-slate-500">Tags (comma-separated)</span>
          <input id="m-tags" class="rounded border border-slate-300 px-2 py-1.5"></label>
        <label class="grid gap-1"><span class="text-slate-500">Blocked by (ids, comma-separated)</span>
          <input id="m-blockers" class="rounded border border-slate-300 px-2 py-1.5 font-mono"></label>
      </div>
      <div id="m-unmet" class="text-xs text-red-600 hidden"></div>
      <label class="grid gap-1 text-sm">
        <span class="text-slate-500">Body (Markdown)</span>
        <textarea id="m-body" rows="14" class="rounded border border-slate-300 px-2 py-1.5 text-sm"></textarea>
      </label>
      <div class="flex items-center gap-2">
        <button id="m-save" class="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700">Save</button>
        <button id="m-reload" class="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50">Reload</button>
        <span id="m-dirty" class="text-xs text-amber-600"></span>
        <button id="m-delete" class="ml-auto rounded px-3 py-1.5 text-sm text-red-600 hover:bg-red-50">Delete</button>
      </div>
      <div id="m-note-wrap" class="grid gap-2 border-t border-slate-200 pt-4 text-sm">
        <span class="text-slate-500">Add a note</span>
        <textarea id="m-note" rows="3" class="rounded border border-slate-300 px-2 py-1.5 text-sm" placeholder="Appended to the bottom of the story with a timestamp"></textarea>
        <div><button id="m-note-btn" class="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50">Append note</button></div>
      </div>
    </div>
  </div>
</div>

<script>
(() => {
  const LABELS = { backlog: 'Backlog', ready: 'Ready', in_progress: 'In progress', review: 'Review', done: 'Done' };
  const state = { statuses: [], stories: [], filter: '', dragging: null, modal: null, loaded: null };
  const $ = (id) => document.getElementById(id);
  const board = $('board'), modal = $('modal');

  // ---- API -------------------------------------------------------------
  async function api(method, path, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    const res = await fetch(path, opts);
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (!res.ok) { const err = new Error((data && data.error) || res.statusText); err.status = res.status; throw err; }
    return data;
  }

  // ---- Toasts ----------------------------------------------------------
  function toast(msg, kind) {
    const el = document.createElement('div');
    const colour = kind === 'error' ? 'bg-red-600' : kind === 'warn' ? 'bg-amber-500' : 'bg-slate-800';
    el.className = `${colour} text-white text-sm rounded px-3 py-2 shadow-lg max-w-sm`;
    el.textContent = msg;
    $('toasts').appendChild(el);
    setTimeout(() => el.remove(), 5000);
  }
  function showWarnings(ws) { (ws || []).forEach(w => toast(w, 'warn')); }

  // ---- Board -----------------------------------------------------------
  function ago(iso) {
    if (!iso) return '';
    const s = Math.max(0, (Date.now() - Date.parse(iso)) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
  }
  function matches(story) {
    const f = state.filter;
    if (!f) return true;
    return story.title.toLowerCase().includes(f) || story.id.startsWith(f) || story.tags.some(t => t.includes(f));
  }
  function cardEl(story) {
    const el = document.createElement('div');
    el.className = 'card bg-white rounded shadow-sm border border-slate-200 p-2.5 cursor-grab hover:shadow ' + (story.blocked ? 'border-l-4 border-l-red-500' : '');
    el.dataset.id = story.id;
    el.draggable = true;
    const tags = story.tags.map(t => `<span class="inline-block rounded-full bg-slate-100 text-slate-600 px-2 py-0.5 text-[11px]">${esc(t)}</span>`).join(' ');
    const lock = story.blocked ? `<span class="text-red-500" title="Blocked by: ${esc(story.unmet.join(', '))}">&#128274;</span>` : '';
    el.innerHTML = `
      <div class="flex items-start gap-1.5">
        <div class="text-sm font-medium leading-snug flex-1">${esc(story.title)}</div>${lock}
      </div>
      <div class="mt-1.5 flex flex-wrap gap-1 items-center">${tags}</div>
      <div class="mt-1.5 flex justify-between text-[11px] text-slate-400 font-mono">
        <span>${story.id}</span><span class="font-sans">${ago(story.updated_at)}</span>
      </div>`;
    el.addEventListener('click', () => openModal(story.id));
    el.addEventListener('dragstart', (e) => {
      state.dragging = story.id;
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', story.id);
      setTimeout(() => el.classList.add('dragging'), 0);
    });
    el.addEventListener('dragend', () => { state.dragging = null; removePlaceholder(); render(); });
    return el;
  }
  function esc(s) { return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

  function render() {
    board.innerHTML = '';
    for (const status of state.statuses) {
      const col = document.createElement('section');
      col.className = 'flex flex-col w-72 shrink-0 bg-slate-200/70 rounded-lg';
      const items = state.stories.filter(s => s.status === status);
      const shown = items.filter(matches);
      col.innerHTML = `<div class="flex items-center justify-between px-3 py-2 text-sm font-semibold text-slate-600">
        <span>${LABELS[status] || status}</span><span class="text-xs font-normal text-slate-400">${items.length}</span></div>`;
      const list = document.createElement('div');
      list.className = 'col-list flex-1 flex flex-col gap-2 px-2 pb-2 overflow-y-auto';
      list.dataset.status = status;
      shown.forEach(s => list.appendChild(cardEl(s)));
      list.addEventListener('dragover', onDragOver);
      list.addEventListener('drop', onDrop);
      col.appendChild(list);
      board.appendChild(col);
    }
  }

  // ---- Drag and drop ---------------------------------------------------
  let placeholder = null;
  function removePlaceholder() { if (placeholder) { placeholder.remove(); placeholder = null; } }
  function onDragOver(e) {
    if (!state.dragging) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    const list = e.currentTarget;
    if (!placeholder) { placeholder = document.createElement('div'); placeholder.className = 'placeholder'; }
    const cards = [...list.querySelectorAll('.card')].filter(c => c.dataset.id !== state.dragging);
    let before = null;
    for (const c of cards) {
      const r = c.getBoundingClientRect();
      if (e.clientY < r.top + r.height / 2) { before = c; break; }
    }
    if (before) list.insertBefore(placeholder, before); else list.appendChild(placeholder);
  }
  async function onDrop(e) {
    e.preventDefault();
    const list = e.currentTarget;
    const id = state.dragging;
    if (!id || !placeholder) return;
    const status = list.dataset.status;
    const order = [];
    for (const child of list.children) {
      if (child === placeholder) order.push(id);
      else if (child.dataset.id && child.dataset.id !== id) order.push(child.dataset.id);
    }
    // Cards hidden by the filter keep their relative position after the visible ones.
    const hidden = state.stories.filter(s => s.status === status && !matches(s) && s.id !== id).map(s => s.id);
    removePlaceholder();
    state.dragging = null;
    try {
      const res = await api('PATCH', `/api/stories/${id}`, { status, order: order.concat(hidden) });
      showWarnings(res.warnings);
    } catch (err) { toast(err.message, 'error'); }
    await refresh();
  }

  // ---- Modal -----------------------------------------------------------
  function fillStatusSelect() {
    $('m-status').innerHTML = state.statuses.map(s => `<option value="${s}">${LABELS[s] || s}</option>`).join('');
  }
  function showModal() { modal.classList.remove('hidden'); modal.classList.add('flex'); }
  function hideModal() { modal.classList.add('hidden'); modal.classList.remove('flex'); state.modal = null; state.loaded = null; refresh(); }

  async function openModal(id) {
    fillStatusSelect();
    if (id === null) {
      state.modal = 'new'; state.loaded = null;
      $('m-id').textContent = 'new story'; $('m-meta').textContent = '';
      $('m-title').value = ''; $('m-status').value = 'backlog'; $('m-tags').value = ''; $('m-blockers').value = '';
      $('m-body').value = ''; $('m-unmet').classList.add('hidden'); $('m-dirty').textContent = '';
      $('m-note-wrap').classList.add('hidden'); $('m-delete').classList.add('hidden'); $('m-reload').classList.add('hidden');
      showModal(); $('m-title').focus();
      return;
    }
    try {
      const s = await api('GET', `/api/stories/${id}`);
      state.modal = s.id; state.loaded = s;
      $('m-id').textContent = s.filename;
      $('m-meta').textContent = `created ${s.created_at} · updated ${s.updated_at}`;
      $('m-title').value = s.title; $('m-status').value = s.status;
      $('m-tags').value = s.tags.join(', '); $('m-blockers').value = s.blocked_by.join(', ');
      $('m-body').value = s.body; $('m-dirty').textContent = '';
      const um = $('m-unmet');
      if (s.unmet.length) { um.textContent = 'Unmet dependencies: ' + s.unmet.join(', '); um.classList.remove('hidden'); } else um.classList.add('hidden');
      $('m-note').value = '';
      $('m-note-wrap').classList.remove('hidden'); $('m-delete').classList.remove('hidden'); $('m-reload').classList.remove('hidden');
      showModal();
    } catch (err) { toast(err.message, 'error'); }
  }
  function splitList(v) { return v.split(',').map(x => x.trim()).filter(Boolean); }

  async function saveModal() {
    const title = $('m-title').value, status = $('m-status').value;
    const tags = splitList($('m-tags').value), blocked_by = splitList($('m-blockers').value), body = $('m-body').value;
    try {
      if (state.modal === 'new') {
        const res = await api('POST', '/api/stories', { title, status, tags, blocked_by, body });
        showWarnings(res.warnings); toast(`Created ${res.story.id}`);
        hideModal();
        return;
      }
      const s = state.loaded;
      const patch = {};
      if (title !== s.title) patch.title = title;
      if (status !== s.status) patch.status = status;
      if (tags.join(',') !== s.tags.join(',')) patch.tags = tags;
      if (blocked_by.join(',') !== s.blocked_by.join(',')) patch.blocked_by = blocked_by;
      if (Object.keys(patch).length) { const res = await api('PATCH', `/api/stories/${s.id}`, patch); showWarnings(res.warnings); }
      if (body !== s.body) {
        try { await api('PUT', `/api/stories/${s.id}/body`, { body, base_sha256: s.body_sha256 }); }
        catch (err) {
          if (err.status === 409) { $('m-dirty').textContent = 'The body changed on disk while you were editing. Copy your text, then Reload.'; toast(err.message, 'error'); return; }
          throw err;
        }
      }
      toast('Saved');
      await openModal(s.id);
    } catch (err) { toast(err.message, 'error'); }
  }
  async function addNote() {
    const text = $('m-note').value.trim();
    if (!text || state.modal === 'new') return;
    try {
      await api('POST', `/api/stories/${state.modal}/notes`, { text, author: 'human' });
      $('m-note').value = '';
      await openModal(state.modal);
    } catch (err) { toast(err.message, 'error'); }
  }
  async function deleteStory() {
    const id = state.modal;
    if (!id || id === 'new') return;
    if (!confirm(`Delete story ${id}? This removes the file.`)) return;
    try { await api('DELETE', `/api/stories/${id}`); }
    catch (err) {
      if (err.status === 409 && confirm(err.message + '\n\nDelete anyway?')) {
        try { await api('DELETE', `/api/stories/${id}?force=1`); } catch (e2) { toast(e2.message, 'error'); return; }
      } else { toast(err.message, 'error'); return; }
    }
    toast(`Deleted ${id}`);
    hideModal();
  }

  // ---- Wiring ----------------------------------------------------------
  async function refresh() {
    if (state.modal || state.dragging) return;
    try {
      const data = await api('GET', '/api/board');
      state.statuses = data.statuses; state.stories = data.stories;
      $('conn').textContent = data.warnings.length ? `${data.warnings.length} file(s) skipped, see terminal` : '';
      render();
    } catch (err) { $('conn').textContent = 'disconnected'; }
  }
  $('search').addEventListener('input', (e) => { state.filter = e.target.value.trim().toLowerCase(); render(); });
  $('new-btn').addEventListener('click', () => openModal(null));
  $('m-close').addEventListener('click', hideModal);
  $('m-save').addEventListener('click', saveModal);
  $('m-reload').addEventListener('click', () => state.modal && state.modal !== 'new' && openModal(state.modal));
  $('m-note-btn').addEventListener('click', addNote);
  $('m-delete').addEventListener('click', deleteStory);
  modal.addEventListener('click', (e) => { if (e.target === modal) hideModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && state.modal) hideModal(); });
  setInterval(() => { if (document.visibilityState === 'visible') refresh(); }, 3000);
  refresh();
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
