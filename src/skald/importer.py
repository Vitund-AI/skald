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
from pathlib import Path
from typing import Optional

from .errors import SkaldError
from .util import parse_when

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
            out += r"(?:.*/)?"; i += 3
        elif glob.startswith("**", i):
            out += r".*"; i += 2
        elif c == "*":
            out += r"[^/]*"; i += 1
        elif c == "?":
            out += r"[^/]"; i += 1
        else:
            out += re.escape(c); i += 1
    return re.compile("^" + out + "$")


def excluded(relpath: str, mapping: dict) -> bool:
    return any(_glob_to_re(g).match(relpath) for g in mapping.get("exclude", []))


def _subject(rule: dict, text: str, relpath: str) -> str:
    on = rule.get("on", "body")
    if on == "filename":
        return Path(relpath).name
    if on == "relpath":
        return relpath
    if on == "body":
        return text
    raise SkaldError(f"mapping: 'on' must be filename, relpath, or body (got {on!r})")


def _expand(template: str, m: re.Match) -> str:
    """``$1`` style groups in a mapping value."""
    return re.sub(r"\$(\d+)", lambda g: m.group(int(g.group(1))) or "", template)


# ---------------------------------------------------------------- planning

def plan_text(text: str, relpath: str, source: Path, mapping: dict, default_status: Optional[str] = None) -> Plan:
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

    # created_at: a regex over the original text with a group.
    created_at = None
    rule = mapping.get("created_at")
    if rule:
        m = _rx(rule["regex"], "created_at", re.M).search(text)
        if m:
            raw = m.group(int(rule.get("group", 1)))
            if parse_when(raw) is None:
                problems.append(f"created_at {raw!r} is not a date")
            else:
                created_at = raw
        else:
            problems.append("created_at: no match")

    # status: first matching rule, else the default rule, else the CLI default.
    status = default_status
    for rule in mapping.get("status", []):
        if "regex" in rule:
            if _rx(rule["regex"], "status").search(_subject(rule, text, relpath)):
                status = rule.get("status")
                break
        elif "default" in rule and status is None:
            status = rule["default"]

    # tags: every matching rule contributes one, with $1 substitution.
    tags: list[str] = []
    for rule in mapping.get("tags", []):
        m = _rx(rule["regex"], "tags").search(_subject(rule, text, relpath))
        if m:
            tag = _expand(rule["tag"], m).strip().lower()
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
    return Plan(source, relpath, title, status, tags, created_at, body, notes, problems)


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


def rewrite_links(root: Path, moved: dict[Path, Path], write: bool) -> dict[str, int]:
    """Point every reference to a moved file at its new path, relative to the referencing file.

    ``moved`` maps each source (resolved) to its new story path. Returns
    ``{file: count}`` for files with at least one rewrite. With ``write``
    false nothing is changed, only counted. A reference inside a moved file
    (now a story) is resolved against the directory the record came from,
    since that is where its relative links pointed.
    """
    root = Path(root).resolve()
    sources = {src.resolve(): dst.resolve() for src, dst in moved.items()}
    origins = {dst: src.parent for src, dst in sources.items()}
    counts: dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            path = Path(dirpath) / f
            if path.suffix not in TEXT_SUFFIXES or path.resolve() in sources:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            n = 0

            bases = [path.parent, root]
            if path.resolve() in origins:
                bases.insert(0, origins[path.resolve()])

            def sub(m: re.Match) -> str:
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
                counts[path.relative_to(root).as_posix()] = n
                if write and new_text != text:
                    path.write_text(new_text, encoding="utf-8")
    return counts
