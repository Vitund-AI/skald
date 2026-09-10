"""``skald import``: a fixture corpus exercising every mapping rule, a dry run that writes nothing,
``--rm`` keeping history through git's rename detection, and link rewriting inside and outside the backlog."""
import json

from .helpers import SkaldTestCase, git

MAPPING = {
    "created_at": {"regex": r"^\*\*Filed:\*\*\s*(\d{4}-\d\d-\d\d)", "group": 1},
    "status": [{"regex": "^needs-plan-", "on": "filename", "status": "plan"}, {"default": "idea"}],
    "tags": [
        {"regex": r"^([a-z-]+)/", "on": "relpath", "tag": "area:$1"},
        {"regex": r"^(?:needs-plan-)?(common|sdlc)-(low|high)-", "on": "filename", "tag": "track:$1"},
        {"regex": r"^(?:needs-plan-)?(?:common|sdlc)-(low|high)-", "on": "filename", "tag": "priority:$1"},
    ],
    "notes": [
        {"block": r"^> \*\*Update (\d{4}-\d\d-\d\d)[^*]*\*\*", "kind": "note", "date_group": 1, "until": r"^(?!>)"},
        {"section": r"^## Open questions", "kind": "question", "per": "bullet"},
    ],
    "strip": [r"^\*\*Priority:\*\*.*$", r"^\*\*Status:\*\*.*$"],
    "exclude": ["archived/**", "*/README.md"],
}

RECORD_A = """# Build placement must follow the audience

**Filed:** 2026-08-17
**Priority:** high
**Status:** open

Some intro text that is the gist.

## Design

The design, with a link to [the other record](../fleet-hosts/sdlc-low-other.md).

> **Update 2026-08-20 (agent):**
> Shipped the first piece.
> Second line of the update.

## Open questions

- Which registry hosts the image?
- Do we keep the legacy path?

## Residuals

Left out on purpose.
"""

RECORD_B = "# Other record\n\n**Filed:** 2026-08-18\n\n" + "\n".join(
    f"Paragraph {i} of the other record, long enough that git pairs the removal with the new story." for i in range(1, 25)
) + "\n"


