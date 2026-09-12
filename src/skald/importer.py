"""``skald import``: bring a folder of Markdown records into the backlog, driven by a mapping file.

The tool never guesses at another project's conventions: every extraction is
a rule in the mapping, and a dry run shows exactly what each rule produced
before anything is written. Bodies are kept byte for byte apart from the
title line, stripped lines, and extracted note blocks; those blocks become
backdated notes in their original order.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import gitutil
from .errors import SkaldError
from .util import atomic_write, parse_when, read_text

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist"}
H1_RE = re.compile(r"^#\s+(.+?)\s*$")
H2_RE = re.compile(r"^##\s+")


@dataclass
class Note:
    kind: str
    text: str
    at: Optional[str]  # YYYY-MM-DD..., or None for the story's created_at


@dataclass
class Plan:
    source: Path
    relpath: str
    title: str
    status: Optional[str]
    tags: list[str]
    created_at: Optional[str]
    body: str
    notes: list[Note] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    created_from: str = "now"  # regex, git, or now


# ---------------------------------------------------------------- mapping

def load_mapping(path: Optional[Path]) -> dict:
    if path is None:
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise SkaldError(f"{path}: {e}") from None
    except ValueError as e:
        raise SkaldError(f"{path}: not valid JSON ({e})") from None
    if not isinstance(data, dict):
        raise SkaldError(f"{path}: the mapping must be a JSON object")
    for key in ("status", "tags", "notes", "strip", "exclude"):
        if key in data and not isinstance(data[key], list):
            raise SkaldError(f"{path}: '{key}' must be a list")
    return data


SUBJECTS = ("filename", "relpath", "path", "body")
CREATED_FALLBACKS = ("git-added", "now", "error")
KIND_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


def validate_mapping(mapping: dict, columns: Optional[list[str]] = None) -> list[str]:
    """Every problem in the mapping, each naming its rule, so a bad mapping fails before any file is read.

    Regexes must compile; a ``$N`` in a tag template must not exceed the regex's
    groups; ``on`` must be a subject; a status must be a column when the columns
    are known; a notes rule needs ``block`` or ``section`` and a valid kind.
    """
    out: list[str] = []

    def rx(pattern, where) -> Optional[re.Pattern]:
        if not isinstance(pattern, str):
            out.append(f"{where}: must be a string")
            return None
        try:
            return re.compile(pattern)
        except re.error as e:
            out.append(f"{where}: bad regex {pattern!r} ({e})")
            return None

    def check_on(rule, where):
        if rule.get("on", "body") not in SUBJECTS:
            out.append(f"{where}: 'on' must be one of {', '.join(SUBJECTS)} (got {rule.get('on')!r})")

    def check_rules(key):
        rules = mapping.get(key, [])
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                out.append(f"{key}[{i}]: must be an object")
        return [r for r in rules if isinstance(r, dict)]

    ca = mapping.get("created_at")
    if ca is not None:
        if not isinstance(ca, dict):
            out.append("created_at: must be an object with 'regex'")
        else:
            m = rx(ca.get("regex", ""), "created_at.regex") if "regex" in ca else None
            if "regex" not in ca and ca.get("fallback", "git-added") == "error":
                out.append("created_at: 'error' needs a regex to fail on")
            group = ca.get("group", 1)
            if m and (not isinstance(group, int) or group < 1 or group > m.groups):
                out.append(f"created_at: 'group' is {group!r} but the regex has {m.groups} group(s)")
            if ca.get("fallback", "git-added") not in CREATED_FALLBACKS:
                out.append(f"created_at: 'fallback' must be one of {', '.join(CREATED_FALLBACKS)} (got {ca.get('fallback')!r})")

    for i, rule in enumerate(check_rules("status")):
        where = f"status[{i}]"
        if "regex" in rule:
            rx(rule["regex"], f"{where}.regex")
            check_on(rule, where)
            if "status" not in rule:
                out.append(f"{where}: a regex rule needs 'status'")
        elif "default" not in rule:
            out.append(f"{where}: needs 'regex' and 'status', or 'default'")
        value = rule.get("status", rule.get("default"))
        if columns is not None and value is not None and value not in columns:
            out.append(f"{where}: '{value}' is not a column (columns: {', '.join(columns)})")

    for i, rule in enumerate(check_rules("tags")):
        where = f"tags[{i}]"
        if "regex" not in rule or "tag" not in rule:
            out.append(f"{where}: needs 'regex' and 'tag'")
            continue
        m = rx(rule["regex"], f"{where}.regex")
        check_on(rule, where)
        if m is not None and isinstance(rule["tag"], str):
            for n in re.findall(r"\$(\d+)", rule["tag"]):
                if int(n) > m.groups:
                    out.append(f"{where}: template refers to ${n} but the regex has {m.groups} group(s)")

    for i, rule in enumerate(check_rules("notes")):
        where = f"notes[{i}]"
        kind = rule.get("kind", "note")
        if not isinstance(kind, str) or not KIND_RE.match(kind):
            out.append(f"{where}: kind must be a short lowercase word (got {kind!r})")
        if "block" in rule:
            m = rx(rule["block"], f"{where}.block")
            if rule.get("until") is not None:
                rx(rule["until"], f"{where}.until")
            dg = rule.get("date_group")
            if dg is not None and m is not None and (not isinstance(dg, int) or dg < 1 or dg > m.groups):
                out.append(f"{where}: 'date_group' is {dg!r} but the block regex has {m.groups} group(s)")
        elif "section" in rule:
            rx(rule["section"], f"{where}.section")
            if rule.get("per") not in (None, "bullet"):
                out.append(f"{where}: 'per' must be 'bullet' when given (got {rule.get('per')!r})")
        else:
            out.append(f"{where}: needs 'block' or 'section'")

    for i, pattern in enumerate(mapping.get("strip", [])):
        rx(pattern, f"strip[{i}]")
    for i, g in enumerate(mapping.get("exclude", [])):
        if not isinstance(g, str):
            out.append(f"exclude[{i}]: must be a string")
    req = mapping.get("requirements")
    if req is not None and not isinstance(req, dict):
        out.append("requirements: must be an object")
    return out


def _rx(pattern: str, where: str, flags: int = 0) -> re.Pattern:
    try:
        return re.compile(pattern, flags)
    except re.error as e:
        raise SkaldError(f"mapping: bad regex in {where}: {pattern!r} ({e})") from None


def _glob_to_re(glob: str) -> re.Pattern:
    """A path glob with ``**`` for any directories, ``*`` within a segment, ``?`` one character."""
    out = ""
    i = 0
    while i < len(glob):
        c = glob[i]
        if glob.startswith("**/", i):
            out += r"(?:.*/)?"
            i += 3
        elif glob.startswith("**", i):
            out += r".*"
            i += 2
        elif c == "*":
            out += r"[^/]*"
            i += 1
        elif c == "?":
            out += r"[^/]"
            i += 1
        else:
            out += re.escape(c)
            i += 1
    return re.compile("^" + out + "$")


def excluded(relpath: str, mapping: dict) -> bool:
    return any(_glob_to_re(g).match(relpath) for g in mapping.get("exclude", []))


def _subject(rule: dict, text: str, relpath: str, path: Optional[str] = None) -> str:
    """What a rule's regex runs over: the filename, the path under the imported directory,
    the path under the project root, or the body."""
    on = rule.get("on", "body")
    if on == "filename":
        return Path(relpath).name
    if on == "relpath":
        return relpath
    if on == "path":
        return path if path is not None else relpath
    if on == "body":
        return text
    raise SkaldError(f"mapping: 'on' must be one of {', '.join(SUBJECTS)} (got {on!r})")


def git_added(source: Path) -> Optional[str]:
    """When git first added ``source`` (author date, ISO), following renames; None outside git or unknown."""
    source = Path(source)
    # %at is the author date as a Unix timestamp: no ISO variant to parse (git 2.55 prints UTC as
    # "Z", which datetime.fromisoformat accepts only from Python 3.11).
    try:
        proc = gitutil._run(["log", "--follow", "--diff-filter=A", "--format=%at", "--", source.name],
                            cwd=source.parent)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    stamps = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    if not stamps or not stamps[-1].isdigit():
        return None
    return datetime.fromtimestamp(int(stamps[-1]), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expand(template: str, m: re.Match) -> str:
    """``$1`` style groups in a mapping value."""
    return re.sub(r"\$(\d+)", lambda g: m.group(int(g.group(1))) or "", template)


# ---------------------------------------------------------------- planning

def plan_text(text: str, relpath: str, source: Path, mapping: dict, default_status: Optional[str] = None,
              path: Optional[str] = None, extra_tags: Optional[list[str]] = None) -> Plan:
    """The story one record becomes. ``relpath`` is the record's path under the directory it was
    given under; ``path`` its path under the project root, for ``"on": "path"`` rules."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")  # line endings are the one byte-level change
    lines = text.splitlines()
    problems: list[str] = []

    # Title: the first H1, dropped from the body; else the filename.
    title = None
    for i, line in enumerate(lines):
        m = H1_RE.match(line)
        if m:
            title = m.group(1)
            del lines[i]
            if i < len(lines) and not lines[i].strip():
                del lines[i]
            break
    if not title:
        title = Path(relpath).stem.replace("-", " ").replace("_", " ").strip() or relpath

    # created_at: a regex over the original text, else the commit that added the file, else now.
    created_at = None
    created_from = "now"
    rule = mapping.get("created_at") or {}
    fallback = rule.get("fallback", "git-added")
    if rule.get("regex"):
        m = _rx(rule["regex"], "created_at", re.M).search(text)
        if m:
            raw = m.group(int(rule.get("group", 1)))
            if parse_when(raw) is None:
                problems.append(f"created_at {raw!r} is not a date")
            else:
                created_at, created_from = raw, "regex"
        elif fallback == "error":
            problems.append("created_at: no match")
    if created_at is None and fallback == "git-added":
        added = git_added(source)
        if added:
            created_at, created_from = added, "git"

    # status: first matching rule, else the default rule, else the CLI default.
    status = default_status
    for rule in mapping.get("status", []):
        if "regex" in rule:
            if _rx(rule["regex"], "status").search(_subject(rule, text, relpath, path)):
                status = rule.get("status")
                break
        elif "default" in rule and status is None:
            status = rule["default"]

    # tags: every matching rule contributes one, with $1 substitution.
    tags: list[str] = []
    for rule in mapping.get("tags", []):
        m = _rx(rule["regex"], "tags").search(_subject(rule, text, relpath, path))
        if m:
            tag = _expand(rule["tag"], m).strip().lower()
            if tag and tag not in tags:
                tags.append(tag)
    for tag in extra_tags or []:
        tag = tag.strip().lower()
        if tag and tag not in tags:
            tags.append(tag)

    # notes: blocks and sections come out of the body in order and become notes.
    notes: list[Note] = []
    keep: list[Optional[str]] = list(lines)  # None marks a line taken by a note
    for rule in mapping.get("notes", []):
        kind = rule.get("kind", "note")
        if "block" in rule:
            start = _rx(rule["block"], "notes.block")
            until = _rx(rule["until"], "notes.until") if rule.get("until") else None
            i = 0
            while i < len(keep):
                line = keep[i]
                if line is None or not start.match(line):
                    i += 1
                    continue
                j = i + 1
                while j < len(keep) and keep[j] is not None and not (until and until.match(keep[j])):
                    j += 1
                block = [keep[k] for k in range(i, j) if keep[k] is not None]
                while block and not block[-1].strip():
                    block.pop()
                m = start.match(line)
                at = m.group(int(rule["date_group"])) if rule.get("date_group") and m.groups() else None
                if block and all(b.startswith(">") for b in block if b.strip()):
                    block = [re.sub(r"^>\s?", "", b) for b in block]
                notes.append(Note(kind, "\n".join(block).strip(), at))
                for k in range(i, j):
                    keep[k] = None
                i = j
        elif "section" in rule:
            head = _rx(rule["section"], "notes.section")
            i = 0
            while i < len(keep):
                line = keep[i]
                if line is None or not (H2_RE.match(line) and head.match(line)):
                    i += 1
                    continue
                j = i + 1
                while j < len(keep) and not (keep[j] is not None and H2_RE.match(keep[j])):
                    j += 1
                body_lines = [keep[k] for k in range(i + 1, j) if keep[k] is not None]
                if rule.get("per") == "bullet":
                    item: list[str] = []
                    items: list[str] = []
                    for b in body_lines:
                        if re.match(r"^\s*[-*]\s+", b):
                            if item:
                                items.append("\n".join(item).strip())
                            item = [re.sub(r"^\s*[-*]\s+", "", b)]
                        elif item and b.strip():
                            item.append(b.strip())
                    if item:
                        items.append("\n".join(item).strip())
                    for it in items:
                        notes.append(Note(kind, it, None))
                else:
                    text_block = "\n".join(body_lines).strip()
                    if text_block:
                        notes.append(Note(kind, text_block, None))
                for k in range(i, j):
                    keep[k] = None
                i = j
        else:
            raise SkaldError("mapping: each notes rule needs 'block' or 'section'")

    # strip: whole lines to drop.
    strips = [_rx(p, "strip") for p in mapping.get("strip", [])]
    body_lines = [l for l in keep if l is not None and not any(s.match(l) for s in strips)]
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(body_lines)).strip("\n") + "\n"  # the gap an extracted block leaves

    # requirements: wrap under the heading unless one is present (the default).
    req = mapping.get("requirements", {})
    heading = req.get("wrap_body_under", "## Requirements")
    unless = req.get("unless_heading_present", True)
    has = any(re.match(r"^##\s+requirements\s*$", l, re.I) for l in body_lines)
    if not (unless and has) and not body.lstrip().startswith(heading):
        body = f"{heading}\n\n{body}"
    return Plan(source, relpath, title, status, tags, created_at, body, notes, problems, created_from)


