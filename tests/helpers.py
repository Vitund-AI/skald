"""Shared fixtures: an isolated SKALD_HOME and throwaway git repositories."""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from skald import cli
from skald.config import ProjectConfig
from skald.errors import SkaldError
from skald.registry import Registry, UserConfig, Workspace
from skald.store import Store


SAMPLE_CONFIG_COLUMNS = [
    {"key": "backlog", "label": "Backlog", "role": "backlog"},
    {"key": "ready", "label": "Ready", "role": "ready"},
    {"key": "doing", "label": "Doing", "role": "active", "limit": 1},
    {"key": "qa", "label": "QA", "role": "active"},
    {"key": "done", "label": "Done", "role": "done"},
    {"key": "wont_do", "label": "Won't do", "role": "closed"},
]


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True)
    return proc.stdout


class SkaldTestCase(unittest.TestCase):
    """Every test gets a fresh config home and a fresh git repository with a project."""

    def setUp(self):
        # resolve() so comparisons hold where TMP is a symlink (macOS /private/var) or a short name (Windows RUNNER~1)
        self.tmp = Path(tempfile.mkdtemp(prefix="skald-test-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = self.tmp / "home"
        self._env = {k: os.environ.get(k) for k in ("SKALD_HOME", "SKALD_DIR", "SKALD_AUTHOR")}
        os.environ["SKALD_HOME"] = str(self.home)
        os.environ.pop("SKALD_DIR", None)
        os.environ.pop("SKALD_AUTHOR", None)
        self.addCleanup(self._restore_env)
        self.repo = self.make_repo("alpha")
        self.skald_dir = self.repo / ".skald"
        self._cwd = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, self._cwd)

    def _restore_env(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def make_repo(self, name: str, init_skald: bool = True) -> Path:
        repo = self.tmp / name
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.email", f"{name}@example.com")
        git(repo, "config", "user.name", f"{name.title()} Tester")
        if init_skald:
            (repo / ".skald" / "stories").mkdir(parents=True)
            ProjectConfig(name).save(repo / ".skald" / "config.json")
            Registry(self.home).register(name, repo / ".skald")
        return repo

    def workspace(self) -> Workspace:
        registry = Registry(self.home)
        return Workspace(registry, UserConfig(self.home))

    def store(self, name: str = "alpha") -> Store:
        return self.workspace().open(name)

    def run_cli(self, *argv: str, cwd: Path = None):
        out, err = io.StringIO(), io.StringIO()
        old = os.getcwd()
        if cwd:
            os.chdir(cwd)
        try:
            with redirect_stdout(out), redirect_stderr(err):
                try:
                    code = cli.run(list(argv))
                except SkaldError as e:
                    print(f"ERROR: {e}", file=sys.stderr)
                    code = e.exit_code
                except SystemExit as e:
                    code = int(e.code or 0)
        finally:
            os.chdir(old)
        return code, out.getvalue(), err.getvalue()

    def new(self, *argv: str, cwd: Path = None) -> str:
        code, out, err = self.run_cli("new", *argv, cwd=cwd)
        self.assertEqual(code, 0, err)
        return out.strip()

    def write_raw(self, name: str, text: str, store: Store = None) -> Path:
        store = store or self.store()
        path = store.stories_dir / name
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return path
