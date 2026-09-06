"""Thin wrappers around the git CLI. Every function tolerates git being absent."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from .errors import GitError


def _run(args: list[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False,
        )
    except (OSError, ValueError) as e:
        raise GitError(f"git is not available: {e}") from None
    if check and proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip() or f"git {' '.join(args)} failed"
        raise GitError(msg)
    return proc


def available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=False)
        return True
    except OSError:
        return False


def root(path: Path) -> Optional[Path]:
    try:
        proc = _run(["rev-parse", "--show-toplevel"], cwd=path)
    except GitError:
        return None
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip()).resolve()


def branch(repo: Path) -> Optional[str]:
    try:
        proc = _run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
        if proc.returncode == 0 and proc.stdout.strip() and proc.stdout.strip() != "HEAD":
            return proc.stdout.strip()
        # An unborn branch (no commits yet) or a detached HEAD.
        proc = _run(["symbolic-ref", "--short", "-q", "HEAD"], cwd=repo)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
        proc = _run(["rev-parse", "--short", "HEAD"], cwd=repo)
        return f"detached at {proc.stdout.strip()}" if proc.returncode == 0 else None
    except GitError:
        return None


def user_name(repo: Path) -> Optional[str]:
    try:
        proc = _run(["config", "--get", "user.name"], cwd=repo)
    except GitError:
        return None
    name = proc.stdout.strip()
    return name or None


def get_alias(repo: Path, name: str) -> Optional[str]:
    try:
        proc = _run(["config", "--get", f"alias.{name}"], cwd=repo)
    except GitError:
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def unset_alias(repo: Path, name: str) -> None:
    try:
        _run(["config", "--unset", f"alias.{name}"], cwd=repo)
    except GitError:
        pass


def changes(repo: Path, subpath: str) -> list[dict]:
    """Uncommitted changes under ``subpath`` as ``[{status, path}]``."""
    proc = _run(["status", "--porcelain", "--untracked-files=all", "--", subpath], cwd=repo, check=True)
    out = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2].strip() or "??", line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        out.append({"status": code, "path": path})
    return out


def commit_path(repo: Path, subpath: str, message: str) -> str:
    """Stage everything under ``subpath`` and commit it. Returns the new commit sha."""
    message = (message or "").strip()
    if not message:
        raise GitError("a commit message is required")
    _run(["add", "-A", "--", subpath], cwd=repo, check=True)
    staged = _run(["diff", "--cached", "--quiet", "--", subpath], cwd=repo)
    if staged.returncode == 0:
        raise GitError(f"nothing to commit under {subpath}")
    _run(["commit", "-q", "-m", message, "--", subpath], cwd=repo, check=True)
    return _run(["rev-parse", "--short", "HEAD"], cwd=repo, check=True).stdout.strip()


def push(repo: Path) -> str:
    proc = _run(["push"], cwd=repo, check=True)
    return (proc.stderr or proc.stdout).strip()


def log_file(repo: Path, path: Path, limit: int = 50) -> list[dict]:
    """Commit history for one file, newest first."""
    rel = str(Path(path).resolve().relative_to(repo))
    proc = _run(
        ["log", f"-n{limit}", "--follow", "--format=%h%x1f%aI%x1f%an%x1f%s", "--", rel],
        cwd=repo,
    )
    if proc.returncode != 0:
        return []
    out = []
    for line in proc.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            out.append({"sha": parts[0], "date": parts[1], "author": parts[2], "subject": parts[3]})
    return out


def show(repo: Path, ref: str, rel_path: str) -> Optional[str]:
    """File content at ``ref``, or None if it did not exist there."""
    proc = _run(["show", f"{ref}:{rel_path}"], cwd=repo)
    return proc.stdout if proc.returncode == 0 else None


def ls_tree(repo: Path, ref: str, rel_dir: str) -> list[str]:
    """Paths of files under ``rel_dir`` at ``ref``."""
    proc = _run(["ls-tree", "-r", "--name-only", ref, "--", rel_dir], cwd=repo)
    if proc.returncode != 0:
        return []
    return [p for p in proc.stdout.splitlines() if p.endswith(".md")]


def rev_parse(repo: Path, ref: str) -> Optional[str]:
    proc = _run(["rev-parse", "--verify", "--quiet", ref], cwd=repo)
    return proc.stdout.strip() if proc.returncode == 0 else None
