"""``skald audit``: the mechanical half of a premise audit.

A design record cites paths, ``path:line`` references, and commit hashes,
and those drift within days. This module extracts the checkable claims from
a story body and checks them against the working tree and the repository.
It reports what it could check; it never claims the story is still true.
That judgment is the agent's, recorded as an ordinary note.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import gitutil
from .store import Story, prelude_of

# A path: directories then a file with an extension, e.g. src/skald/cli.py. A bare file with an
# extension counts when it carries a line reference (cli.py:1338), since that is how people cite code.
PATH_RE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]{1,8}|[\w-]+\.[A-Za-z]{1,8}(?=:\d))(?::(\d+)(?:-(\d+))?)?(?![\w/])")
# A commit hash: 7 to 40 hex characters as a whole word, with at least one letter and one digit so
# plain numbers and words like "deadbeef" are not both taken (deadbeef is; it looks like a hash).
HASH_RE = re.compile(r"(?<![\w/.])([0-9a-f]{7,40})(?![\w/])(?!\.\w)")  # a trailing full stop is fine; abc1234.py is a file
SKIP_DIRS = {".git", ".skald", "node_modules", "__pycache__", ".venv", "venv", "build", "dist"}
STAMP_FMT = "%Y-%m-%d %H:%M UTC"


def extract(text: str) -> dict:
    """Claims in ``text``: ``{paths: [..], lines: [(path, n)], commits: [..]}``, each de-duplicated in order."""
    paths: list[str] = []
    lines: list[tuple[str, int]] = []
    for m in PATH_RE.finditer(text):
        path = m.group(1)
        if path not in paths:
            paths.append(path)
        if m.group(2):
            n = int(m.group(3) or m.group(2))
            if (path, n) not in lines:
                lines.append((path, n))
    commits: list[str] = []
    for m in HASH_RE.finditer(text):
        h = m.group(1)
        if any(c.isalpha() for c in h) and any(c.isdigit() for c in h) and h not in commits:
            commits.append(h)
    return {"paths": paths, "lines": lines, "commits": commits}


def _basename_index(root: Path) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            out.setdefault(f, []).append(Path(dirpath) / f)
    return out


def resolve_path(root: Path, cited: str, index: Optional[dict] = None) -> Optional[Path]:
    """The file a citation names: relative to the root, else a unique basename match anywhere in the tree."""
    direct = root / cited
    if direct.is_file():
        return direct
    if "/" not in cited and index is not None:
        hits = index.get(cited, [])
        if len(hits) == 1:
            return hits[0]
    return None


def last_audit(story: Story) -> Optional[dict]:
    return story.last_note("audit")


def _stamp_to_iso(stamp: str) -> Optional[str]:
    try:
        return datetime.strptime(stamp, STAMP_FMT).replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return None


def since_stamp(story: Story) -> tuple[str, bool]:
    """(ISO instant, audited-before?) for the changed-since check: the newest audit note, else created_at."""
    note = last_audit(story)
    if note:
        iso = _stamp_to_iso(note["stamp"])
        if iso:
            return iso, True
    return story.created_at, False


def changed_since(repo: Path, since_iso: str, paths: list[Path]) -> list[str]:
    """Distinct repository-relative paths among ``paths`` touched by a commit after ``since_iso``."""
    if not paths:
        return []
    rel = []
    for p in paths:
        try:
            rel.append(p.resolve().relative_to(repo).as_posix())
        except ValueError:
            continue
    if not rel:
        return []
    proc = gitutil._run(["log", f"--since={since_iso}", "--name-only", "--format=", "--", *rel], cwd=repo)
    if proc.returncode != 0:
        return []
    seen: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line and line in rel and line not in seen:
            seen.append(line)
    return seen


def run_audit(story: Story, repo: Optional[Path], include_notes: bool = False) -> dict:
    """Check every claim in the story. Pure apart from reading the tree and asking git."""
    text = story.body if include_notes else prelude_of(story.body)
    claims = extract(text)
    root = repo or story.path.parent.parent.parent
    index = _basename_index(root) if any("/" not in p for p in claims["paths"]) else None
    resolved: dict[str, Optional[Path]] = {p: resolve_path(root, p, index) for p in claims["paths"]}
    missing = [p for p, r in resolved.items() if r is None]
    past_end = []
    for path, n in claims["lines"]:
        target = resolved.get(path)
        if target is None:
            continue
        try:
            count = sum(1 for _ in open(target, "rb"))
        except OSError:
            continue
        if n > count:
            past_end.append({"ref": f"{path}:{n}", "lines": count})
    bad_commits = []
    if repo is not None:
        for h in claims["commits"]:
            proc = gitutil._run(["cat-file", "-e", f"{h}^{{commit}}"], cwd=repo)
            if proc.returncode != 0:
                bad_commits.append(h)
    else:
        bad_commits = list(claims["commits"])
    since_iso, audited = since_stamp(story)
    changed = changed_since(repo, since_iso, [r for r in resolved.values() if r is not None]) if repo else []
    return {
        "id": story.id,
        "title": story.title,
        "paths": {"checked": len(claims["paths"]), "missing": missing},
        "lines": {"checked": len(claims["lines"]), "past_end": past_end},
        "commits": {"checked": len(claims["commits"]), "missing": bad_commits, "unchecked": repo is None},
        "changed_since": {"since": since_iso, "audited_before": audited, "paths": changed},
    }


def summary_lines(result: dict) -> list[str]:
    """The compact summary, one line per check, used for the terminal and the audit note."""
    p, l, c, ch = result["paths"], result["lines"], result["commits"], result["changed_since"]
    out = [f"paths      {p['checked']} checked" + (f", {len(p['missing'])} missing: {', '.join(p['missing'])}" if p["missing"] else ", all present")]
    if l["checked"]:
        out.append(f"line refs  {l['checked']} checked" + (
            f", {len(l['past_end'])} past end of file: " + ", ".join(f"{x['ref']} (file has {x['lines']})" for x in l["past_end"])
            if l["past_end"] else ", all within their files"))
    if c["checked"]:
        if c.get("unchecked"):
            out.append(f"commits    {c['checked']} cited, not checked (no git repository)")
        else:
            out.append(f"commits    {c['checked']} checked" + (f", {len(c['missing'])} not found: {', '.join(c['missing'])}" if c["missing"] else ", all found"))
    when = ch["since"][:10]
    label = f"changed since last audit ({when})" if ch["audited_before"] else f"changed since the story was created ({when})"
    out.append(f"{label}: " + (", ".join(ch["paths"]) if ch["paths"] else "nothing"))
    return out


def status_line(story: Story, repo: Optional[Path]) -> str:
    """For the resume header: when the story was last audited and what moved since."""
    note = last_audit(story)
    if not note:
        return "never audited"
    iso = _stamp_to_iso(note["stamp"])
    days = ""
    if iso:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(iso)
        days = f" ({age.days}d ago)"
    changed = []
    if repo is not None:
        claims = extract(prelude_of(story.body))
        index = _basename_index(repo) if any("/" not in p for p in claims["paths"]) else None
        found = [r for r in (resolve_path(repo, p, index) for p in claims["paths"]) if r is not None]
        changed = changed_since(repo, iso or story.created_at, found)
    tail = f"; {len(changed)} referenced file(s) changed since" if changed else "; no referenced file changed since"
    return f"last audited {note['stamp'][:10]}{days}{tail}"