def collect(paths: list[Path], mapping: dict) -> list[tuple[Path, str]]:
    """Every Markdown file under the given paths with its path relative to the directory it was given under."""
    out: list[tuple[Path, str]] = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
                for f in sorted(filenames):
                    if f.endswith(".md"):
                        full = Path(dirpath) / f
                        rel = full.relative_to(p).as_posix()
                        if not excluded(rel, mapping):
                            out.append((full, rel))
        elif p.is_file():
            if not excluded(p.name, mapping):
                out.append((p, p.name))
        else:
            raise SkaldError(f"{p}: no such file or directory")
    return out


# ---------------------------------------------------------------- links

LINK_TOKEN_RE = re.compile(r"(?<![\w/])((?:\.\.?/)?(?:[\w.-]+/)*[\w.-]+\.md)(?![\w/])")
TEXT_SUFFIXES = {".md", ".txt", ".rst", ".py", ".yml", ".yaml", ".json", ".toml", ".html", ".js", ".ts", ".sh"}


def _walk_files(*dirs: Path):
    """Every file under the given directories, each file once, skipping SKIP_DIRS."""
    seen: set[Path] = set()
    for d in dirs:
        if d is None or not d.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
            for f in filenames:
                path = Path(dirpath) / f
                key = path.resolve()
                if key not in seen:
                    seen.add(key)
                    yield path


