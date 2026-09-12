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

The design, with a link to [the other record](../fleet-hosts/sdlc-low-other.md)
and the bare name `sdlc-low-other.md` as siblings cite each other.

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
        # Written with Windows line endings, as a checkout on Windows would have it.
        (self.backlog / "fleet-hosts" / "sdlc-low-other.md").write_bytes(RECORD_B.replace("\n", "\r\n").encode("utf-8"))
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
        self.assertNotIn("\r", self.run_cli("show", b["id"])[1])  # CRLF source, LF story
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
        strict = dict(MAPPING, created_at=dict(MAPPING["created_at"], fallback="error"))
        (self.repo / "strict.json").write_text(json.dumps(strict), encoding="utf-8")
        code, out, err = self.run_cli("import", str(self.backlog), "--map", "strict.json")
        self.assertEqual(code, 1)
        self.assertIn("nodate.md: created_at: no match", err)
        self.assertEqual(list((self.skald_dir / "stories").glob("*.md")), [])
        code, out, err = self.run_cli("import", str(self.backlog / "fleet-hosts" / "sdlc-low-other.md"), "--status", "ready")
        self.assertEqual(code, 0, err)
        s = json.loads(self.run_cli("ls", "--json")[1])[0]
        self.assertEqual((s["status"], s["title"], s["tags"]), ("ready", "Other record", []))

    def test_links_resolve_across_roots_and_ancestors(self):
        # A bucket-relative link from another bucket, a repository-relative link outside ROOT, and the
        # stories themselves, which live outside ROOT when ROOT is docs/.
        (self.backlog / "storage").mkdir()
        (self.backlog / "storage" / "README.md").write_text("Pairs with `fleet-hosts/sdlc-low-other.md` (bucket-relative).\n", encoding="utf-8")  # excluded, so it stays
        (self.repo / "docs" / "HANDOFF.md").write_text("Start at docs/backlog/fleet-hosts/sdlc-low-other.md (repository-relative).\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "more links")
        code, out, err = self.run_cli("import", str(self.backlog), "--map", "map.json", "--rm",
                                      "--rewrite-links", str(self.repo / "docs"))
        self.assertEqual(code, 0, err)
        stories = {s["title"]: s for s in json.loads(self.run_cli("ls", "--json")[1])}
        a, b = stories["Build placement must follow the audience"], stories["Other record"]
        show = self.run_cli("show", a["id"])[1]
        self.assertNotIn("sdlc-low-other.md", show)
        self.assertEqual(show.count(f"{b['id']}-other-record.md"), 2, show)  # the ../fleet-hosts/ link and the bare name
        disk = (self.backlog / "storage" / "README.md").read_text()
        self.assertIn(f"../../../.skald/stories/{b['id']}-other-record.md", disk)
        handoff = (self.repo / "docs" / "HANDOFF.md").read_text()
        self.assertIn(f".skald/stories/{b['id']}-other-record.md", handoff)
        self.assertNotIn("docs/backlog", handoff)
        self.assertIn("HANDOFF.md: 1", out)
        self.assertIn("backlog/storage/README.md: 1", out)

    def test_created_at_from_git_path_tags_and_cli_tags(self):
        # No created_at rule: the date is the commit that added the file. A path rule sees the bucket even
        # when only that bucket is imported; --tag adds fixed tags.
        mapping = {"tags": [{"regex": "^docs/backlog/([a-z-]+)/", "on": "path", "tag": "area:$1"}]}
        (self.repo / "m.json").write_text(json.dumps(mapping), encoding="utf-8")
        added = git(self.repo, "log", "--diff-filter=A", "--format=%at", "--", "docs/backlog/fleet-hosts/sdlc-low-other.md").strip()
        code, out, err = self.run_cli("import", str(self.backlog / "fleet-hosts"), "--map", "m.json", "--tag", "wave:1", "--dry-run")
        self.assertEqual(code, 0, err)
        self.assertIn("(from git, the commit that added the file)", out)
        self.assertIn("tags:       area:fleet-hosts, wave:1", out)
        code, out, err = self.run_cli("import", str(self.backlog / "fleet-hosts"), "--map", "m.json", "--tag", "wave:1")
        self.assertEqual(code, 0, err)
        b = {s["title"]: s for s in json.loads(self.run_cli("ls", "--json")[1])}["Other record"]
        self.assertEqual(b["tags"], ["area:fleet-hosts", "wave:1"])
        from datetime import datetime, timezone
        expected = datetime.fromtimestamp(int(added), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual(b["created_at"], expected)
        # A record outside git falls back to now, and a regex still wins over git.
        outside = self.repo.parent / "loose.md"
        outside.write_text("# Loose\n\n**Filed:** 2025-01-02\n", encoding="utf-8")
        code, out, _ = self.run_cli("import", str(outside), "--dry-run")
        self.assertIn("created_at: (now)  (no rule matched)", out)
        code, out, _ = self.run_cli("import", str(outside), "--map", "map.json", "--dry-run")
        self.assertIn("created_at: 2025-01-02  (from the mapping)", out)

    def test_mapping_is_validated_before_any_file_is_read(self):
        from skald import importer as imp
        bad = {
            "created_at": {"regex": "(\\d+", "fallback": "sometimes"},
            "status": [{"regex": "^x", "on": "nowhere", "status": "nope"}, {"oops": 1}],
            "tags": [{"regex": "^(a)-", "on": "filename", "tag": "priority:$2"}, {"regex": "^a"}],
            "notes": [{"kind": "Not Valid", "block": "^>", "date_group": 3}, {"section": "^## Q", "per": "line"}, {"kind": "x"}],
            "strip": ["["],
        }
        problems = imp.validate_mapping(bad, columns=["idea", "ready", "done"])
        for expected in (
            "created_at.regex: bad regex",
            "created_at: 'fallback' must be one of git-added, now, error",
            "status[0]: 'on' must be one of filename, relpath, path, body",
            "status[0]: 'nope' is not a column",
            "status[1]: needs 'regex' and 'status', or 'default'",
            "tags[0]: template refers to $2 but the regex has 1 group(s)",
            "tags[1]: needs 'regex' and 'tag'",
            "notes[0]: kind must be a short lowercase word",
            "notes[0]: 'date_group' is 3 but the block regex has 0 group(s)",
            "notes[1]: 'per' must be 'bullet' when given",
            "notes[2]: needs 'block' or 'section'",
            "strip[0]: bad regex",
        ):
            self.assertTrue(any(x.startswith(expected) for x in problems), (expected, problems))
        self.assertEqual(imp.validate_mapping(MAPPING, columns=["idea", "plan", "ready", "done"]), [])
        # On the command line the mapping fails before any file is read, naming the rule.
        (self.repo / "bad.json").write_text(json.dumps({"tags": [{"regex": "^(a)", "tag": "p:$2"}]}), encoding="utf-8")
        code, out, err = self.run_cli("import", str(self.backlog), "--map", "bad.json")
        self.assertEqual(code, 1)
        self.assertIn("bad.json: tags[0]: template refers to $2 but the regex has 1 group(s)", err)
        self.assertIn("nothing read", err)
        self.assertEqual(list((self.skald_dir / "stories").glob("*.md")), [])
