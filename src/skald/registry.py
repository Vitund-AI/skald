"""Machine-local state: the project index and user preferences.

Nothing here is ever committed. The config directory is resolved as:

1. ``$SKALD_HOME`` if set.
2. ``%APPDATA%\\skald`` on Windows.
3. ``$XDG_CONFIG_HOME/skald``, defaulting to ``~/.config/skald``.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
import sys
from pathlib import Path
from typing import Optional

from .config import ProjectConfig, slugify_name
from .errors import ConfigError, NotFoundError, SkaldError
from .store import Store
from .util import atomic_write, now_iso

USER_DEFAULTS = {
    "author": "",        # display name for notes made from the board; empty = git user.name
    "push": False,       # push after committing from the board
    "port": 8321,        # board port
    "host": "127.0.0.1",  # board bind address
    "stale_days": 3,     # mark active stories untouched for this many days
}


def config_home() -> Path:
    env = os.environ.get("SKALD_HOME")
    if env:
        return Path(env).expanduser().resolve()
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "skald"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "skald"


def token_path(home: Path) -> Path:
    return home / "token"


def read_token(home: Path) -> Optional[str]:
    """The board server's token, or None if none has been generated yet."""
    try:
        value = token_path(home).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def ensure_token(home: Path) -> str:
    """Create the token on first use. The file is private to the user (0600 in a 0700 directory)."""
    existing = read_token(home)
    if existing:
        return existing
    return rotate_token(home)


def rotate_token(home: Path) -> str:
    """Replace the token. Existing browser sessions and scripts stop working until they use the new one."""
    home.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(home, stat.S_IRWXU)
    except OSError:  # pragma: no cover - Windows, or a directory we do not own
        pass
    value = secrets.token_hex(32)
    path = token_path(home)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(value + "\n")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:  # pragma: no cover
        pass
    return value


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ConfigError(f"{path}: not valid JSON ({e})") from None
    except OSError as e:
        raise ConfigError(f"{path}: {e}") from None