def rewrite_links(root: Path, moved: dict[Path, Path], write: bool, project_root: Optional[Path] = None,
                  also: tuple[Path, ...] = ()) -> dict[str, int]:
    """Point every reference to a moved file at its new path, relative to the referencing file.

    ``moved`` maps each source (resolved) to its new story path. Files under
    ``root`` and under each directory in ``also`` (the stories directory, so
    the new stories are rewritten even when ROOT excludes ``.skald``) are
    visited. A relative reference is tried against the referencing file's
    directory, every ancestor of it up to ``root``, and ``project_root``,
    so same-directory, bucket-relative, and repository-relative forms all
    resolve. A reference inside a moved file (now a story) is tried first
    against the directory the record came from, since that is where its
    links pointed. Returns ``{file: count}`` for files with at least one
    rewrite, keys relative to ``root`` where possible. With ``write`` false
    nothing is changed, only counted.
    """
    root = Path(root).resolve()
    project_root = Path(project_root).resolve() if project_root else None
    sources = {src.resolve(): dst.resolve() for src, dst in moved.items()}
    origins = {dst: src.parent for src, dst in sources.items()}
    counts: dict[str, int] = {}
    for path in _walk_files(root, *also):
        if path.suffix not in TEXT_SUFFIXES or path.resolve() in sources:
            continue
        try:
            text = read_text(path)  # line endings preserved, so a rewrite never changes them
        except (OSError, UnicodeDecodeError):
            continue
        n = 0

        stop = {root, project_root, None}

        def ancestors(start: Path, stop=stop) -> list[Path]:
            out = []
            d = start
            while True:
                out.append(d)
                if d in stop or d.parent == d:
                    break
                d = d.parent
            return out

        bases: list[Path] = []
        if path.resolve() in origins:
            bases.extend(ancestors(origins[path.resolve()]))
        for d in ancestors(path.resolve().parent) + [root, project_root]:
            if d is not None and d not in bases:
                bases.append(d)

        def sub(m: re.Match, bases=bases, path=path) -> str:
            nonlocal n
            token = m.group(1)
            for base in bases:
                try:
                    target = (base / token).resolve()
                except OSError:
                    continue
                if target in sources:
                    n += 1
                    return os.path.relpath(sources[target], path.parent).replace(os.sep, "/")
            return token

        new_text = LINK_TOKEN_RE.sub(sub, text)
        if n:
            try:
                key = path.resolve().relative_to(root).as_posix()
            except ValueError:
                key = path.resolve().relative_to(project_root).as_posix() if project_root and project_root in path.resolve().parents else str(path)
            counts[key] = n
            if write and new_text != text:
                atomic_write(path, new_text)
    return counts