class TestImport(SkaldTestCase):
    def setUp(self):
        super().setUp()
        self.backlog = self.repo / "docs" / "backlog"
        (self.backlog / "fleet-hosts").mkdir(parents=True)
        (self.backlog / "archived").mkdir()
        (self.backlog / "fleet-hosts" / "needs-plan-common-high-placement.md").write_text(RECORD_A, encoding="utf-8")
        (self.backlog / "fleet-hosts" / "sdlc-low-other.md").write_text(RECORD_B, encoding="utf-8")
        (self.backlog / "fleet-hosts" / "README.md").write_text("# index\n", encoding="utf-8")
        (self.backlog / "archived" / "old.md").write_text("# old\n", encoding="utf-8")
        (self.repo / "docs" / "ORDER.md").write_text("See docs/backlog/fleet-hosts/needs-plan-common-high-placement.md first.\n", encoding="utf-8")
        (self.repo / "map.json").write_text(json.dumps(MAPPING), encoding="utf-8")
        cfg = self.skald_dir / "config.json"
        data = json.loads(cfg.read_text())
        data["columns"] = [{"key": "idea", "label": "Idea", "role": "backlog"}, {"key": "plan", "label": "Plan", "role": "backlog"},
                           {"key": "ready", "label": "Ready", "role": "ready"}, {"key": "done", "label": "Done", "role": "done"}]
        cfg.write_text(json.dumps(data))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "seed")

    def test_dry_run_writes_nothing(self):
        code, out, err = self.run_cli("import", str(self.backlog), "--map", "map.json", "--dry-run", "--rewrite-links", str(self.repo))
        self.assertEqual(code, 0, err)
        self.assertIn("fleet-hosts/needs-plan-common-high-placement.md", out)
        self.assertIn("title:      Build placement must follow the audience", out)
        self.assertIn("status:     plan", out)
        self.assertIn("tags:       area:fleet-hosts, track:common, priority:high", out)
        self.assertIn("created_at: 2026-08-17", out)
        self.assertIn("note:       [note] 2026-08-20: **Update 2026-08-20 (agent):**", out)
        self.assertIn("note:       [question] at created_at: Which registry hosts the image?", out)
        self.assertNotIn("archived/old.md", out)
        self.assertNotIn("README.md", out)
        self.assertIn("dry run: 2 file(s), 3 note(s); nothing written", out)
        self.assertIn("would be rewritten", out)
        self.assertEqual(git(self.repo, "status", "--porcelain").strip(), "")
        self.assertEqual(list((self.skald_dir / "stories").glob("*.md")), [])

    def test_import_rm_and_links(self):
        code, out, err = self.run_cli("import", str(self.backlog), "--map", "map.json", "--rm",
                                      "--rewrite-links", str(self.repo), "--as", "migrator")
        self.assertEqual(code, 0, err)
        self.assertIn("imported 2 stories", out)
        code, ls, _ = self.run_cli("ls", "--json")
        stories = {s["title"]: s for s in json.loads(ls)}
        a = stories["Build placement must follow the audience"]
        b = stories["Other record"]
        self.assertEqual((a["status"], a["created_at"], sorted(a["tags"])),
                         ("plan", "2026-08-17T00:00:00Z", ["area:fleet-hosts", "priority:high", "track:common"]))
        self.assertEqual((b["status"], b["tags"]), ("idea", ["area:fleet-hosts", "priority:low", "track:sdlc"]))
        self.assertEqual(a["questions"]["open"], 2)
        code, show, _ = self.run_cli("show", a["id"])
        self.assertIn("## Requirements\n\n**Filed:** 2026-08-17\n\nSome intro text that is the gist.", show)
        self.assertNotIn("**Priority:**", show)
        self.assertNotIn("\n\n\n", show)
        self.assertNotIn("> **Update", show)
        self.assertNotIn("## Open questions", show)
        self.assertIn("## Design", show)
        self.assertIn("## [migrator] 2026-08-20 00:00 UTC\n**Update 2026-08-20 (agent):**\nShipped the first piece.\nSecond line of the update.", show)
        self.assertIn("## [migrator] 2026-08-17 00:00 UTC · question\nWhich registry hosts the image?", show)
        # Links: the sibling file and the intra-backlog link inside the imported story point at the new files.
        order = (self.repo / "docs" / "ORDER.md").read_text()
        self.assertIn(f"../.skald/stories/{a['id']}-", order)
        self.assertNotIn("docs/backlog", order)
        self.assertIn(f"{b['id']}", show)
        self.assertNotIn("sdlc-low-other.md", show)
        self.assertIn("links: rewrote", out)
        # Sources are gone; one commit carries removal and creation and git pairs them as a rename.
        self.assertFalse((self.backlog / "fleet-hosts" / "sdlc-low-other.md").exists())
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "import backlog")
        story_path = next((self.skald_dir / "stories").glob(f"{b['id']}-*.md"))
        follow = git(self.repo, "log", "--follow", "--oneline", "--", str(story_path.relative_to(self.repo)))
        self.assertEqual(len(follow.strip().splitlines()), 2, follow)
        self.assertEqual(self.run_cli("check")[0], 0)

    def test_problems_abort_and_status_override(self):
        (self.backlog / "fleet-hosts" / "nodate.md").write_text("# No date\n\nbody\n", encoding="utf-8")
        code, out, err = self.run_cli("import", str(self.backlog), "--map", "map.json")
        self.assertEqual(code, 1)
        self.assertIn("nodate.md: created_at: no match", err)
        self.assertEqual(list((self.skald_dir / "stories").glob("*.md")), [])
        code, out, err = self.run_cli("import", str(self.backlog / "fleet-hosts" / "sdlc-low-other.md"), "--status", "ready")
        self.assertEqual(code, 0, err)
        s = json.loads(self.run_cli("ls", "--json")[1])[0]
        self.assertEqual((s["status"], s["title"], s["tags"]), ("ready", "Other record", []))
