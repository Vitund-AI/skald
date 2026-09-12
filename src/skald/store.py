"""Story files and the per-project store.

A story is a Markdown file in ``.skald/stories/`` with a ``---`` fenced
frontmatter block whose values are JSON literals. The filename carries the
story id. See SPEC.md for the format.
"""
from __future__ import annotations

import json
import os
import re
import secrets
from pathlib import Path
from typing import Optional

from .config import ProjectConfig
from .errors import ConflictError, CorruptStoryError, NotFoundError, SkaldError
from .util import atomic_write, checklist_progress, note_stamp, now_iso, parse_iso, parse_when, read_text, sha256_text, slugify

KNOWN_FIELDS = ["title", "status", "rank", "tags", "blocked_by", "assignee", "parent", "released", "created_at", "updated_at"]
RANK_STEP = 10

ID_RE = re.compile(r"^[0-9a-f]{6}$")
REF_RE = re.compile(r"^(?:(?P<project>[a-z0-9][a-z0-9-]{0,63}):)?(?P<id>[0-9a-f]{6})$")
FILENAME_RE = re.compile(r"^([0-9a-f]{6})(?:-[a-z0-9-]*)?\.md$")
FM_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*): (.*)$")
CONFLICT_RE = re.compile(r"^(<{7}|={7}|>{7})( |$)", re.M)


def split_ref(ref: str) -> tuple[Optional[str], str]:
    """``"proj:abc123"`` -> ``("proj", "abc123")``; ``"abc123"`` -> ``(None, "abc123")``."""
    if ":" in ref:
        project, _, sid = ref.partition(":")
        return project, sid
    return None, ref


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


NOTE_HEADING_RE = re.compile(
    r"^## \[(?P<author>[^\]\n]+)\] (?P<stamp>\d{4}-\d\d-\d\d \d\d:\d\d UTC)(?: · (?P<kind>[a-z][a-z0-9_-]{0,31}))?\s*$",
    re.M,
)
KIND_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


def parse_notes(body: str) -> list[dict]:
    """Notes appended by ``skald note``, in order: ``[{author, stamp, kind, text}]``."""
    matches = list(NOTE_HEADING_RE.finditer(body))
    notes = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        text = body[m.end():end].strip("\n")
        notes.append({"author": m.group("author"), "stamp": m.group("stamp"), "kind": m.group("kind") or "note",
                      "text": text.rstrip()})
    return notes


ANSWERS_RE = re.compile(
    r"^(?P<verb>answers|withdraws) (?:Q(?P<label>\d+) )?\[(?P<author>[^\]\n]+)\] "
    r"(?P<stamp>\d{4}-\d\d-\d\d \d\d:\d\d UTC)(?: · (?P<first>.*))?\s*$", re.I)
QUESTION_REF_RE = re.compile(r"^\s*q?\s*(\d+)\s*$", re.I)


def _first_line(note: dict) -> str:
    text = note["text"].strip()
    return text.splitlines()[0] if text else ""


def answer_line(question: dict, withdraw: bool = False) -> str:
    """The first line of a decision that closes a question: the verb, the question's stable label,
    and its author, stamp, and first line. The tool matches on author, stamp, and first line; the
    label is for the person reading the file."""
    verb = "Withdraws" if withdraw else "Answers"
    label = f"Q{question['number']} " if question.get("number") else ""
    first = _first_line(question)
    return f"{verb} {label}[{question['author']}] {question['stamp']}" + (f" · {first}" if first else "")


def _answers(line: str, question: dict) -> Optional[str]:
    """``answered`` or ``withdrawn`` when ``line`` names ``question``, else None."""
    m = ANSWERS_RE.match(line)
    if not m or m.group("author") != question["author"] or m.group("stamp") != question["stamp"]:
        return None
    if m.group("first") is not None and m.group("first").strip() != _first_line(question):
        return None
    return "withdrawn" if m.group("verb").lower() == "withdraws" else "answered"


def _naming_lines(decision: dict) -> list[str]:
    """The leading lines of a decision that name questions (``answer --all`` writes one per question)."""
    out = []
    for line in decision["text"].strip().splitlines():
        if ANSWERS_RE.match(line):
            out.append(line)
        else:
            break
    return out


def questions_of(notes: list[dict]) -> list[dict]:
    """Every question note, numbered by order of appearance (Q1, Q2, ...; the number never changes),
    each with ``closed_by``: the decision that named it, plus ``how`` (answered or withdrawn), or
    None while it is open. A decision closes only the questions its leading lines name; any other
    decision is a decision, not an answer.
    """
    out: list[dict] = []
    for n in notes:
        if n["kind"] == "question":
            q = dict(n)
            q["number"] = len(out) + 1
            q["closed_by"] = None
            out.append(q)
        elif n["kind"] == "decision":
            for line in _naming_lines(n):
                for q in out:
                    if q["closed_by"] is None:
                        how = _answers(line, q)
                        if how:
                            q["closed_by"] = {"author": n["author"], "stamp": n["stamp"], "how": how}
    return out


def open_questions(notes: list[dict]) -> list[dict]:
    """Questions no decision has named yet, each carrying its stable ``number``."""
    return [q for q in questions_of(notes) if q["closed_by"] is None]


def reopened_questions(notes: list[dict]) -> list[dict]:
    """Open questions followed by a plain decision: closed under the rule before 0.5, open now."""
    open_stamps = {(q["author"], q["stamp"], _first_line(q)) for q in open_questions(notes)}
    seen: list[dict] = []
    out: list[dict] = []
    number = 0
    for n in notes:  # file order, since two notes can share a minute
        if n["kind"] == "question":
            number += 1
            if (n["author"], n["stamp"], _first_line(n)) in open_stamps:
                seen.append(dict(n, number=number))
        elif n["kind"] == "decision" and not _naming_lines(n):
            out.extend(q for q in seen if q not in out)
    return out


def parse_question_ref(ref) -> int:
    """``3``, ``"3"``, or ``"Q3"`` as the question number."""
    if isinstance(ref, bool):
        raise SkaldError("question must be a number such as 3 or Q3")
    if isinstance(ref, int):
        return ref
    m = QUESTION_REF_RE.match(str(ref))
    if not m:
        raise SkaldError(f"question must be a number such as 3 or Q3 (got {ref!r})")
    return int(m.group(1))


def prelude_of(body: str) -> str:
    """The body before the first note heading: every section the author wrote, none of the notes."""
    m = NOTE_HEADING_RE.search(body)
    return (body[:m.start()] if m else body).rstrip("\n")


H2_RE = re.compile(r"^##\s+(?!\[)(.+?)\s*$")


