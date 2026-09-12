"""Invariants of this repository's own Skald backlog and package data."""
import json
import os
import sys
import unittest
from pathlib import Path

from skald import cli
from skald.config import ProjectConfig
from skald.store import Store

ROOT = Path(__file__).resolve().parent.parent


class TestRepo(unittest.TestCase):
    def test_package_data_is_present(self):
        self.assertIn("<title>Skald</title>", (ROOT / "src" / "skald" / "web" / "index.html").read_text(encoding="utf-8"))
        self.assertIn("# Working with Skald", cli.agents_template())

    def test_own_agents_md_matches_template(self):
        agents = ROOT / ".skald" / "AGENTS.md"
        if not agents.exists():
            self.skipTest("no .skald/AGENTS.md in this checkout")
        self.assertEqual(agents.read_text(encoding="utf-8"), cli.agents_template())

    def test_cli_reference_is_current(self):
        doc = ROOT / "docs" / "cli.md"
        if not doc.exists():
            self.skipTest("no docs/cli.md in this checkout")
        self.assertEqual(doc.read_text(encoding="utf-8"), cli.docs_markdown(), "run `skald docs`")

    def test_newest_changelog_release_matches_package_version(self):
        """release never edits version files (D46), so the bump must happen by hand; this catches a missed one."""
        import re

        from skald import __version__

        heads = [l for l in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines() if l.startswith("## ")]
        first = heads[0]
        if re.match(r"^## unreleased\b", first, re.I):
            first = heads[1]
        m = re.match(r"^## (\d+\.\d+\.\d+) \(\d{4}-\d\d-\d\d\)$", first)
        self.assertIsNotNone(m, f"the newest release heading must read '## X.Y.Z (YYYY-MM-DD)', not {first!r}")
        self.assertEqual(m.group(1), __version__, "bump src/skald/__init__.py to match the newest release in CHANGELOG.md")

    def test_own_backlog_is_clean(self):
        skald_dir = ROOT / ".skald"
        if not (skald_dir / "stories").exists():
            self.skipTest("no .skald/stories in this checkout")
        config = ProjectConfig.load(skald_dir / "config.json")
        self.assertEqual(config.name, "skald")
        problems, _ = Store(skald_dir, config).check()
        self.assertEqual(problems, [])



