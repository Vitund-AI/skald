"""Invariants of this repository's own Skald backlog and package data."""
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

    def test_own_backlog_is_clean(self):
        skald_dir = ROOT / ".skald"
        if not (skald_dir / "stories").exists():
            self.skipTest("no .skald/stories in this checkout")
        config = ProjectConfig.load(skald_dir / "config.json")
        self.assertEqual(config.name, "skald")
        problems, _ = Store(skald_dir, config).check()
        self.assertEqual(problems, [])

    def test_no_legacy_single_file_layout(self):
        self.assertFalse((ROOT / "skald.py").exists())
        self.assertFalse((ROOT / ".skald" / "skald.py").exists())