def sections_of(body: str) -> list[dict]:
    """The H2 sections of the prelude in order: ``[{heading, lines}]``, lines counted below each heading."""
    lines = prelude_of(body).splitlines()
    out: list[dict] = []
    for i, line in enumerate(lines):
        m = H2_RE.match(line)
        if m:
            out.append({"heading": m.group(1), "start": i, "lines": 0})
    for j, sec in enumerate(out):
        end = out[j + 1]["start"] if j + 1 < len(out) else len(lines)
        block = [ln for ln in lines[sec["start"] + 1:end]]
        while block and not block[-1].strip():
            block.pop()
        while block and not block[0].strip():
            block.pop(0)
        sec["lines"] = len(block)
    for sec in out:
        del sec["start"]
    return out


def section_of(body: str, name: str) -> Optional[str]:
    """One H2 section of the prelude, heading included, matched case-insensitively by prefix; None if absent."""
    lines = prelude_of(body).splitlines()
    want = name.strip().lower()
    start = None
    for i, line in enumerate(lines):
        m = H2_RE.match(line)
        if m and start is None and m.group(1).lower().startswith(want):
            start = i
        elif m and start is not None:
            return "\n".join(lines[start:i]).rstrip("\n")
    return "\n".join(lines[start:]).rstrip("\n") if start is not None else None


def requirements_of(body: str) -> str:
    """What ``resume`` prints: the ``## Requirements`` section when the body has one, else the whole prelude.

    A heading, not a length limit, decides the cut, so the author of the body
    controls it and the rule is visible in the file.
    """
    section = section_of(body, "requirements")
    return section if section is not None else prelude_of(body)


def acceptance_progress(body: str) -> tuple[int, int]:
    """Checklist progress inside a ``## Acceptance`` section only (0, 0 when absent)."""
    lines = body.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s+acceptance(\s+criteria)?\s*$", line.strip(), re.I):
            start = i + 1
            break
    if start is None:
        return 0, 0
    section = []
    for line in lines[start:]:
        if re.match(r"^#{1,2}\s", line):
            break
        section.append(line)
    return checklist_progress("\n".join(section))


# --------------------------------------------------------------------------
# Story and file format
# --------------------------------------------------------------------------


class Story:
    __slots__ = ("id", "path", "fields", "body", "archived")

    def __init__(self, story_id: str, path: Path, fields: dict, body: str, archived: bool = False):
        self.id = story_id
        self.path = path
        self.fields = fields
        self.body = body
        self.archived = archived

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
    def assignee(self) -> str:
        return self.fields.get("assignee", "")

    @property
    def created_at(self) -> str:
        return self.fields["created_at"]

    @property
    def updated_at(self) -> str:
        return self.fields["updated_at"]

    @property
    def released(self) -> str:
        return self.fields.get("released", "") or ""

    @property
    def parent(self) -> str:
        return self.fields.get("parent", "") or ""

    def to_dict(self, compact: bool = False) -> dict:
        d = {"id": self.id}
        if not compact:
            d["filename"] = self.path.name
        d.update(self.fields)
        d.setdefault("assignee", "")
        if compact:
            d.pop("created_at", None)
            d.pop("rank", None)
        d["archived"] = self.archived
        done, total = checklist_progress(self.body)
        d["checklist"] = {"done": done, "total": total}
        a_done, a_total = acceptance_progress(self.body)
        if a_total:
            d["acceptance"] = {"done": a_done, "total": a_total}
        questions = self.questions()
        open_qs = [q for q in questions if q["closed_by"] is None]
        d["questions"] = {"open": len(open_qs)}
        if not compact and open_qs:
            d["questions"]["items"] = open_qs
        if not compact and len(open_qs) < len(questions):
            d["questions"]["closed"] = [q for q in questions if q["closed_by"] is not None]
        return d

    def notes(self) -> list[dict]:
        return parse_notes(self.body)

    def last_note(self, kind: Optional[str] = None) -> Optional[dict]:
        for n in reversed(self.notes()):
            if kind is None or n["kind"] == kind:
                return n
        return None

    def questions(self) -> list[dict]:
        """Every question, numbered by appearance, with what closed it (see ``questions_of``)."""
        return questions_of(self.notes())

    def open_questions(self) -> list[dict]:
        """Questions waiting on a human: no decision has named them yet."""
        return open_questions(self.notes())


def validate_fields(fields: dict, where: str) -> dict:
    """Validate and normalise parsed frontmatter. Returns a new dict."""
    out = dict(fields)
    title = out.get("title")
    if not isinstance(title, str) or not title.strip():
        raise CorruptStoryError(f"{where}: 'title' must be a non-empty string")
    out["title"] = title.strip()
    status = out.get("status")
    if not isinstance(status, str) or not status.strip():
        raise CorruptStoryError(f"{where}: 'status' must be a non-empty string")
    out["status"] = status.strip()
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
    assignee = out.get("assignee", "")
    if assignee is None:
        assignee = ""
    if not isinstance(assignee, str):
        raise CorruptStoryError(f"{where}: 'assignee' must be a string")
    assignee = assignee.strip()
    if assignee:
        out["assignee"] = assignee
    else:
        out.pop("assignee", None)
    parent = out.get("parent", "")
    if parent is None:
        parent = ""
    if not isinstance(parent, str):
        raise CorruptStoryError(f"{where}: 'parent' must be a string")
    parent = parent.strip().lower()
    if parent and not ID_RE.match(parent):
        raise CorruptStoryError(f"{where}: 'parent' must be a local story id, got {parent!r}")
    if parent:
        out["parent"] = parent
    else:
        out.pop("parent", None)
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
            raise CorruptStoryError(f"{where}: line {i + 1}: expected 'key: value', got {line!r}")
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


def id_from_filename(name: str) -> Optional[str]:
    m = FILENAME_RE.match(name)
    return m.group(1) if m else None


# --------------------------------------------------------------------------
# Dependency state
# --------------------------------------------------------------------------


class DepState:
    """How one ``blocked_by`` entry resolved."""

    __slots__ = ("ref", "state", "satisfied", "closed")

    def __init__(self, ref: str, state: str, satisfied: bool, closed: bool = False):
        self.ref = ref          # the entry as written, e.g. "abc123" or "other:abc123"
        self.state = state      # a column key, or "missing", "unavailable", "archived"
        self.satisfied = satisfied
        self.closed = closed    # satisfied by a closed (won't do) story

    def to_dict(self) -> dict:
        return {"ref": self.ref, "state": self.state, "satisfied": self.satisfied, "closed": self.closed}


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------


