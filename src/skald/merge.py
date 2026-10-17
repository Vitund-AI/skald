"""``skald merge-file``: git's merge driver for story files (DECISIONS D84, SPEC "Merging story files").

Git hands the driver three versions of one story, the common ancestor (base), ours and theirs,
and takes the result from the file it named ours. A story is merged by part rather than by line:

- front matter field by field against the base, so two branches that changed different fields
  never conflict, and when both changed the same field a recorded rule picks the result;
- notes as a set ordered by their timestamps, because notes only ever get appended;
- the authored body line by line, through ``git merge-file``, so only a real overlapping edit
  produces conflict markers, and those stay inside the body where the front matter cannot break.

A side that does not parse as a story (already conflicted, hand-broken) makes the whole file a
plain line merge, which is what git would have done without the driver. The rendered board
(``.skald/README.md``) is routed here too: it is derived from the stories, so a merge keeps our
copy rather than conflict, ``skald check`` calls it stale, and the next commit re-renders it.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from . import gitutil
from .errors import SkaldError
from .store import NOTE_HEADING_RE, parse_story_text, serialise_story

SET_FIELDS = ("tags", "blocked_by")


def split_body(body: str) -> tuple[str, list[str]]:
    """The authored prelude and the note blocks, each block from its heading to the next, trailing newlines trimmed."""
    marks = list(NOTE_HEADING_RE.finditer(body))
    if not marks:
        return body, []
    blocks = [body[m.start():(marks[i + 1].start() if i + 1 < len(marks) else len(body))].rstrip("\n")
              for i, m in enumerate(marks)]
    return body[:marks[0].start()], blocks


def join_body(prelude: str, blocks: list[str]) -> str:
    """The inverse of ``split_body``, in the layout ``skald note`` writes: a blank line between parts."""
    parts = ([prelude.rstrip("\n")] if prelude.strip() else []) + blocks
    return "\n\n".join(parts) + "\n" if parts else ""


def _stamp(block: str) -> str:
    m = NOTE_HEADING_RE.match(block)
    return m.group("stamp") if m else ""


def merge_notes(base: list[str], ours: list[str], theirs: list[str]) -> list[str]:
    """Both sides' notes, once each, minus any a side removed, ordered by timestamp (ours first on a tie)."""
    removed = (set(base) - set(ours)) | (set(base) - set(theirs))
    out: list[str] = []
    for block in ours + theirs:
        if block not in removed and block not in out:
            out.append(block)
    return sorted(out, key=_stamp)  # stable: equal stamps keep ours-then-theirs order


def merge_set(base: list, ours: list, theirs: list) -> list:
    """Both sides' additions and removals: ours' order, then what theirs added."""
    removed = (set(base) - set(ours)) | (set(base) - set(theirs))
    out: list = []
    for value in ours + theirs:
        if value not in removed and value not in out:
            out.append(value)
    return out


_MISSING = object()


def merge_fields(base: dict, ours: dict, theirs: dict, columns: list[str]) -> dict:
    """Front matter, field by field against the base. A field one side changed (or deleted) takes
    that side; one both changed alike is that value; one both changed differently follows its rule."""
    out: dict = {}
    newer = theirs if theirs.get("updated_at", "") > ours.get("updated_at", "") else ours
    keys = list(ours) + [k for k in theirs if k not in ours] + [k for k in base if k not in ours and k not in theirs]
    for key in keys:
        b, o, t = base.get(key, _MISSING), ours.get(key, _MISSING), theirs.get(key, _MISSING)
        if key in SET_FIELDS:
            if o is _MISSING and t is _MISSING:
                continue
            value = merge_set([] if b is _MISSING else b, [] if o is _MISSING else o, [] if t is _MISSING else t)
        elif o == t or t == b:
            value = o
        elif o == b:
            value = t
        elif key == "updated_at":
            value = max(x for x in (o, t) if x is not _MISSING)
        elif key == "created_at":
            value = b if b is not _MISSING else o
        elif key == "status" and o in columns and t in columns:
            value = o if columns.index(o) >= columns.index(t) else t  # further along the workflow
        else:
            value = newer.get(key, _MISSING)  # the most recent edit
        if value is not _MISSING:
            out[key] = value
    return out


def merge_text(base: str, ours: str, theirs: str) -> tuple[str, bool]:
    """A line merge by ``git merge-file``: the result, and whether it holds conflict markers."""
    with tempfile.TemporaryDirectory(prefix="skald-merge-") as tmp:
        paths = []
        for name, text in (("ours", ours), ("base", base), ("theirs", theirs)):
            p = Path(tmp) / name
            p.write_text(text, encoding="utf-8", newline="")
            paths.append(p)
        return gitutil.merge_file(*paths)


def merge_story(base: str, ours: str, theirs: str, columns: Optional[list[str]] = None) -> tuple[str, bool]:
    """The merged story file and whether a person still has to resolve something (markers in the body)."""
    try:
        bf, bb = parse_story_text(base, "base") if base.strip() else ({}, "")
        of, ob = parse_story_text(ours, "ours")
        tf, tb = parse_story_text(theirs, "theirs")
    except SkaldError:
        return merge_text(base, ours, theirs)
    fields = merge_fields(bf, of, tf, columns or [])
    (bp, bn), (op, on), (tp, tn) = split_body(bb), split_body(ob), split_body(tb)
    prelude, conflicted = (op, False) if op == tp or tp == bp else (tp, False) if op == bp else merge_text(bp, op, tp)
    return serialise_story(fields, join_body(prelude, merge_notes(bn, on, tn))), conflicted


def _columns(path: Optional[str]) -> list[str]:
    """Column keys in workflow order, from the config.json beside the story's ``stories/`` directory."""
    if not path:
        return []
    from .config import ProjectConfig

    try:
        return ProjectConfig.load(Path(path).resolve().parent.parent / "config.json").keys
    except (SkaldError, OSError, ValueError):
        return []


def run_driver(base_path: str, ours_path: str, theirs_path: str, path: Optional[str] = None) -> int:
    """git's ``%O %A %B %P``: write the merge into the ours file; exit 0 when clean, 1 when markers remain."""
    def read(p: str) -> str:
        with open(p, encoding="utf-8", newline="") as fh:
            return fh.read()

    if path and "/stories/" not in "/" + Path(path).as_posix():
        return 0  # the rendered board: derived, so keep ours; the next commit re-renders it
    text, conflicted = merge_story(read(base_path), read(ours_path), read(theirs_path), _columns(path))
    tmp = ours_path + ".skald-merge"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, ours_path)
    return 1 if conflicted else 0
