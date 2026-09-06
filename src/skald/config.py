"""Per-project configuration: ``.skald/config.json``.

This file is committed with the repository. It carries the project's name
(which cross-project references depend on), the story-format version, and
the board's columns.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .errors import ConfigError
from .util import atomic_write

FORMAT = 1
ROLES = ("backlog", "ready", "active", "done", "closed")
TERMINAL_ROLES = ("done", "closed")
WARN_ROLES = ("ready", "active", "done")

DEFAULT_COLUMNS = [
    {"key": "backlog", "label": "Backlog", "role": "backlog"},
    {"key": "ready", "label": "Ready", "role": "ready"},
    {"key": "in_progress", "label": "In progress", "role": "active"},
    {"key": "review", "label": "Review", "role": "active"},
    {"key": "done", "label": "Done", "role": "done"},
]

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


def slugify_name(text: str) -> str:
    ascii_text = text.encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:64].rstrip("-") or "project"


class Column:
    __slots__ = ("key", "label", "role", "limit")

    def __init__(self, key: str, label: str, role: str, limit: int | None = None):
        self.key = key
        self.label = label
        self.role = role
        self.limit = limit

    def to_dict(self) -> dict:
        d = {"key": self.key, "label": self.label, "role": self.role}
        if self.limit is not None:
            d["limit"] = self.limit
        return d


class ProjectConfig:
    def __init__(self, name: str, columns: list[Column] | None = None, extra: dict | None = None):
        if not NAME_RE.match(name):
            raise ConfigError(
                f"invalid project name {name!r}: use lowercase letters, digits, and hyphens"
            )
        self.name = name
        self.columns = columns or [Column(**c) for c in DEFAULT_COLUMNS]
        self.extra = dict(extra or {})
        self._validate_columns()

    # -- construction ----------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict, where: str = "config.json") -> "ProjectConfig":
        if not isinstance(data, dict):
            raise ConfigError(f"{where}: must be a JSON object")
        fmt = data.get("format", FORMAT)
        if not isinstance(fmt, int) or isinstance(fmt, bool):
            raise ConfigError(f"{where}: 'format' must be an integer")
        if fmt > FORMAT:
            raise ConfigError(
                f"{where}: format {fmt} is newer than this version of Skald understands ({FORMAT}); upgrade skald-kanban"
            )
        name = data.get("name")
        if not isinstance(name, str):
            raise ConfigError(f"{where}: 'name' must be a string")
        raw_cols = data.get("columns", DEFAULT_COLUMNS)
        if not isinstance(raw_cols, list) or not raw_cols:
            raise ConfigError(f"{where}: 'columns' must be a non-empty list")
        columns = []
        for i, c in enumerate(raw_cols):
            if not isinstance(c, dict):
                raise ConfigError(f"{where}: columns[{i}] must be an object")
            key = c.get("key")
            if not isinstance(key, str) or not KEY_RE.match(key):
                raise ConfigError(
                    f"{where}: columns[{i}].key must match {KEY_RE.pattern} (got {key!r})"
                )
            label = c.get("label", key.replace("_", " ").capitalize())
            if not isinstance(label, str) or not label.strip():
                raise ConfigError(f"{where}: columns[{i}].label must be a non-empty string")
            role = c.get("role")
            if role not in ROLES:
                raise ConfigError(
                    f"{where}: columns[{i}].role must be one of {', '.join(ROLES)} (got {role!r})"
                )
            limit = c.get("limit")
            if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
                raise ConfigError(f"{where}: columns[{i}].limit must be a positive integer")
            columns.append(Column(key, label.strip(), role, limit))
        extra = {k: v for k, v in data.items() if k not in ("format", "name", "columns")}
        try:
            return cls(name, columns, extra)
        except ConfigError as e:
            raise ConfigError(f"{where}: {e}") from None

    @classmethod
    def load(cls, path: Path) -> "ProjectConfig":
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            raise ConfigError(f"{path}: {e}") from None
        try:
            data = json.loads(text)
        except ValueError as e:
            raise ConfigError(f"{path}: not valid JSON ({e})") from None
        return cls.from_dict(data, str(path))

    def to_dict(self) -> dict:
        d = {"format": FORMAT, "name": self.name, "columns": [c.to_dict() for c in self.columns]}
        d.update(self.extra)
        return d

    def save(self, path: Path) -> None:
        atomic_write(path, json.dumps(self.to_dict(), indent=2) + "\n")

    # -- queries ---------------------------------------------------------

    def _validate_columns(self) -> None:
        seen = set()
        for c in self.columns:
            if c.key in seen:
                raise ConfigError(f"duplicate column key {c.key!r}")
            seen.add(c.key)
        if not any(c.role in TERMINAL_ROLES for c in self.columns):
            raise ConfigError("at least one column must have role 'done' or 'closed'")

    @property
    def keys(self) -> list[str]:
        return [c.key for c in self.columns]

    def column(self, key: str) -> Column | None:
        for c in self.columns:
            if c.key == key:
                return c
        return None

    def has(self, key: str) -> bool:
        return self.column(key) is not None

    def index(self, key: str) -> int:
        for i, c in enumerate(self.columns):
            if c.key == key:
                return i
        return len(self.columns)

    def role(self, key: str) -> str | None:
        c = self.column(key)
        return c.role if c else None

    def is_terminal(self, key: str) -> bool:
        return self.role(key) in TERMINAL_ROLES

    def is_closed(self, key: str) -> bool:
        return self.role(key) == "closed"

    def warns_on(self, key: str) -> bool:
        return self.role(key) in WARN_ROLES

    def keys_with_role(self, *roles: str) -> list[str]:
        return [c.key for c in self.columns if c.role in roles]

    @property
    def default_key(self) -> str:
        """Where new stories go: the first backlog column, else the first column."""
        for c in self.columns:
            if c.role == "backlog":
                return c.key
        return self.columns[0].key

    @property
    def first_active_key(self) -> str | None:
        for c in self.columns:
            if c.role == "active":
                return c.key
        return None

    def describe(self) -> str:
        parts = []
        for c in self.columns:
            s = f"{c.key} ({c.role}"
            if c.limit:
                s += f", limit {c.limit}"
            parts.append(s + ")")
        return ", ".join(parts)