class Store:
    """All reads and writes of one project's ``.skald/`` directory go through here.

    ``workspace`` is optional and duck-typed: it must provide ``open(name)``
    returning another ``Store`` or ``None`` for cross-project references.
    """

    def __init__(self, skald_dir: Path, config: ProjectConfig, workspace=None):
        self.dir = Path(skald_dir)
        self.config = config
        self.name = config.name
        self.stories_dir = self.dir / "stories"
        self.archive_dir = self.dir / "archive"
        self.templates_dir = self.dir / "templates"
        self.workspace = workspace

    def __repr__(self) -> str:  # pragma: no cover
        return f"Store({self.name!r}, {self.dir})"

    # -- reading ---------------------------------------------------------

    def _paths(self, directory: Path) -> list[Path]:
        if not directory.is_dir():
            return []
        return sorted(p for p in directory.iterdir() if p.suffix == ".md" and p.is_file())

    def _read(self, path: Path, archived: bool = False) -> Story:
        story_id = id_from_filename(path.name)
        if story_id is None:
            raise CorruptStoryError(f"{path.name}: filename must look like <6 hex>-<slug>.md")
        try:
            text = read_text(path)
        except OSError as e:
            raise CorruptStoryError(f"{path.name}: {e}") from None
        fields, body = parse_story_text(text, path.name)
        return Story(story_id, path, fields, body, archived)

    def sort_key(self, story: Story):
        return (self.config.index(story.status), story.rank, story.created_at, story.id)

    def load_all(self, include_archived: bool = False) -> tuple[list[Story], list[str]]:
        """Return (stories in sort order, warnings about files that were skipped)."""
        stories, warnings = [], []
        for path in self._paths(self.stories_dir):
            try:
                stories.append(self._read(path))
            except CorruptStoryError as e:
                warnings.append(f"skipping corrupt story {e}")
        if include_archived:
            for path in self._paths(self.archive_dir):
                try:
                    stories.append(self._read(path, archived=True))
                except CorruptStoryError as e:
                    warnings.append(f"skipping corrupt archived story {e}")
        stories.sort(key=self.sort_key)
        return stories, warnings

    def index(self, include_archived: bool = True) -> dict[str, Story]:
        stories, _ = self.load_all(include_archived=include_archived)
        return {s.id: s for s in stories}

    def _all_ids(self) -> dict[str, Path]:
        out: dict[str, Path] = {}
        for directory in (self.stories_dir, self.archive_dir):
            for p in self._paths(directory):
                sid = id_from_filename(p.name)
                if sid and sid not in out:
                    out[sid] = p
        return out

    def resolve(self, ref: str) -> str:
        """Turn a local id or unique prefix into a full id."""
        ref = (ref or "").strip().lower()
        if not ref:
            raise SkaldError("story id is required")
        if ":" in ref:
            raise SkaldError(f"'{ref}' names another project; only local ids can be resolved here")
        matches = sorted(sid for sid in self._all_ids() if sid.startswith(ref))
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise NotFoundError(f"no story matches '{ref}' in project {self.name}")
        raise SkaldError(f"'{ref}' is ambiguous: {', '.join(matches)}")

    def get(self, ref: str) -> Story:
        story_id = self.resolve(ref)
        path = self._all_ids()[story_id]
        return self._read(path, archived=path.parent == self.archive_dir)

    def get_or_none(self, story_id: str) -> Optional[Story]:
        path = self._all_ids().get(story_id)
        if path is None:
            return None
        try:
            return self._read(path, archived=path.parent == self.archive_dir)
        except CorruptStoryError:
            return None

    def body_sha(self, story: Story) -> str:
        return sha256_text(story.body)

    # -- dependencies ----------------------------------------------------

    def dep_states(self, story: Story, idx: Optional[dict[str, Story]] = None) -> list[DepState]:
        idx = idx if idx is not None else self.index()
        out = []
        for ref in story.blocked_by:
            project, sid = split_ref(ref)
            if project is None or project == self.name:
                target = idx.get(sid)
                cfg = self.config
            else:
                other = self.workspace.open(project) if self.workspace else None
                if other is None:
                    out.append(DepState(ref, "unavailable", False))
                    continue
                target = other.get_or_none(sid)
                cfg = other.config
            if target is None:
                out.append(DepState(ref, "missing", False))
            elif target.archived:
                out.append(DepState(ref, "archived", True, cfg.is_closed(target.status)))
            else:
                terminal = cfg.is_terminal(target.status)
                out.append(DepState(ref, target.status, terminal, terminal and cfg.is_closed(target.status)))
        return out

    def unmet(self, story: Story, idx: Optional[dict[str, Story]] = None) -> list[str]:
        return [d.ref for d in self.dep_states(story, idx) if not d.satisfied]

    def unmet_warning(self, story: Story, idx: Optional[dict[str, Story]] = None) -> Optional[str]:
        states = self.dep_states(story, idx)
        unmet = [d for d in states if not d.satisfied]
        closed = [d for d in states if d.satisfied and d.closed]
        if not unmet and not closed:
            return None
        parts = []
        if unmet:
            parts.append(
                f"{story.id} has unmet dependencies: " + ", ".join(f"{d.ref} ({d.state})" for d in unmet)
            )
        if closed:
            parts.append(
                f"{story.id} depends on closed stories that will not be done: "
                + ", ".join(f"{d.ref} ({d.state})" for d in closed)
            )
        return "; ".join(parts)

    def _cycle_through(self, story_id: str, blocked_by: list[str], idx: dict[str, Story]) -> Optional[list[str]]:
        """Return a local dependency path leading from a blocker back to story_id, or None."""
        graph = {sid: [split_ref(b)[1] for b in s.blocked_by if split_ref(b)[0] in (None, self.name)] for sid, s in idx.items()}
        graph[story_id] = [split_ref(b)[1] for b in blocked_by if split_ref(b)[0] in (None, self.name)]
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

    # -- writing ---------------------------------------------------------

    def _write(self, story: Story, touch: bool = True) -> None:
        story.fields = validate_fields(story.fields, story.path.name)
        if touch:
            story.fields["updated_at"] = now_iso()
        atomic_write(story.path, serialise_story(story.fields, story.body))

    def _new_id(self) -> str:
        existing = self._all_ids()
        while True:
            candidate = secrets.token_hex(3)
            if candidate not in existing:
                return candidate

    def _bottom_rank(self, status: str, stories: list[Story]) -> int:
        ranks = [s.rank for s in stories if s.status == status and not s.archived]
        return (max(ranks) + RANK_STEP) if ranks else RANK_STEP

    def _check_status(self, status: str) -> str:
        if not self.config.has(status):
            raise SkaldError(f"invalid status '{status}' (columns: {', '.join(self.config.keys)})")
        return status

    def _resolve_blockers(self, story_id: Optional[str], blocked_by) -> list[str]:
        """Validate and canonicalise a blocked_by list. Cross-project refs are kept as written."""
        if not isinstance(blocked_by, (list, tuple)):
            raise SkaldError("blocked_by must be a list of story ids")
        out = set()
        for ref in blocked_by:
            if not isinstance(ref, str):
                raise SkaldError("blocked_by must be a list of story ids")
            ref = ref.strip().lower()
            if not ref:
                continue
            project, sid = split_ref(ref)
            if project is not None and project != self.name:
                if not REF_RE.match(ref):
                    raise SkaldError(f"invalid reference '{ref}' (expected project:id)")
                other = self.workspace.open(project) if self.workspace else None
                if other is not None and other.get_or_none(sid) is None:
                    raise NotFoundError(f"no story {sid} in project {project}")
                out.add(ref)
                continue
            full = self.resolve(sid)
            if full == story_id:
                raise SkaldError(f"{full} cannot block itself")
            out.add(full)
        return sorted(out)

    def _template_body(self, template: Optional[str]) -> str:
        if not template:
            return ""
        path = self.templates_dir / f"{template}.md"
        if not path.is_file():
            available = ", ".join(self.templates()) or "none"
            raise NotFoundError(f"no template '{template}' (available: {available})")
        return read_text(path)

    def templates(self) -> list[str]:
        return sorted(p.stem for p in self._paths(self.templates_dir))

    def create(self, title: str, status: Optional[str] = None, tags=(), blocked_by=(), body: str = "",
               assignee: str = "", template: Optional[str] = None, parent: Optional[str] = None,
               inherit: bool = True, created_at: Optional[str] = None, wrap: bool = True) -> tuple[Story, list[str]]:
        title = (title or "").strip()
        parent_story: Optional[Story] = None
        if parent:
            parent_story = self.get(self._local_parent(parent))
            if inherit:
                # A child belongs to its parent's epic, area, and lane unless told otherwise.
                tags = [t for t in parent_story.tags if split_facet(t)] + list(tags or [])
        if not title:
            raise SkaldError("title is required")
        status = self._check_status(status or self.config.default_key)
        blockers = self._resolve_blockers(None, list(blocked_by or []))
        stories, _ = self.load_all()
        story_id = self._new_id()
        slug = slugify(title)
        filename = f"{story_id}-{slug}.md" if slug else f"{story_id}.md"
        body = body or ""
        if body and not body.endswith("\n"):
            body += "\n"
        template_body = self._template_body(template)
        if template_body:
            full_body = template_body
            if not full_body.endswith("\n"):
                full_body += "\n"
            if body:
                full_body += "\n" + body
        elif not wrap or body.lstrip().startswith("## Requirements"):
            full_body = body.lstrip()  # the caller wrote the heading already, or asked for the body as is
        else:
            full_body = "## Requirements\n\n" + body
        stamp = now_iso()
        if created_at:
            when = parse_when(created_at)
            if when is None:
                raise SkaldError("--created-at must be YYYY-MM-DD HH:MM (UTC), YYYY-MM-DDTHH:MM:SSZ, or YYYY-MM-DD")
            stamp = when.strftime("%Y-%m-%dT%H:%M:%SZ")
        fields = {
            "title": title,
            "status": status,
            "rank": self._bottom_rank(status, stories),
            "tags": normalise_tags(list(tags or [])),
            "blocked_by": blockers,
            "assignee": (assignee or "").strip(),
            "created_at": stamp,
            "updated_at": stamp,
        }
        if parent_story is not None:
            fields["parent"] = parent_story.id
        story = Story(story_id, self.stories_dir / filename, fields, full_body)
        self._write(story, touch=not created_at)  # a backdated story keeps its given stamps
        warnings = []
        if self.config.warns_on(status):
            w = self.unmet_warning(story)
            if w:
                warnings.append(w)
        return story, warnings

    def _local_parent(self, ref: str) -> str:
        """A parent is local only: a cross-project reference is rejected rather than resolved."""
        if ":" in (ref or ""):
            raise SkaldError(f"a parent must be a story in this project, not '{ref}'")
        return self.resolve(ref)

    def children(self, story_id: str, stories: Optional[list[Story]] = None) -> list[Story]:
        stories = stories if stories is not None else self.load_all()[0]
        return [s for s in stories if s.parent == story_id]

    def _parent_chain(self, start: str, idx: dict[str, Story]) -> list[str]:
        """Ids from ``start`` upwards through parents, stopping at a missing story or a repeat."""
        chain, cur = [], start
        while cur and cur in idx and cur not in chain:
            chain.append(cur)
            cur = idx[cur].parent
        return chain

    def update(self, ref: str, *, title=None, status=None, rank=None, tags=None, blocked_by=None,
               assignee=None, order=None, parent=None,
               elsewhere: Optional[dict] = None) -> tuple[Story, list[str]]:
        story = self.get(ref)
        if story.archived:
            raise ConflictError(f"{story.id} is archived; unarchive it first")
        stories, _ = self.load_all()
        idx = self.index()
        warnings: list[str] = []
        status_changed = False
        deps_changed = False

        if title is not None:
            if not isinstance(title, str) or not title.strip():
                raise SkaldError("title must be a non-empty string")
            story.fields["title"] = title.strip()
        if status is not None:
            self._check_status(status)
            if status != story.status:
                old_index = self.config.index(story.status)
                old_role = self.config.role(story.status)
                story.fields["status"] = status
                story.fields["rank"] = self._bottom_rank(status, stories)
                status_changed = True
                a_done, a_total = acceptance_progress(story.body)
                if a_total and a_done < a_total and self._is_forward_gate(old_index, status):
                    warnings.append(
                        f"{story.id} moves to {status} with {a_total - a_done} of {a_total} acceptance criteria unchecked"
                    )
                if self.config.is_terminal(status):
                    open_children = [c for c in self.children(story.id, stories) if not self.config.is_terminal(c.status)]
                    if open_children:
                        warnings.append(
                            f"{story.id} moves to {status} with {len(open_children)} child(ren) still open: "
                            + ", ".join(c.id for c in open_children)
                        )
                # Leaving the backlog for ready is the human's gate; an open question means it is not decided yet.
                if old_role == "backlog" and self.config.role(status) == "ready":
                    open_qs = story.open_questions()
                    if open_qs:
                        warnings.append(
                            f"{story.id} moves to {status} with {len(open_qs)} open question(s); answer them with skald answer"
                        )
        if parent is not None:
            if parent in ("", "-"):
                story.fields.pop("parent", None)
            else:
                pid = self._local_parent(parent)
                if pid == story.id:
                    raise SkaldError(f"{story.id} cannot be its own parent")
                idx_all = {s.id: s for s in stories}
                if story.id in self._parent_chain(pid, idx_all):
                    raise SkaldError(f"{pid} is a descendant of {story.id}; that would make a cycle")
                story.fields["parent"] = pid
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
        if assignee is not None:
            if not isinstance(assignee, str):
                raise SkaldError("assignee must be a string")
            story.fields["assignee"] = assignee.strip()

        self._write(story)
        idx[story.id] = story

        if order is not None:
            self.reorder(story.status, order)
            story = self.get(story.id)

        if self.config.warns_on(story.status) and (status_changed or deps_changed):
            w = self.unmet_warning(story, idx)
            if w:
                warnings.append(w)
        column = self.config.column(story.status)
        if status_changed and self.config.role(status) == "active" and self.config.facet_limits:
            busy = self.busy_lanes(stories, elsewhere)
            for c in self.lane_conflicts(story, busy):
                warnings.append(f"{story.id} enters a busy lane: {c}")
        if status_changed and column and column.limit:
            count = sum(1 for s in self.index(include_archived=False).values() if s.status == column.key)
            if count > column.limit:
                warnings.append(f"column '{column.key}' is over its limit ({count}/{column.limit})")
        return story, warnings

    def _is_forward_gate(self, old_index: int, new_status: str) -> bool:
        """True for moves into a terminal column, or forward into an active column past the first one."""
        role = self.config.role(new_status)
        if role in ("done", "closed"):
            return True
        if role == "active":
            first_active = self.config.first_active_key
            new_index = self.config.index(new_status)
            return new_index > old_index and new_status != first_active
        return False

    def claim(self, ref: str, author: str, stale_days: Optional[int] = None,
              elsewhere: Optional[dict] = None) -> tuple[Story, list[str]]:
        """Assign the story to ``author`` and move it into the first active column if it is not active yet."""
        story = self.get(ref)
        author = (author or "").strip()
        if not author:
            raise SkaldError("an author is required to claim a story")
        pre: list[str] = []
        if story.assignee and story.assignee != author:
            stale = " (stale)" if _is_stale(story, stale_days) else ""
            pre.append(f"{story.id} was assigned to {story.assignee}{stale}; now {author}")
        for c in (elsewhere or {}).get(story.id, []):
            if c["assignee"] != author:
                pre.append(f"{story.id} is also claimed by {c['assignee']} on branch {c['branch']} ({c['status']})")
        kwargs: dict = {"assignee": author}
        role = self.config.role(story.status)
        target = self.config.first_active_key
        if role in ("backlog", "ready") and target:
            kwargs["status"] = target
        updated, warnings = self.update(story.id, elsewhere=elsewhere, **kwargs)
        return updated, pre + warnings

    def busy_lanes(self, stories: Optional[list[Story]] = None, elsewhere: Optional[dict] = None) -> dict[str, dict[str, list[str]]]:
        """For each limited facet key, the ids holding each value: active here, or claimed elsewhere.

        ``{key: {value: [ids]}}``. A story counts once, whether it is active in
        this working tree or active with an assignee on another branch or in
        another checkout (``elsewhere``).
        """
        limits = self.config.facet_limits
        if not limits:
            return {}
        stories = stories if stories is not None else self.load_all()[0]
        held = set(elsewhere or {})
        out: dict[str, dict[str, list[str]]] = {k: {} for k in limits}
        for s in stories:
            active = self.config.role(s.status) == "active" or s.id in held
            if not active:
                continue
            for tag in s.tags:
                parts = split_facet(tag)
                if parts and parts[0] in limits:
                    out[parts[0]].setdefault(parts[1], []).append(s.id)
        return out

    def lane_conflicts(self, story: Story, busy: dict[str, dict[str, list[str]]]) -> list[str]:
        """Warnings for each lane of ``story`` that is already at its limit, not counting the story itself."""
        out = []
        for tag in story.tags:
            parts = split_facet(tag)
            if not parts or parts[0] not in self.config.facet_limits:
                continue
            key, value = parts
            holders = [i for i in busy.get(key, {}).get(value, []) if i != story.id]
            limit = self.config.facet_limits[key]
            if len(holders) >= limit:
                out.append(f"lane {key}:{value} is busy ({len(holders)}/{limit}: {', '.join(holders)})")
        return out

    def next_story(self, for_author: Optional[str] = None, stale_days: Optional[int] = None,
                   elsewhere: Optional[dict] = None, warnings: Optional[list] = None,
                   tag: Optional[str] = None) -> Optional[Story]:
        """First ready, unblocked story available to ``for_author``.

        A story assigned to someone else is skipped unless the assignment is stale
        (untouched for ``stale_days``), in which case it is offered with a warning.
        A story claimed by someone else on another branch (``elsewhere``) is skipped
        with a warning so parallel agents do not duplicate work. With ``tag`` only
        stories carrying it are considered, so a loop that routes work by a facet
        such as ``effort:deep`` asks for its next story in one call.
        """
        stories, _ = self.load_all()
        idx = {s.id: s for s in stories}
        ready = set(self.config.keys_with_role("ready"))
        notes = warnings if warnings is not None else []
        busy = self.busy_lanes(stories, elsewhere)
        tag = (tag or "").strip().lower() or None
        for s in stories:
            if s.status not in ready:
                continue
            if tag and tag not in s.tags:
                continue
            if self.unmet(s, idx):
                continue
            claims = [c for c in (elsewhere or {}).get(s.id, []) if c["assignee"] != for_author]
            if claims:
                c = claims[0]
                notes.append(f"skipping {s.id}: claimed by {c['assignee']} on branch {c['branch']} ({c['status']})")
                continue
            conflicts = self.lane_conflicts(s, busy)
            if conflicts:
                # Order is what dependencies express; a lane says two stories must not run at once.
                notes.append(f"skipping {s.id}: " + "; ".join(conflicts))
                continue
            if s.assignee and s.assignee != for_author:
                if _is_stale(s, stale_days):
                    notes.append(f"{s.id} was assigned to {s.assignee} but untouched for {stale_days}+ days; offering it")
                else:
                    continue
            return s
        return None

    def reorder(self, status: str, ids) -> list[Story]:
        self._check_status(status)
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

    def answer(self, ref: str, text: str, author: str = "agent", question=None, all_open: bool = False,
               withdraw: bool = False) -> tuple[Story, list[dict]]:
        """Close questions with a decision note whose leading lines name them; nothing else closes one.

        ``question`` is a stable number (``3`` or ``"Q3"``). Without it, the one open question is
        the target; several open refuse rather than guess, and none open refuses (record a plain
        decision with ``note --kind decision``). ``all_open`` names every open question.
        ``withdraw`` records the drop of a question instead of an answer. Returns the story and
        the questions closed.
        """
        open_qs = self.get(ref).open_questions()
        text = (text or "").strip()
        if not text:
            raise SkaldError("the answer text is required" if not withdraw else "say why the question is withdrawn")
        if question is not None and all_open:
            raise SkaldError("--question and --all are alternatives")
        if not open_qs:
            raise SkaldError("this story has no open question; record a decision with skald note --kind decision")
        if all_open:
            targets = open_qs
        elif question is not None:
            number = parse_question_ref(question)
            targets = [q for q in open_qs if q["number"] == number]
            if not targets:
                closed = [q for q in self.get(ref).questions() if q["number"] == number]
                if closed:
                    raise SkaldError(f"Q{number} is already {closed[0]['closed_by']['how']} ({closed[0]['closed_by']['stamp']} by {closed[0]['closed_by']['author']})")
                raise SkaldError(f"no question Q{number}; open: {', '.join('Q' + str(q['number']) for q in open_qs)}")
        elif len(open_qs) == 1:
            targets = open_qs
        else:
            raise SkaldError(f"{len(open_qs)} questions are open ({', '.join('Q' + str(q['number']) for q in open_qs)}); "
                             f"say which with --question N, or --all")
        lines = [answer_line(q, withdraw) for q in targets]
        story = self.append_note(ref, "\n".join(lines) + "\n" + text, author, "decision")
        return story, targets

    def append_note(self, ref: str, text: str, author: str = "agent", kind: Optional[str] = None,
                    at: Optional[str] = None) -> Story:
        """Append a dated note. ``at`` backdates the heading (a migration primitive); the default is now."""
        text = (text or "").strip()
        if not text:
            raise SkaldError("note text is required")
        author = (author or "").strip() or "agent"
        if re.search(r"[\[\]\n]", author):
            raise SkaldError("author may not contain brackets or newlines")
        kind = (kind or "").strip().lower()
        if kind and not KIND_RE.match(kind):
            raise SkaldError("note kind must be a short lowercase word, e.g. handoff, decision, blocker")
        story = self.get(ref)
        if story.archived:
            raise ConflictError(f"{story.id} is archived; unarchive it first")
        stamp = note_stamp()
        if at:
            when = parse_when(at)
            if when is None:
                raise SkaldError("--at must be YYYY-MM-DD HH:MM (UTC), YYYY-MM-DDTHH:MM:SSZ, or YYYY-MM-DD")
            stamp = when.strftime("%Y-%m-%d %H:%M UTC")
        body = story.body.rstrip("\n")
        body = body + "\n\n" if body.strip() else ""
        suffix = f" · {kind}" if kind and kind != "note" else ""
        body += f"## [{author}] {stamp}{suffix}\n{text}\n"
        story.body = body
        self._write(story)
        return story

    def write_body(self, ref: str, body: str, base_sha256: Optional[str]) -> Story:
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
        stories, _ = self.load_all(include_archived=True)
        return [s for s in stories if any(split_ref(b) in ((None, story_id), (self.name, story_id)) for b in s.blocked_by)]

    def delete(self, ref: str, force: bool = False, notes: Optional[list] = None) -> Story:
        """Delete a story. With ``force``, references to it are cleared rather than left dangling,
        and each change is described in ``notes``: the backlog is never left in a state ``check`` calls corrupt."""
        story = self.get(ref)
        deps = self.dependents(story.id)
        if deps and not force:
            raise ConflictError(
                f"{story.id} is a dependency of {', '.join(d.id for d in deps)}; use --force to delete anyway"
            )
        kids = self.children(story.id)
        if kids and not force:
            raise ConflictError(
                f"{story.id} is the parent of {', '.join(k.id for k in kids)}; use --force to delete anyway"
            )
        for d in deps:
            keep = [b for b in d.blocked_by if split_ref(b)[1] != story.id or split_ref(b)[0] not in (None, self.name)]
            d.fields["blocked_by"] = keep
            self._write(d)
            if notes is not None:
                notes.append(f"removed {story.id} from blocked_by of {d.id}")
        for k in kids:
            k.fields.pop("parent", None)
            self._write(k)
            if notes is not None:
                notes.append(f"cleared parent of {k.id}")
        os.unlink(story.path)
        return story

    def mark_released(self, ref: str, version: str) -> Story:
        """Record the version a story shipped in (``released`` in the frontmatter)."""
        story = self.get(ref)
        if story.archived:
            raise ConflictError(f"{story.id} is archived; unarchive it first")
        story.fields["released"] = version
        self._write(story)
        return story

    def archive(self, dry_run: bool = False, ids=None) -> list[Story]:
        """Move every story in a terminal column to ``.skald/archive/``, or only ``ids``.

        Every id given must be in a terminal column; otherwise nothing is moved.
        """
        stories, _ = self.load_all()
        if ids is not None:
            wanted = [self.resolve(ref) for ref in ids]
            by_id = {s.id: s for s in stories}
            missing = [i for i in wanted if i not in by_id]
            if missing:
                raise NotFoundError(f"not in the backlog: {', '.join(missing)}")
            blocked = [i for i in wanted if not self.config.is_terminal(by_id[i].status)]
            if blocked:
                raise SkaldError(f"not in a done or closed column: {', '.join(blocked)}")
            stories = [by_id[i] for i in dict.fromkeys(wanted)]
        moved = []
        for s in stories:
            if self.config.is_terminal(s.status):
                if not dry_run:
                    self.archive_dir.mkdir(parents=True, exist_ok=True)
                    os.replace(s.path, self.archive_dir / s.path.name)
                    s.path = self.archive_dir / s.path.name
                    s.archived = True
                moved.append(s)
        return moved

    def unarchive(self, ref: str) -> Story:
        story = self.get(ref)
        if not story.archived:
            raise SkaldError(f"{story.id} is not archived")
        target = self.stories_dir / story.path.name
        os.replace(story.path, target)
        story.path = target
        story.archived = False
        return story

    # -- checks ----------------------------------------------------------

    def check(self) -> tuple[list[str], list[str]]:
        """Validate every story file. Returns (problems, warnings)."""
        problems: list[str] = []
        warnings: list[str] = []
        stories: list[Story] = []
        seen_ids: dict[str, str] = {}
        for directory, archived in ((self.stories_dir, False), (self.archive_dir, True)):
            for path in self._paths(directory):
                try:
                    raw = read_text(path)
                except OSError as e:
                    problems.append(f"{path.name}: {e}")
                    continue
                if CONFLICT_RE.search(raw):
                    problems.append(f"{path.name}: contains git conflict markers")
                    continue
                try:
                    story = self._read(path, archived)
                except CorruptStoryError as e:
                    problems.append(str(e))
                    continue
                if story.id in seen_ids:
                    problems.append(f"{path.name}: duplicate id {story.id} (also {seen_ids[story.id]})")
                    continue
                seen_ids[story.id] = path.name
                stories.append(story)
        if self.stories_dir.is_dir():
            for p in self.stories_dir.iterdir():
                if p.is_file() and p.suffix == ".md" and id_from_filename(p.name) is None:
                    pass  # reported above via _read
        idx = {s.id: s for s in stories}
        for s in stories:
            if not self.config.has(s.status):
                problems.append(
                    f"{s.path.name}: status '{s.status}' is not a column in config.json ({', '.join(self.config.keys)})"
                )
            if s.archived and not self.config.is_terminal(s.status):
                warnings.append(f"{s.path.name}: archived but status '{s.status}' is not terminal")
            if not s.archived:
                reopened = reopened_questions(s.notes())
                if reopened:
                    labels = ", ".join(f"Q{q['number']}" for q in reopened)
                    warnings.append(f"{s.path.name}: {labels} open again: a plain decision followed them, which closed questions "
                                    f"before 0.5 and no longer does; skald answer {s.id} --question N or --all")
            for b in s.blocked_by:
                if not REF_RE.match(b):
                    problems.append(f"{s.path.name}: blocked_by entry '{b}' is not a valid reference")
                    continue
                project, sid = split_ref(b)
                if project is None or project == self.name:
                    if sid == s.id:
                        problems.append(f"{s.path.name}: blocked by itself")
                    elif sid not in idx:
                        problems.append(f"{s.path.name}: blocked_by references missing story {sid}")
                else:
                    other = self.workspace.open(project) if self.workspace else None
                    if other is None:
                        warnings.append(f"{s.path.name}: blocked_by references project '{project}', which is not registered on this machine")
                    elif other.get_or_none(sid) is None:
                        problems.append(f"{s.path.name}: blocked_by references missing story {project}:{sid}")
        for s in stories:
            if s.parent and s.parent not in idx:
                problems.append(f"{s.path.name}: parent references missing story {s.parent}")
            elif s.parent == s.id:
                problems.append(f"{s.path.name}: is its own parent")
        seen_parent_cycles = set()
        for s in stories:
            chain = self._parent_chain(s.id, idx)
            last = idx[chain[-1]].parent if chain else ""
            if last and last in chain:
                key = frozenset(chain[chain.index(last):])
                if key not in seen_parent_cycles:
                    seen_parent_cycles.add(key)
                    problems.append("parent cycle: " + " -> ".join(chain[chain.index(last):] + [last]))
        reported = set()
        for s in stories:
            cycle = self._cycle_through(s.id, s.blocked_by, idx)
            if cycle:
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    problems.append(f"dependency cycle: {' -> '.join(cycle)}")
        return problems, warnings

    # -- derived views ---------------------------------------------------

    def story_dict(self, story: Story, idx: Optional[dict[str, Story]] = None, stale_days: Optional[int] = None,
                   compact: bool = False) -> dict:
        d = story.to_dict(compact=compact)
        d["project"] = self.name
        states = self.dep_states(story, idx)
        if not compact:
            d["deps"] = [s.to_dict() for s in states]
            d["role"] = self.config.role(story.status)
        d["unmet"] = [s.ref for s in states if not s.satisfied]
        d["blocked"] = bool(d["unmet"])
        if idx is not None:
            kids = [s for s in idx.values() if s.parent == story.id and not s.archived]
            if kids:
                d["children"] = {"total": len(kids), "done": sum(1 for k in kids if self.config.is_terminal(k.status))}
        d["stale"] = False
        if stale_days and self.config.role(story.status) == "active":
            updated = parse_iso(story.updated_at)
            if updated is not None:
                from datetime import datetime, timezone

                age = datetime.now(timezone.utc) - updated
                d["stale"] = age.days >= stale_days
        return d


