"""Make a project's read-modify-write cycles take turns.

Story files are written atomically (``util.atomic_write``), so a reader never sees half a
file. That does not stop a lost update: two commands each read the backlog, decide, and
write, and the second write silently undoes the first (a story claimed twice, a tag lost,
two new stories on one rank). Every mutating ``Store`` method therefore runs under a short
exclusive lock per checkout, held across its read and its write and never across a git call.

The lock is an OS file lock (``fcntl.flock`` on Unix, ``msvcrt.locking`` on Windows) on a
file in the machine-local config directory, keyed by the resolved ``.skald/`` path. It is
never inside the repository, so it cannot show up in ``git status`` or be swept into
``git add .skald``. The OS releases it when a process dies, so a crashed command leaves no
stale lock behind. Within one process (the board server's threads), a re-entrant thread
lock serialises callers first, and a method that calls another locked method re-enters
instead of deadlocking. Readers never take the lock.
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .errors import LockTimeoutError

DEFAULT_TIMEOUT = 30.0
_POLL = 0.01

_registry: dict[str, "_ProjectLock"] = {}
_registry_guard = threading.Lock()


def timeout_from_env() -> float:
    raw = os.environ.get("SKALD_LOCK_TIMEOUT", "")
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT
    return value if value > 0 else DEFAULT_TIMEOUT


def _key(skald_dir: Path) -> str:
    return os.path.normcase(str(Path(skald_dir).resolve()))


def lock_path(skald_dir: Path) -> Path:
    """Where the lock file for this checkout's ``.skald/`` lives: never in the repository."""
    name = hashlib.sha256(_key(skald_dir).encode("utf-8")).hexdigest()[:24] + ".lock"
    from .registry import config_home  # registry imports store, which imports this module

    for base in (config_home() / "locks", Path(tempfile.gettempdir()) / "skald-locks"):
        try:
            base.mkdir(parents=True, exist_ok=True)
            return base / name
        except OSError:
            continue
    raise LockTimeoutError(f"cannot create a lock directory for {skald_dir}")


if sys.platform.startswith("win"):  # pragma: no cover - exercised by the Windows CI job
    import msvcrt

    def _try_lock(fd: int) -> bool:
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    def _unlock(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _try_lock(fd: int) -> bool:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False

    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


class _ProjectLock:
    def __init__(self, skald_dir: Path):
        self.skald_dir = Path(skald_dir)
        self.thread_lock = threading.RLock()
        self.depth = 0  # only touched while thread_lock is held
        self.fd: int | None = None

    def _acquire_file(self, deadline: float, timeout: float) -> None:
        path = lock_path(self.skald_dir)
        fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            while not _try_lock(fd):
                if time.monotonic() >= deadline:
                    raise LockTimeoutError(
                        f"another skald command has been changing this project for {timeout:g}s "
                        f"(lock {path}); try again, or raise SKALD_LOCK_TIMEOUT")
                time.sleep(_POLL)
        except BaseException:
            os.close(fd)
            raise
        self.fd = fd

    def _release_file(self) -> None:
        fd, self.fd = self.fd, None
        if fd is not None:
            try:
                _unlock(fd)
            finally:
                os.close(fd)

    @contextmanager
    def hold(self, timeout: float) -> Iterator[None]:
        deadline = time.monotonic() + timeout
        if not self.thread_lock.acquire(timeout=timeout):
            raise LockTimeoutError(f"another request has been changing this project for {timeout:g}s; try again")
        try:
            if self.depth == 0:
                self._acquire_file(deadline, timeout)
            self.depth += 1
            try:
                yield
            finally:
                self.depth -= 1
                if self.depth == 0:
                    self._release_file()
        finally:
            self.thread_lock.release()


@contextmanager
def project_lock(skald_dir: Path, timeout: float | None = None) -> Iterator[None]:
    """Hold the exclusive mutation lock for one checkout's ``.skald/`` directory."""
    key = _key(skald_dir)
    with _registry_guard:
        lock = _registry.get(key)
        if lock is None:
            lock = _registry[key] = _ProjectLock(Path(skald_dir))
    with lock.hold(timeout if timeout is not None else timeout_from_env()):
        yield
