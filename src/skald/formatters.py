"""Keep code formatters off Skald's own files (DECISIONS D87).

Everything under ``.skald/`` is written by Skald in its own canonical layout: story files, the
rendered board, the agent contract, the config. A formatter run over the repository rewrites
them (Prettier pads the board's tables, which makes ``check`` call it stale, and reflows stories,
which turns into diff noise and merge conflicts). So ``skald init`` adds ``.skald/`` to the
project's ``.prettierignore``. It edits that file only where Prettier is evidently in use (the
file exists, or a Prettier config or ``package.json`` entry does). It never creates the file
in a project that doesn't use Prettier.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

IGNORE_LINE = ".skald/"
IGNORE_FILE = ".prettierignore"
# Every name Prettier reads its configuration from, beside package.json's "prettier" key.
CONFIG_FILES = (
    ".prettierrc", ".prettierrc.json", ".prettierrc.json5", ".prettierrc.yaml", ".prettierrc.yml",
    ".prettierrc.toml", ".prettierrc.js", ".prettierrc.cjs", ".prettierrc.mjs", ".prettierrc.ts",
    ".prettierrc.cts", ".prettierrc.mts", "prettier.config.js", "prettier.config.cjs",
    "prettier.config.mjs", "prettier.config.ts", "prettier.config.cts", "prettier.config.mts",
)
_DEPENDENCY_KEYS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
# Lines that already keep Prettier out of .skald/ (gitignore syntax, as Prettier reads it).
_COVERING = {".skald", ".skald/", "/.skald", "/.skald/", ".skald/**", "/.skald/**", "**/.skald", "**/.skald/",
             "**/.skald/**"}


def prettier_evidence(root: Path) -> Optional[str]:
    """Why this project looks like it runs Prettier (a file name), or None."""
    if (root / IGNORE_FILE).is_file():
        return IGNORE_FILE
    for name in CONFIG_FILES:
        if (root / name).is_file():
            return name
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if isinstance(data, dict):
            if "prettier" in data:
                return "package.json"
            for key in _DEPENDENCY_KEYS:
                deps = data.get(key)
                if isinstance(deps, dict) and "prettier" in deps:
                    return "package.json"
    return None


def ignores_skald(text: str) -> bool:
    """Whether a .prettierignore already has a line that keeps Prettier out of .skald/."""
    return any(line.strip() in _COVERING for line in text.splitlines())


def ensure_prettierignore(root: Path) -> Optional[str]:
    """Add ``.skald/`` to ``root/.prettierignore`` where Prettier is in use; say what was done, or None."""
    evidence = prettier_evidence(root)
    if evidence is None:
        return None
    path = root / IGNORE_FILE
    if not path.exists():
        path.write_bytes(f"# Skald writes these files in its own layout\n{IGNORE_LINE}\n".encode("utf-8"))
        return f"created {IGNORE_FILE} with {IGNORE_LINE} (Prettier is configured here: {evidence})"
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    if ignores_skald(text):
        return f"{IGNORE_FILE} already skips {IGNORE_LINE}"
    eol = b"\r\n" if b"\r\n" in raw else b"\n"
    sep = b"" if not raw or raw.endswith(b"\n") else eol
    path.write_bytes(raw + sep + IGNORE_LINE.encode("utf-8") + eol)
    return f"added {IGNORE_LINE} to {IGNORE_FILE}"