# --------------------------------------------------------------------------
# Read-only snapshots of other branches
# --------------------------------------------------------------------------


class Snapshot:
    """A project's stories as they are on a git ref, read from objects, never from the worktree.

    Duck-types the read side of ``Store`` (``config``, ``name``, ``load_all``,
    ``unmet``, ``story_dict``, ``get``) so listings work unchanged. Dependencies
    resolve only within the snapshot; cross-project references are ``unavailable``.
    """

    readonly = True

    def __init__(self, ref: str, sha: str, config: ProjectConfig, stories: list[Story], warnings: list[str]):
        self.ref = ref
        self.sha = sha
        self.config = config
        self.name = config.name
        self._stories = sorted(stories, key=self.sort_key)
        self.warnings = warnings

    def sort_key(self, story: Story):
        return (self.config.index(story.status), story.rank, story.created_at, story.id)

    def load_all(self, include_archived: bool = False) -> tuple[list[Story], list[str]]:
        stories = [s for s in self._stories if include_archived or not s.archived]
        return stories, list(self.warnings)

    def index(self, include_archived: bool = True) -> dict[str, Story]:
        return {s.id: s for s in self._stories if include_archived or not s.archived}

    def get(self, ref: str) -> Story:
        ref = (ref or "").strip().lower()
        matches = [s for s in self._stories if s.id.startswith(ref)] if ref else []
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise NotFoundError(f"no story matches '{ref}' on {self.ref}")
        raise SkaldError(f"'{ref}' is ambiguous on {self.ref}: {', '.join(s.id for s in matches)}")

    def dep_states(self, story: Story, idx: Optional[dict[str, Story]] = None) -> list[DepState]:
        idx = idx if idx is not None else self.index()
        out = []
        for ref in story.blocked_by:
            project, sid = split_ref(ref)
            if project is not None and project != self.name:
                out.append(DepState(ref, "unavailable", False))
                continue
            target = idx.get(sid)
            if target is None:
                out.append(DepState(ref, "missing", False))
            elif target.archived:
                out.append(DepState(ref, "archived", True, self.config.is_closed(target.status)))
            else:
                terminal = self.config.is_terminal(target.status)
                out.append(DepState(ref, target.status, terminal, terminal and self.config.is_closed(target.status)))
        return out

    def unmet(self, story: Story, idx: Optional[dict[str, Story]] = None) -> list[str]:
        return [d.ref for d in self.dep_states(story, idx) if not d.satisfied]

    def story_dict(self, story: Story, idx: Optional[dict[str, Story]] = None, stale_days: Optional[int] = None,
                   compact: bool = False) -> dict:
        d = story.to_dict(compact=compact)
        d["project"] = self.name
        d["ref"] = self.ref
        states = self.dep_states(story, idx)
        if not compact:
            d["deps"] = [s.to_dict() for s in states]
            d["role"] = self.config.role(story.status)
        d["unmet"] = [s.ref for s in states if not s.satisfied]
        d["blocked"] = bool(d["unmet"])
        d["stale"] = False
        return d