class TestExamples(unittest.TestCase):
    def test_example_scripts_compile_and_report_runs(self):
        import os
        import py_compile
        import subprocess
        root = Path(__file__).resolve().parents[1]
        # The child interpreter needs src/ the way tests/__init__.py gives it to this one.
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(p for p in (str(root / "src"), os.environ.get("PYTHONPATH", "")) if p))
        scripts = sorted((root / "examples").rglob("*.py"))
        self.assertTrue(scripts)
        for s in scripts:
            py_compile.compile(str(s), doraise=True)
        proc = subprocess.run([sys.executable, str(root / "examples" / "model-routing" / "report.py"), "--json"],
                              capture_output=True, text=True, cwd=root, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rows = json.loads(proc.stdout)
        self.assertTrue(all({"id", "intended", "worked_by", "days", "sent_back"} <= set(r) for r in rows))


@unittest.skipUnless(sys.platform != "win32", "the release script is bash")
class TestReleaseScript(unittest.TestCase):
    """scripts/release.sh: the checks refuse the wrong state, and --dry-run changes nothing."""

    def setUp(self):
        import shutil
        import subprocess
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="skald-release-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        root = Path(__file__).resolve().parents[1]
        self.script = root / "scripts" / "release.sh"
        # A stub gh: present and "logged in", never reaches GitHub.
        gh = self.tmp / "bin" / "gh"
        gh.parent.mkdir()
        gh.write_text("#!/bin/sh\nexit 0\n")
        gh.chmod(0o755)
        # A skald launcher for the child shell, on this interpreter and this checkout.
        skald = self.tmp / "bin" / "skald"
        skald.write_text(f"#!/bin/sh\nPYTHONPATH={root / 'src'} exec {sys.executable} -m skald \"$@\"\n")
        skald.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{gh.parent}{os.pathsep}{os.environ['PATH']}", SKALD_HOME=str(self.tmp / "home"),
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        # A bare origin with a dev branch, and a clone of it, holding a version file and a done story.
        origin = self.tmp / "origin.git"
        subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
        self.repo = self.tmp / "repo"
        subprocess.run(["git", "clone", "-q", str(origin), str(self.repo)], check=True, env=self.env, capture_output=True)
        (self.repo / "src" / "skald").mkdir(parents=True)
        (self.repo / "src" / "skald" / "__init__.py").write_text('__version__ = "1.0.0"\n')
        (self.repo / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n- hand-written\n\n## 1.0.0 (2026-01-01)\n")
        self.git("checkout", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "seed")
        self.git("push", "-q", "-u", "origin", "main")
        self.git("checkout", "-q", "-b", "dev")
        subprocess.run([str(skald), "init"], cwd=self.repo, check=True, env=self.env, capture_output=True)
        subprocess.run([str(skald), "new", "Shipped thing", "--status", "done"], cwd=self.repo, check=True, env=self.env, capture_output=True)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "a done story")
        self.git("push", "-q", "-u", "origin", "dev")

    def git(self, *args):
        import subprocess
        subprocess.run(["git", *args], cwd=self.repo, check=True, env=self.env, capture_output=True)

    def release(self, *args):
        import subprocess
        return subprocess.run(["bash", str(self.script), *args], cwd=self.repo, env=self.env, capture_output=True, text=True)

    def test_dry_run_checks_and_changes_nothing(self):
        import subprocess
        before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, capture_output=True, text=True).stdout
        r = self.release("1.1.0", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("version: 1.0.0 -> 1.1.0", r.stdout)
        self.assertIn("tag: v1.1.0 is free", r.stdout)
        self.assertIn("## 1.1.0", r.stdout)                       # the release preview
        self.assertIn("nothing was changed", r.stdout)
        after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, capture_output=True, text=True).stdout
        self.assertEqual(before, after)
        self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=self.repo, capture_output=True, text=True).stdout, "")
        self.assertIn('__version__ = "1.0.0"', (self.repo / "src" / "skald" / "__init__.py").read_text())

    def test_checks_refuse_the_wrong_state(self):
        r = self.release("v1.1.0", "--dry-run")
        self.assertEqual(r.returncode, 1)
        self.assertIn("without the v", r.stderr)
        r = self.release("0.9.0", "--dry-run")
        self.assertIn("older than the current 1.0.0", r.stderr)
        r = self.release("1.0.0", "--dry-run")
        self.assertIn("already the version", r.stderr)
        (self.repo / "scratch.txt").write_text("x")
        r = self.release("1.1.0", "--dry-run")
        self.assertIn("not clean", r.stderr)
        (self.repo / "scratch.txt").unlink()
        self.git("checkout", "-q", "-b", "feature")
        r = self.release("1.1.0", "--dry-run")
        self.assertIn("run from dev", r.stderr)
        self.git("checkout", "-q", "dev")
        self.git("tag", "v1.1.0")
        r = self.release("1.1.0", "--dry-run")
        self.assertIn("already exists locally", r.stderr)


class TestDocsOnlyClassifier(unittest.TestCase):
    """scripts/docs_only.py: what CI may skip the matrix for, and what it must not."""

    def classify(self, *paths):
        import subprocess
        root = Path(__file__).resolve().parents[1]
        return subprocess.run([sys.executable, str(root / "scripts" / "docs_only.py")], input="\n".join(paths),
                              capture_output=True, text=True).stdout.strip()

    def test_documentation_the_tests_never_read_is_skippable(self):
        self.assertEqual(self.classify("README.md"), "true")
        self.assertEqual(self.classify("docs/board.md", "docs/images/board-dark.png", "SECURITY.md", "DECISIONS.md", "SPEC.md"), "true")

    def test_anything_the_tests_read_or_any_code_runs_everything(self):
        for paths in (("README.md", "src/skald/cli.py"), ("docs/cli.md",), ("CHANGELOG.md", "README.md"),
                      (".skald/stories/abc123-x.md",), ("src/skald/templates/AGENTS.md",), ("tests/test_cli.py",),
                      (".github/workflows/test.yml",), (), ("", " ")):
            self.assertEqual(self.classify(*paths), "false", paths)