class UserConfig:
    def __init__(self, home: Optional[Path] = None):
        self.home = home or config_home()
        self.path = self.home / "config.json"
        data = _load_json(self.path, {})
        if not isinstance(data, dict):
            raise ConfigError(f"{self.path}: must be a JSON object")
        self.data = data

    def get(self, key: str):
        if key not in USER_DEFAULTS:
            raise SkaldError(f"unknown setting '{key}' (known: {', '.join(USER_DEFAULTS)})")
        default = USER_DEFAULTS[key]
        value = self.data.get(key, default)
        # Tolerate hand-edited config.json: coerce to the default's type or fall back.
        try:
            if isinstance(default, bool):
                return value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes", "on")
            if isinstance(default, int):
                return int(value)
            return str(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    def set(self, key: str, raw: str) -> None:
        if key not in USER_DEFAULTS:
            raise SkaldError(f"unknown setting '{key}' (known: {', '.join(USER_DEFAULTS)})")
        default = USER_DEFAULTS[key]
        if isinstance(default, bool):
            if raw.lower() in ("1", "true", "yes", "on"):
                value = True
            elif raw.lower() in ("0", "false", "no", "off"):
                value = False
            else:
                raise SkaldError(f"'{key}' must be true or false")
        elif isinstance(default, int):
            try:
                value = int(raw)
            except ValueError:
                raise SkaldError(f"'{key}' must be an integer") from None
        else:
            value = raw
        self.data[key] = value
        self.save()

    def unset(self, key: str) -> None:
        self.data.pop(key, None)
        self.save()

    def all(self) -> dict:
        return {k: self.get(k) for k in USER_DEFAULTS}

    def save(self) -> None:
        atomic_write(self.path, json.dumps(self.data, indent=2) + "\n")


def checkout_id(skald_dir: Path) -> str:
    """An opaque, stable id for a checkout: the API and the board refer to paths only through it."""
    return hashlib.sha1(str(Path(skald_dir).resolve()).encode("utf-8")).hexdigest()[:8]


class Registry:
    """The index of projects known on this machine: ``projects.json``."""

    def __init__(self, home: Optional[Path] = None):
        self.home = home or config_home()
        self.path = self.home / "projects.json"
        data = _load_json(self.path, {"projects": {}})
        if not isinstance(data, dict) or not isinstance(data.get("projects"), dict):
            raise ConfigError(f"{self.path}: expected {{\"projects\": {{...}}}}")
        self.projects: dict[str, dict] = data["projects"]

    def save(self) -> None:
        atomic_write(self.path, json.dumps({"projects": self.projects}, indent=2, sort_keys=True) + "\n")

    def register(self, name: str, skald_dir: Path) -> Optional[str]:
        """Record ``name`` at ``skald_dir``. Returns a notice if something changed, else None.

        The first path registered for a name is the primary: the one ``-p NAME``,
        cross-project references, and the board use. Another checkout of the
        same project (a worktree or a second clone) is recorded as a checkout
        and never replaces a primary that still exists. The primary moves only
        when its directory has gone, which is the "I moved the repository" case.
        """
        skald_dir = Path(skald_dir).resolve()
        entry = self.projects.get(name)
        if entry is None:
            self.projects[name] = {"path": str(skald_dir), "registered_at": now_iso()}
            self.save()
            return f"registered project '{name}' at {skald_dir}"
        primary = Path(entry.get("path", ""))
        if primary == skald_dir:
            return None
        others = [Path(p) for p in entry.get("checkouts", [])]
        if not (primary / "stories").is_dir():
            entry["path"] = str(skald_dir)
            entry["registered_at"] = now_iso()
            entry["checkouts"] = [str(p) for p in others if p != skald_dir]
            if not entry["checkouts"]:
                entry.pop("checkouts")
            self.save()
            return f"project '{name}' moved from {primary} to {skald_dir}"
        if skald_dir in others:
            return None
        entry["checkouts"] = [str(p) for p in others] + [str(skald_dir)]
        self.save()
        return (f"project '{name}' is registered at {primary}; this checkout at {skald_dir} is recorded "
                f"beside it (`skald projects use` here makes it the primary)")

    def use(self, name: str, skald_dir: Path) -> None:
        """Make ``skald_dir`` the primary path for ``name``; the old primary becomes a checkout."""
        skald_dir = Path(skald_dir).resolve()
        entry = self.projects.get(name)
        if entry is None:
            raise NotFoundError(f"no registered project '{name}'")
        primary = Path(entry.get("path", ""))
        if primary == skald_dir:
            return
        others = [Path(p) for p in entry.get("checkouts", []) if Path(p) != skald_dir]
        if (primary / "stories").is_dir():
            others.insert(0, primary)
        entry["path"] = str(skald_dir)
        entry["registered_at"] = now_iso()
        if others:
            entry["checkouts"] = [str(p) for p in others]
        else:
            entry.pop("checkouts", None)
        self.save()

    def checkouts(self, name: str) -> list[dict]:
        """Every working tree of ``name``: the primary first, then recorded checkouts and git worktrees.

        Each is ``{id, path, primary, worktree, exists}``. ``id`` is a short hash
        of the path so the HTTP API never carries a filesystem path. Recorded
        checkouts whose directory has gone are forgotten.
        """
        entry = self.projects.get(name)
        if entry is None:
            return []
        primary = Path(entry.get("path", ""))
        exists = (primary / "stories").is_dir()
        out = [{"id": checkout_id(primary), "path": str(primary), "primary": True, "worktree": False, "exists": exists}]
        seen = {primary}
        # Git worktrees of the primary, found without anyone registering them.
        worktrees: list[Path] = []
        if exists:
            from . import gitutil

            repo = gitutil.root(primary)
            if repo is not None:
                try:
                    rel = primary.relative_to(repo)
                except ValueError:
                    rel = None
                if rel is not None:
                    worktrees = [(wt / rel).resolve() for wt in gitutil.worktrees(repo)]
        kept = []
        for p in [Path(x) for x in entry.get("checkouts", [])]:
            if p in seen:
                continue
            seen.add(p)
            if not (p / "stories").is_dir():
                continue
            kept.append(p)
            out.append({"id": checkout_id(p), "path": str(p), "primary": False, "worktree": p in worktrees,
                        "exists": True})
        if [str(p) for p in kept] != entry.get("checkouts", []):
            if kept:
                entry["checkouts"] = [str(p) for p in kept]
            else:
                entry.pop("checkouts", None)
            self.save()
        for p in worktrees:
            if p in seen or not (p / "stories").is_dir():
                continue
            seen.add(p)
            out.append({"id": checkout_id(p), "path": str(p), "primary": False, "worktree": True, "exists": True})
        return out

    def remove(self, name: str) -> None:
        if name not in self.projects:
            raise NotFoundError(f"no registered project '{name}'")
        del self.projects[name]
        self.save()

    def path_of(self, name: str) -> Optional[Path]:
        entry = self.projects.get(name)
        return Path(entry["path"]) if entry else None

    def entries(self) -> list[dict]:
        out = []
        for name in sorted(self.projects):
            p = Path(self.projects[name]["path"])
            out.append({
                "name": name,
                "path": str(p),
                "exists": (p / "stories").is_dir(),
                "registered_at": self.projects[name].get("registered_at", ""),
                "checkouts": [c for c in self.checkouts(name) if not c["primary"]],
            })
        return out

    def name_for_path(self, skald_dir: Path) -> Optional[str]:
        skald_dir = Path(skald_dir).resolve()
        for name, entry in self.projects.items():
            if Path(entry.get("path", "")) == skald_dir:
                return name
        return None


# --------------------------------------------------------------------------
# Locating and opening projects
# --------------------------------------------------------------------------


def find_skald_dir(start: Optional[Path] = None) -> Optional[Path]:
    """Find the ``.skald`` directory for the current location.

    ``$SKALD_DIR`` wins. Otherwise walk up from ``start`` (default: cwd)
    looking for a ``.skald`` directory.
    """
    env = os.environ.get("SKALD_DIR")
    if env:
        return Path(env).expanduser().resolve()
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        d = candidate / ".skald"
        if d.is_dir():
            return d
    return None


def default_name_for(skald_dir: Path) -> str:
    return slugify_name(skald_dir.resolve().parent.name)


class Workspace:
    """Opens projects by name through the registry. Caches open stores."""

    def __init__(self, registry: Optional[Registry] = None, user: Optional[UserConfig] = None):
        self.registry = registry or Registry()
        self.user = user or UserConfig(self.registry.home)
        self._stores: dict[str, Optional[Store]] = {}
        self.notices: list[str] = []

    def open_dir(self, skald_dir: Path, register: bool = True, create_config: bool = True) -> Store:
        """Open the project at ``skald_dir``, creating config.json if missing."""
        skald_dir = Path(skald_dir).resolve()
        if not (skald_dir / "stories").is_dir():
            raise NotFoundError(f"{skald_dir} is not a Skald project (no stories/ directory); run `skald init`")
        cfg_path = skald_dir / "config.json"
        if cfg_path.exists():
            config = ProjectConfig.load(cfg_path)
        else:
            name = self.registry.name_for_path(skald_dir) or default_name_for(skald_dir)
            config = ProjectConfig(name)
            if create_config:
                config.save(cfg_path)
                self.notices.append(f"wrote {cfg_path} (project name '{name}'); commit it with your next change")
        if register:
            notice = self.registry.register(config.name, skald_dir)
            if notice:
                self.notices.append(notice)
        store = Store(skald_dir, config, workspace=self)
        primary = self.registry.path_of(config.name)
        if primary is None or primary == skald_dir:
            self._stores[config.name] = store
        return store

    def open(self, name: str) -> Optional[Store]:
        """Open a registered project by name. Returns None if unknown or missing on disk."""
        if name in self._stores:
            return self._stores[name]
        path = self.registry.path_of(name)
        store: Optional[Store] = None
        if path and (path / "stories").is_dir():
            try:
                store = self.open_dir(path, register=False, create_config=False)
            except (ConfigError, NotFoundError):
                store = None
        self._stores[name] = store
        return store

    def open_checkout(self, name: str, checkout: str) -> Optional[Store]:
        """Open one checkout of ``name`` by its id (see ``Registry.checkouts``). None if unknown."""
        for c in self.registry.checkouts(name):
            if c["id"] == checkout:
                if c["primary"]:
                    return self.open(name)
                try:
                    return self.open_dir(Path(c["path"]), register=False, create_config=False)
                except (ConfigError, NotFoundError):
                    return None
        return None

    def other_checkouts(self, store: Store) -> list[Store]:
        """Stores for the other working trees of ``store``'s project, for claims made there but not committed."""
        out = []
        for c in self.registry.checkouts(store.name):
            if Path(c["path"]) == store.dir or not c["exists"]:
                continue
            try:
                out.append(self.open_dir(Path(c["path"]), register=False, create_config=False))
            except (ConfigError, NotFoundError, SkaldError):
                continue
        return out

    def open_all(self) -> tuple[list[Store], list[str]]:
        stores, warnings = [], []
        for entry in self.registry.entries():
            s = self.open(entry["name"])
            if s is None:
                warnings.append(f"project '{entry['name']}' at {entry['path']} is not available")
            else:
                stores.append(s)
        return stores, warnings

    def current(self, project: Optional[str] = None, start: Optional[Path] = None) -> Store:
        """The store for ``--project NAME`` or for the current directory."""
        if project:
            store = self.open(project)
            if store is None:
                raise NotFoundError(f"project '{project}' is not registered on this machine (see `skald projects`)")
            return store
        skald_dir = find_skald_dir(start)
        if skald_dir is None:
            raise NotFoundError(
                "no .skald directory found here or in any parent; run `skald init` or pass --project NAME"
            )
        return self.open_dir(skald_dir)