def _snapshot_of(store: "Store", ref: str) -> Snapshot:
    from . import gitutil

    repo = gitutil.root(store.dir)
    if repo is None:
        raise SkaldError(f"{store.dir} is not inside a git repository")
    sha = gitutil.rev_parse(repo, ref)
    if sha is None:
        raise NotFoundError(f"unknown git ref '{ref}'")
    try:
        rel = store.dir.relative_to(repo).as_posix()
    except ValueError:
        raise SkaldError(f"{store.dir} is outside the repository {repo}") from None
    story_paths = gitutil.ls_tree(repo, ref, f"{rel}/stories")
    archive_paths = gitutil.ls_tree(repo, ref, f"{rel}/archive")
    wanted = story_paths + archive_paths + [f"{rel}/config.json"]
    blobs = gitutil.cat_file_batch(repo, ref, wanted)
    config = store.config
    cfg_text = blobs.get(f"{rel}/config.json")
    if cfg_text:
        try:
            config = ProjectConfig.from_dict(json.loads(cfg_text), f"{ref}:{rel}/config.json")
        except (ValueError, SkaldError):
            config = store.config
    stories, warnings = [], []
    for path, archived in [(p, False) for p in story_paths] + [(p, True) for p in archive_paths]:
        name = path.rsplit("/", 1)[-1]
        sid = id_from_filename(name)
        text = blobs.get(path)
        if sid is None or text is None:
            continue
        try:
            fields, body = parse_story_text(text, f"{ref}:{name}")
        except CorruptStoryError as e:
            warnings.append(f"skipping corrupt story {e}")
            continue
        stories.append(Story(sid, Path(path), fields, body, archived))
    return Snapshot(ref, sha, config, stories, warnings)


