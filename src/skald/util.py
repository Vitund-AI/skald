"""Small helpers with no Skald-specific knowledge."""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def note_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def parse_iso(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def slugify(title: str, limit: int = 50) -> str:
    ascii_title = title.encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")
    return slug[:limit].rstrip("-")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` via a temp file and rename, so readers never see a partial file."""
    path = Path(path)
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


def read_text(path: Path) -> str:
    """Read a file preserving line endings exactly."""
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def checklist_progress(body: str) -> tuple[int, int]:
    """Count Markdown task-list items: returns (done, total)."""
    total = done = 0
    for line in body.splitlines():
        m = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+\[([ xX])\]\s", line)
        if m:
            total += 1
            if m.group(1) in ("x", "X"):
                done += 1
    return done, total
