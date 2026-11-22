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

    def test_refuses_while_main_has_commits_dev_lacks(self):
        # The render job's commit on main, never merged back: the pull request to main could conflict.
        self.git("checkout", "-q", "main")
        (self.repo / "board.txt").write_text("rendered\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "skald: refresh rendered board [skip ci]")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "dev")
        r = self.release("1.1.0", "--dry-run")
        self.assertEqual(r.returncode, 1)
        self.assertIn("main has changes that dev lacks", r.stderr)
        self.assertIn("refresh rendered board", r.stderr)
        self.assertIn("git merge origin/main", r.stderr)
        self.git("merge", "-q", "origin/main", "-m", "merge main")
        self.git("push", "-q", "origin", "dev")
        r = self.release("1.1.0", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("main: nothing that dev lacks", r.stdout)

    def test_lets_through_main_commits_that_change_nothing(self):
        # The merge of the last release pull request, never merged back: history only, no files.
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "dev", "-m", "Merge pull request #88 from o/dev")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "dev")
        r = self.release("1.1.0", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("main: 1 commit(s) that dev lacks, none changing a file", r.stdout)

    def fake_github(self):
        """A gh that plays GitHub against the local origin: the pull request merges dev into main,
        every check passes, and the publish run succeeds. It logs each call."""
        gh = self.tmp / "bin" / "gh"
        gh.write_text(f"""#!/bin/sh
echo "$*" >> {self.tmp / 'gh.log'}
case "$1 $2" in
  "auth status") exit 0 ;;
  "pr list") echo "" ;;
  "pr create") echo "https://github.test/o/r/pull/7" ;;
  "pr view") git rev-parse origin/dev ;;
  "pr checks") echo "unittest pass" ;;
  "pr merge") git fetch -q origin && git push -q origin refs/remotes/origin/dev:refs/heads/main ;;
  "run list") case "$*" in *skald.yml*) echo "1 0" ;; *publish.yml*) echo "123" ;; esac ;;
  "run watch") exit 0 ;;
  "repo view") echo "https://github.test/o/r" ;;
esac
""")
        # The release runs the repository's tests; give the scratch repository one that passes.
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "__init__.py").write_text("")
        (self.repo / ".gitignore").write_text("__pycache__/\n")
        (self.repo / "tests" / "test_ok.py").write_text("import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "a test")
        self.git("push", "-q", "origin", "dev")

    def test_a_release_runs_to_the_end_unattended(self):
        import subprocess
        self.fake_github()
        r = self.release("1.1.0", "--yes")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("released 1.1.0", r.stdout)
        out = lambda *a: subprocess.run(["git", *a], cwd=self.repo, capture_output=True, text=True).stdout.strip()  # noqa: E731
        self.git("fetch", "-q", "origin", "--tags")
        self.assertEqual(out("rev-parse", "v1.1.0^{commit}"), out("rev-parse", "origin/main"))  # tagged main
        self.assertIn('__version__ = "1.1.0"', out("show", "v1.1.0:src/skald/__init__.py"))
        # main merged back into dev, so the next release starts level
        self.assertEqual(subprocess.run(["git", "merge-base", "--is-ancestor", "origin/main", "origin/dev"], cwd=self.repo).returncode, 0)
        log = (self.tmp / "gh.log").read_text()
        self.assertIn("pr merge", log)
        self.assertIn("run watch 123 --exit-status", log)

    def test_ask_stops_before_the_merge(self):
        import subprocess
        self.fake_github()
        r = subprocess.run(["bash", str(self.script), "1.1.0", "--ask"], cwd=self.repo, env=self.env,
                           capture_output=True, text=True, input="y\nn\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("stopped", r.stderr)
        self.assertNotIn("pr merge", (self.tmp / "gh.log").read_text())
        # Resuming picks up at the pull request (the fake lists none open, so it opens one) and finishes.
        r = self.release("1.1.0", "--resume")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("resume from: step 4", r.stdout)
        self.assertIn("released 1.1.0", r.stdout)

    def bump(self, version, push=False):
        f = self.repo / "src" / "skald" / "__init__.py"
        f.write_text(f'__version__ = "{version}"\n')
        self.git("commit", "-q", "-am", f"Bump to {version}")
        if push:
            self.git("push", "-q", "origin", "dev")

    def test_resume_works_out_where_the_release_stopped(self):
        r = self.release("1.1.0", "--resume", "--dry-run")
        self.assertEqual(r.returncode, 1)
        self.assertIn("nothing to resume", r.stderr)
        # Bumped and committed, not pushed (the tests failed, say): resume at the pull request.
        self.bump("1.1.0")
        r = self.release("1.1.0", "--dry-run")
        self.assertIn("add --resume", r.stderr)
        r = self.release("1.1.0", "--resume", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("resume from: step 4", r.stdout)
        self.assertIn("next: scripts/release.sh 1.1.0 --resume", r.stdout)
        # The pull request merged: main carries the version, so resume at the tag.
        self.git("push", "-q", "origin", "dev")
        self.git("push", "-q", "origin", "dev:main")
        r = self.release("1.1.0", "--resume", "--dry-run")
        self.assertIn("resume from: step 5", r.stdout)
        # Tagged and pushed: what is left is the merge back into dev and the publish.
        self.git("tag", "-a", "v1.1.0", "-m", "Release 1.1.0")
        self.git("push", "-q", "origin", "v1.1.0")
        r = self.release("1.1.0", "--resume", "--dry-run")
        self.assertIn("resume from: step 6", r.stdout)


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