def _branch_diff(store: "Store", snap: Snapshot) -> dict:
    """Compare a snapshot with the working tree. Returns ids grouped by relationship."""
    here = store.index(include_archived=True)
    there = snap.index(include_archived=True)
    only_there = [there[i] for i in sorted(set(there) - set(here))]
    only_here = [here[i] for i in sorted(set(here) - set(there))]
    differ = []
    for sid in sorted(set(here) & set(there)):
        h, t = here[sid], there[sid]
        if h.status != t.status or h.title != t.title or h.archived != t.archived:
            differ.append((h, t))
    return {"only_there": only_there, "only_here": only_here, "differ": differ}


def _claims_elsewhere(store: "Store", include_remote: bool = False, checkouts=None) -> dict[str, list[dict]]:
    """Active stories with an assignee on other branches: ``{id: [{branch, assignee, status}]}``.

    ``checkouts`` are stores for other working trees of the same project. Their
    claims are read from disk, so an agent that claimed in a worktree is seen
    before it commits; such entries carry ``checkout`` (the path). A working
    tree stands in for its branch, so the branch is not scanned a second time.
    """
    from . import gitutil

    out: dict[str, list[dict]] = {}
    covered: set = set()
    for co in checkouts or []:
        co_repo = gitutil.root(co.dir)
        label = (gitutil.branch(co_repo) if co_repo else None) or "working tree"
        covered.add(label)
        try:
            stories = co.load_all()[0]
        except SkaldError:
            continue
        for st in stories:
            if st.assignee and co.config.role(st.status) == "active":
                out.setdefault(st.id, []).append(
                    {"branch": label, "assignee": st.assignee, "status": st.status, "checkout": str(co.dir)})
    repo = gitutil.root(store.dir)
    if repo is None:
        return out
    current = gitutil.branch(repo)
    for b in gitutil.branches(repo):
        if b["name"] == current or b["name"] in covered or (b["remote"] and not include_remote):
            continue
        try:
            snap = store.snapshot(b["name"])
        except SkaldError:
            continue
        for st in snap.load_all()[0]:
            if st.assignee and snap.config.role(st.status) == "active":
                out.setdefault(st.id, []).append({"branch": b["name"], "assignee": st.assignee, "status": st.status})
    return out


