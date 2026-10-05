"""Upgrade a project's backlog to the story format this version of Skald writes.

The format is the integer ``format`` in ``.skald/config.json`` (``config.FORMAT``). A
backlog newer than Skald refuses to load at all (``ProjectConfig.from_dict``), so the
answer there is always "upgrade skald-kanban". A backlog older than Skald is upgraded
here, one format at a time, by the steps in ``STEPS``: each takes the store at format
``n`` and leaves it at ``n + 1``, losslessly, and running ``migrate`` again afterwards
finds nothing to do.

At format 1 there are no steps, so ``skald migrate`` only confirms the backlog is
current. The command exists before any format bump so the upgrade path has a real entry
point that scripts and CI can call today (SPEC, Compatibility).
"""
from __future__ import annotations

import json
from typing import Callable

from .config import FORMAT
from .errors import ConfigError
from .lock import project_lock
from .store import Store
from .util import atomic_write, read_text

# format n -> function upgrading a store from n to n + 1. Empty until the format changes.
STEPS: dict[int, Callable[[Store], None]] = {}


def declared_format(store: Store) -> tuple[int, bool]:
    """``(format, explicit)``: the backlog's format, and whether config.json states it (it defaults to 1)."""
    raw = json.loads(read_text(store.dir / "config.json"))
    if "format" in raw:
        return raw["format"], True
    return FORMAT, False


def plan(store: Store) -> dict:
    fmt, explicit = declared_format(store)
    steps = list(range(fmt, FORMAT))
    stories, warnings = store.load_all(include_archived=True)
    return {"format": fmt, "explicit": explicit, "current": FORMAT, "needed": bool(steps),
            "steps": [f"{n} -> {n + 1}" for n in steps], "stories": len(stories), "warnings": warnings}


def apply(store: Store) -> dict:
    """Run every step from the backlog's format to ``FORMAT``, rewriting ``format`` after each.

    Under the project's mutation lock, so no other command writes a story mid-migration.
    """
    with project_lock(store.dir):
        result = plan(store)
        for n in range(result["format"], FORMAT):
            step = STEPS.get(n)
            if step is None:
                raise ConfigError(f"no migration from format {n} to {n + 1}; this backlog cannot be upgraded by this version")
            step(store)
            path = store.dir / "config.json"
            raw = json.loads(read_text(path))
            raw["format"] = n + 1
            atomic_write(path, json.dumps(raw, indent=2) + "\n")
    return result
