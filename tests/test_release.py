"""skald release: changelog section, released stamp, archive, commit."""
import json

from skald import release as rel
from skald.errors import SkaldError

from .helpers import SAMPLE_CONFIG_COLUMNS, SkaldTestCase, git


class TestRelease(SkaldTestCase):
    def setUp(self):
        super().setUp()
        cfg = json.loads((self.skald_dir / "config.json").read_text())
        cfg["columns"] = SAMPLE_CONFIG_COLUMNS
        (self.skald_dir / "config.json").write_text(json.dumps(cfg))
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-q", "-m", "init")
        self.a = self.new("Add login", "--status", "done", "--body",
                          "## Requirements\n\nInternal detail.\n\n## Changelog\n\nSign in with an email\nand a password.\n\n## Acceptance\n- [x] works\n")
        self.b = self.new("Fix logout", "--status", "done")
        self.c = self.new("Dark mode", "--status", "wont_do")
        self.d = self.new("Still open", "--status", "ready")
        self.run_cli("note", self.a, "done", "--as", "agent")

    def test_changelog_text_prefers_the_section(self):
        s = self.store()
        self.assertEqual(rel.changelog_text(s.get(self.a)), "Sign in with an email and a password.")
        self.assertEqual(rel.changelog_text(s.get(self.b)), "Fix logout")

    def test_plan_and_section(self):
        s = self.store()
        r = rel.plan(s, "1.2.0", "2026-09-09")
        self.assertEqual([x.id for x in r.changes], [self.a, self.b])
        self.assertEqual([x.id for x in r.closed], [self.c])
        self.assertEqual(r.section(), f"## 1.2.0 (2026-09-09)\n\n- Sign in with an email and a password. ({self.a})\n- Fix logout ({self.b})\n\n### Not doing\n\n- Dark mode ({self.c})\n")
        with self.assertRaises(SkaldError):
            rel.plan(s, "", "2026-09-09")
        with self.assertRaises(SkaldError):
            rel.plan(s, "1.0", "yesterday")
        s.update(self.a, status="ready"); s.update(self.b, status="ready"); s.update(self.c, status="ready")
        with self.assertRaises(SkaldError):
            rel.plan(s, "1.2.0")

    def test_merge_changelog_cases(self):
        s = self.store()
        r = rel.plan(s, "1.2.0", "2026-09-09")
        # no changelog yet
        self.assertTrue(rel.merge_changelog(None, r).startswith("# Changelog\n\n## 1.2.0 (2026-09-09)\n"))
        # unreleased first section keeps its notes and gains the list
        existing = "# Changelog\n\n## 1.2.0 (unreleased)\n\nHand-written intro.\n\n### Added\n- thing\n\n## 1.1.0 (2026-01-01)\n\n- old\n"
        merged = rel.merge_changelog(existing, r)
        self.assertIn("## 1.2.0 (2026-09-09)\n\nHand-written intro.\n\n### Added\n- thing\n\n### Stories\n\n- Sign in", merged)
        self.assertIn("#### Not doing", merged)
        self.assertTrue(merged.rstrip().endswith("- old"))
        self.assertEqual(merged.count("## 1.1.0"), 1)
        # released first section: new section goes above it
        existing = "# Changelog\n\n## 1.1.0 (2026-01-01)\n\n- old\n"
        merged = rel.merge_changelog(existing, r)
        self.assertLess(merged.index("## 1.2.0"), merged.index("## 1.1.0"))
        self.assertTrue(merged.startswith("# Changelog\n\n## 1.2.0"))

    def test_cli_dry_run_changes_nothing(self):
        code, out, err = self.run_cli("release", "1.2.0", "--dry-run", "--date", "2026-09-09")
        self.assertEqual(code, 0, err)
        self.assertIn("## 1.2.0 (2026-09-09)", out)
        self.assertIn("would archive 3 stories", out)
        self.assertFalse((self.repo / "CHANGELOG.md").exists())
        self.assertEqual(self.store().get(self.a).status, "done")

    def test_cli_release_writes_stamps_archives_commits(self):
        (self.repo / "CHANGELOG.md").write_text("# Changelog\n\n## 1.2.0 (unreleased)\n\nNotes.\n")
        code, out, err = self.run_cli("release", "1.2.0", "--date", "2026-09-09")
        self.assertEqual(code, 0, err)
        self.assertIn("committed", out)
        text = (self.repo / "CHANGELOG.md").read_text()
        self.assertIn("## 1.2.0 (2026-09-09)\n\nNotes.\n\n### Stories\n\n- Sign in with an email and a password.", text)
        s = self.store()
        for sid in (self.a, self.b, self.c):
            story = s.get(sid)
            self.assertTrue(story.archived)
            self.assertEqual(story.released, "1.2.0")
        self.assertFalse(s.get(self.d).archived)
        self.assertEqual(git(self.repo, "status", "--porcelain").strip(), "")
        msg = git(self.repo, "log", "-1", "--format=%B")
        self.assertIn("Release 1.2.0", msg)
        for sid in (self.a, self.b, self.c):
            self.assertIn(f"Skald-Story: {sid}", msg)
        code, out, _ = self.run_cli("ls", "--release", "1.2.0", "--json")
        self.assertEqual(sorted(x["id"] for x in json.loads(out)), sorted([self.a, self.b, self.c]))
        self.assertTrue(all(x["released"] == "1.2.0" for x in json.loads(out)))
        code, out, _ = self.run_cli("ls", "--release", "9.9.9", "--json")
        self.assertEqual(json.loads(out), [])
        # a second release with nothing done is refused
        code, out, err = self.run_cli("release", "1.3.0")
        self.assertNotEqual(code, 0)
        self.assertIn("nothing to release", err)

    def test_cli_no_commit_and_custom_changelog(self):
        code, out, err = self.run_cli("release", "2.0.0", "--no-commit", "--changelog", "docs/HISTORY.md", "--date", "2026-09-09")
        self.assertEqual(code, 0, err)
        self.assertTrue((self.repo / "docs" / "HISTORY.md").exists())
        self.assertNotIn("committed", out)
        self.assertNotEqual(git(self.repo, "status", "--porcelain").strip(), "")

    def test_completion_offers_releases(self):
        self.run_cli("release", "1.2.0", "--no-commit", "--date", "2026-09-09")
        code, out, _ = self.run_cli("_complete", "--", "2", "ls", "--release", "")
        self.assertIn("1.2.0", out)