def _is_stale(story: Story, stale_days: Optional[int]) -> bool:
    if not stale_days:
        return False
    updated = parse_iso(story.updated_at)
    if updated is None:
        return False
    from datetime import datetime, timezone

    return (datetime.now(timezone.utc) - updated).days >= stale_days


Store.snapshot = _snapshot_of
Store.branch_diff = _branch_diff
Store.claims_elsewhere = _claims_elsewhere
Store.readonly = False


# --------------------------------------------------------------------------
# Facets: tags of the form key:value
# --------------------------------------------------------------------------


def split_facet(tag: str) -> Optional[tuple[str, str]]:
    """``"epic:auth"`` -> ``("epic", "auth")``; a plain tag -> None."""
    if ":" not in tag:
        return None
    key, _, value = tag.partition(":")
    key, value = key.strip(), value.strip()
    if not key or not value:
        return None
    return key, value


def facets(stories: list[Story], config: ProjectConfig) -> dict[str, dict[str, dict]]:
    """Group stories by ``key:value`` tags: ``{key: {value: {total, done, open, ids}}}``."""
    out: dict[str, dict[str, dict]] = {}
    for s in stories:
        for tag in s.tags:
            parts = split_facet(tag)
            if not parts:
                continue
            key, value = parts
            bucket = out.setdefault(key, {}).setdefault(value, {"total": 0, "done": 0, "open": 0, "ids": []})
            bucket["total"] += 1
            if config.is_terminal(s.status):
                bucket["done"] += 1
            else:
                bucket["open"] += 1
            bucket["ids"].append(s.id)
    return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}


