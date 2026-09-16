"""Opt-in check for a newer ``skald-kanban`` on PyPI.

Off by default and gated by the ``update_check`` feature flag; the board asks
for it only when the flag is on. The result is cached machine-local so PyPI is
queried at most once a day, and every failure (offline, timeout, bad JSON, a
locked-down network) is swallowed so nothing here can break the board or the
server. Standard library only, like the rest of the package.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

from .util import atomic_write, now_iso, parse_iso

PYPI_JSON = "https://pypi.org/pypi/skald-kanban/json"
TTL_SECONDS = 24 * 60 * 60
TIMEOUT = 2.5

# A final release only: N(.N)+ with no pre/post/dev suffix. A pre-release on
# PyPI must not read as an update for someone on a stable version.
_FINAL_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)+$")


def parse_version(value) -> Optional[tuple]:
    """The numeric tuple for a final release string, or None if it is not one."""
    if not isinstance(value, str) or not _FINAL_RE.match(value.strip()):
        return None
    return tuple(int(p) for p in value.strip().split("."))


def is_newer(latest: str, current: str) -> bool:
    """True when ``latest`` is a final release strictly newer than ``current``."""
    a, b = parse_version(latest), parse_version(current)
    if a is None or b is None:
        return False
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def fetch_latest(timeout: float = TIMEOUT) -> Optional[str]:
    """The newest version on PyPI, or None on any error (offline, timeout, bad data)."""
    try:
        req = Request(PYPI_JSON, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as res:
            data = json.loads(res.read().decode("utf-8"))
        version = data.get("info", {}).get("version")
        return version if isinstance(version, str) else None
    except Exception:
        return None


def state_path(home: Path) -> Path:
    return home / "update.json"


def read_state(home: Path) -> dict:
    try:
        data = json.loads(state_path(home).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _fresh(state: dict) -> bool:
    when = parse_iso(state.get("checked_at", "")) if state.get("checked_at") else None
    if when is None:
        return False
    from datetime import datetime, timezone

    return (datetime.now(timezone.utc) - when).total_seconds() < TTL_SECONDS


def check(home: Optional[Path], current: str, force: bool = False) -> dict:
    """``{current, latest, outdated, checked_at}`` for the update note.

    Serves the cached result and only queries PyPI when the cache is missing or
    older than a day. Never raises; a lookup that fails leaves ``latest`` at
    whatever was last known (or None) and ``outdated`` False.
    """
    state = read_state(home) if home is not None else {}
    if home is not None and not force and _fresh(state):
        latest = state.get("latest")
    else:
        latest = fetch_latest()
        if latest is None:
            latest = state.get("latest")  # keep the last known value on a failed lookup
        elif home is not None:
            try:
                atomic_write(state_path(home), json.dumps({"checked_at": now_iso(), "latest": latest}) + "\n")
                state = {"checked_at": now_iso(), "latest": latest}
            except OSError:
                pass
    outdated = bool(latest) and is_newer(latest, current)
    return {"current": current, "latest": latest if isinstance(latest, str) else None,
            "outdated": outdated, "checked_at": state.get("checked_at")}
