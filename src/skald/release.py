"""``skald release``: the done column becomes a changelog section and a versioned archive.

Done means finished but not shipped; archived with ``released: "X.Y.Z"`` means shipped in
that version. The command reads every story in a terminal column, writes a section for
them into the changelog, stamps each with the version, archives them, and commits.
"""
from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Optional

from .errors import SkaldError
from .store import Store, Story, prelude_of

CHANGELOG_HEADING_RE = re.compile(r"^##\s+changelog\s*$", re.I)
SECTION_RE = re.compile(r"^##\s+(.*)$")
UNRELEASED_RE = re.compile(r"unreleased", re.I)
DEFAULT_CHANGELOG = "CHANGELOG.md"


def changelog_text(story: Story) -> str:
    """The story's ``## Changelog`` section as one paragraph, or its title."""
    lines = prelude_of(story.body).splitlines()
    start = None
    for i, line in enumerate(lines):
        if CHANGELOG_HEADING_RE.match(line.strip()):
            start = i + 1
            break
    if start is None:
        return story.title
    out = []
    for line in lines[start:]:
        if re.match(r"^#{1,6}\s", line):
            break
        out.append(line.strip())
    text = " ".join(part for part in " ".join(out).split() if part)
    return text or story.title


class Release:
    def __init__(self, version: str, date: str, changes: list[Story], closed: list[Story]):
        self.version = version
        self.date = date
        self.changes = changes
        self.closed = closed

    @property
    def stories(self) -> list[Story]:
        return self.changes + self.closed

    def section(self) -> str:
        lines = [f"## {self.version} ({self.date})", ""]
        for s in self.changes:
            lines.append(f"- {changelog_text(s)} ({s.id})")
        if self.closed:
            if self.changes:
                lines.append("")
            lines += ["### Not doing", ""]
            lines += [f"- {s.title} ({s.id})" for s in self.closed]
        return "\n".join(lines) + "\n"


def plan(store: Store, version: str, date: Optional[str] = None) -> Release:
    version = (version or "").strip()
    if not version or any(c.isspace() for c in version):
        raise SkaldError("a version such as 1.2.0 is required")
    date = date or _dt.date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise SkaldError("--date must be YYYY-MM-DD")
    stories, _ = store.load_all()
    changes = [s for s in stories if store.config.is_terminal(s.status) and not store.config.is_closed(s.status)]
    closed = [s for s in stories if store.config.is_closed(s.status)]
    if not changes and not closed:
        raise SkaldError("nothing to release: no story is in a done or closed column")
    return Release(version, date, changes, closed)


def merge_changelog(existing: Optional[str], release: Release) -> str:
    """Insert the release section into a changelog.

    If the first ``##`` section is marked unreleased, it becomes this version and the
    generated list is appended to it under ``### Stories``, so hand-written notes for
    the version survive. Otherwise a new section goes in above the first one.
    """
    section = release.section()
    if not existing or not existing.strip():
        return f"# Changelog\n\n{section}"
    lines = existing.splitlines(keepends=True)
    heads = [i for i, l in enumerate(lines) if SECTION_RE.match(l)]
    if heads and UNRELEASED_RE.search(lines[heads[0]]):
        first = heads[0]
        end = heads[1] if len(heads) > 1 else len(lines)
        lines[first] = f"## {release.version} ({release.date})\n"
        body = section.split("\n", 2)[2]  # drop the heading and its blank line
        block = "\n".join(l for l in body.splitlines())
        block = block.replace("### Not doing", "#### Not doing")
        insert = "\n### Stories\n\n" + block.rstrip("\n") + "\n"
        head = "".join(lines[:end]).rstrip("\n") + "\n"
        tail = "".join(lines[end:])
        return head + insert + ("\n" + tail if tail else "")
    if heads:
        at = heads[0]
        return "".join(lines[:at]) + section + "\n" + "".join(lines[at:])
    return existing.rstrip("\n") + "\n\n" + section


def apply(store: Store, release: Release, changelog_path: Path) -> dict:
    """Write the changelog, stamp and archive the stories. Returns what changed."""
    from .util import atomic_write

    existing = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else None
    atomic_write(changelog_path, merge_changelog(existing, release))
    ids = [s.id for s in release.stories]
    for s in release.stories:
        store.mark_released(s.id, release.version)
    moved = store.archive(ids=ids)
    return {"version": release.version, "date": release.date, "changelog": str(changelog_path),
            "archived": [s.id for s in moved]}