# --------------------------------------------------------------------------
# Diffs between two states (snapshots or the working tree)
# --------------------------------------------------------------------------


def diff_states(base, head) -> dict:
    """Compare two duck-typed states (``index(include_archived=True)``) by story id."""
    a = base.index(include_archived=True) if base is not None else {}
    b = head.index(include_archived=True)
    added = [b[i] for i in sorted(set(b) - set(a))]
    removed = [a[i] for i in sorted(set(a) - set(b))]
    changes = []
    for sid in sorted(set(a) & set(b)):
        x, y = a[sid], b[sid]
        fields = {}
        if x.status != y.status:
            fields["status"] = (x.status, y.status)
        if x.assignee != y.assignee:
            fields["assignee"] = (x.assignee, y.assignee)
        if x.title != y.title:
            fields["title"] = (x.title, y.title)
        if x.archived != y.archived:
            fields["archived"] = (x.archived, y.archived)
        if sorted(x.tags) != sorted(y.tags):
            fields["tags"] = (x.tags, y.tags)
        if x.blocked_by != y.blocked_by:
            fields["blocked_by"] = (x.blocked_by, y.blocked_by)
        nx, ny = len(parse_notes(x.body)), len(parse_notes(y.body))
        notes_added = max(0, ny - nx)
        body_changed = x.body != y.body and not notes_added
        if fields or notes_added or body_changed:
            changes.append({"story": y, "before": x, "fields": fields, "notes_added": notes_added, "body_changed": body_changed})
    return {"added": added, "removed": removed, "changed": changes}
