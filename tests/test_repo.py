"""Invariants of this repository's own Skald backlog and package data."""
import json
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

        first = next(l for l in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines() if l.startswith("## "))
        m = re.match(r"^## (\d+\.\d+\.\d+)", first)
        if m:
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
        import py_compile
        import subprocess
        root = Path(__file__).resolve().parents[1]
        scripts = sorted((root / "examples").rglob("*.py"))
        self.assertTrue(scripts)
        for s in scripts:
            py_compile.compile(str(s), doraise=True)
        proc = subprocess.run([sys.executable, str(root / "examples" / "model-routing" / "report.py"), "--json"],
                              capture_output=True, text=True, cwd=root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rows = json.loads(proc.stdout)
        self.assertTrue(all({"id", "intended", "worked_by", "days", "sent_back"} <= set(r) for r in rows))
