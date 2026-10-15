"""skald tick / untick: ticking checklist items by number instead of editing the file."""
import json
import time

from skald.mcp import McpServer
from skald.store import acceptance_progress, heading_of, section_of, sections_of, task_items

from .helpers import SkaldTestCase

BODY = """Build the login form.

## Requirements

- [ ] not an acceptance item

## Acceptance

- [ ] renders on mobile
- [x] styled
  - [ ] nested: keyboard reachable
1. [ ] numbered list item

```md
- [ ] an example in a fence, never counted
```

### Edge cases

- [ ] empty password refused

## Test plan

- [ ] run on Windows
"""


class TestTaskItems(SkaldTestCase):
    def test_numbering_follows_the_section_and_skips_fences(self):
        items = task_items(BODY)
        self.assertEqual([(i["number"], i["done"], i["text"]) for i in items], [
            (1, False, "renders on mobile"), (2, True, "styled"), (3, False, "nested: keyboard reachable"),
            (4, False, "numbered list item"), (5, False, "empty password refused")])  # ### Edge cases is part of it
        self.assertEqual(acceptance_progress(BODY), (1, 5))  # the board and the review warning count the same items
        self.assertEqual([i["text"] for i in task_items(BODY, "test PLAN")], ["run on Windows"])
        self.assertEqual([i["text"] for i in task_items(BODY, "edge")], ["empty password refused"])  # prefix

    def test_errors_say_what_there_is(self):
        with self.assertRaisesRegex(Exception, "no 'Deploy' section; sections with items: Requirements, Acceptance, Edge cases, Test plan"):
            task_items(BODY, "Deploy")
        with self.assertRaisesRegex(Exception, "2 headings match 'Notes'"):
            task_items("## Notes one\n- [ ] a\n## Notes two\n- [ ] b\n", "Notes")
        self.assertEqual(acceptance_progress("no headings at all"), (0, 0))

    def test_heading_parsing_is_linear_on_hostile_input(self):
        # Story bodies come from anyone with write access; the old heading patterns backtracked
        # quadratically on a long run of spaces (minutes at this size), CodeQL's ReDoS finding.
        body = "## a" + " " * 200_000 + "b\n\n## Acceptance\n\n- [ ] x\n"
        start = time.perf_counter()
        self.assertEqual(len(task_items(body)), 1)
        sections_of(body)
        section_of(body, "acc")
        self.assertLess(time.perf_counter() - start, 2.0)
        self.assertEqual([heading_of(h) for h in ("## Title ##", "## C#", "##   ", "## [claude] 2026", "#tag")],
                         [(2, "Title"), (2, "C#"), None, None, None])

    def test_notes_are_not_addressable(self):
        body = "## Acceptance\n\n- [ ] real\n\n## [claude] 2026-10-15 10:00 UTC · handoff\n\n- [ ] inside a note\n"
        self.assertEqual([i["text"] for i in task_items(body)], ["real"])


class TestTickCommand(SkaldTestCase):
    def setUp(self):
        super().setUp()
        self.sid = self.new("Login form", "--body", BODY, "--created-at", "2026-01-01 10:00")

    def body(self):
        return self.store().get(self.sid).body

    def test_tick_and_untick_change_only_the_box(self):
        before = self.store().get(self.sid)
        code, out, err = self.run_cli("tick", self.sid, "1", "3")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.strip(), f"ticked 1, 3 on {self.sid}; Acceptance 3/5")
        after = self.body()
        self.assertIn("- [x] renders on mobile", after)
        self.assertIn("  - [x] nested: keyboard reachable", after)
        self.assertIn("- [ ] not an acceptance item", after)  # other sections untouched
        self.assertIn("- [ ] an example in a fence", after)
        self.assertEqual(len(after.splitlines()), len(before.body.splitlines()))
        self.assertNotEqual(self.store().get(self.sid).updated_at, before.updated_at)  # backdated, so a bump shows

        code, out, _ = self.run_cli("tick", self.sid, "1", "2")
        self.assertEqual(out.strip(), f"nothing changed on {self.sid} (1, 2 already ticked); Acceptance 3/5")
        code, out, _ = self.run_cli("untick", self.sid, "2")
        self.assertEqual(out.strip(), f"unticked 2 on {self.sid}; Acceptance 2/5")
        self.assertIn("- [ ] styled", self.body())

    def test_other_section_and_listing(self):
        code, out, _ = self.run_cli("tick", self.sid, "1", "--section", "test plan")
        self.assertEqual(out.strip(), f"ticked 1 on {self.sid}; test plan 1/1")
        self.assertIn("- [x] run on Windows", self.body())
        code, out, _ = self.run_cli("untick", self.sid)  # no numbers: list, change nothing
        self.assertEqual(out.splitlines()[:3], [f"{self.sid}  Acceptance 1/5", "   1 [ ] renders on mobile", "   2 [x] styled"])
        code, out, _ = self.run_cli("tick", self.sid, "5", "--json")
        data = json.loads(out)
        self.assertEqual((data["changed"], data["items"][4]), ([5], {"number": 5, "done": True, "text": "empty password refused"}))

    def test_bad_number_changes_nothing(self):
        before = self.body()
        code, _, err = self.run_cli("tick", self.sid, "1", "9")
        self.assertEqual(code, 1)
        self.assertIn(f"no item 9; Acceptance has 5 items (skald tick {self.sid} lists them)", err)
        self.assertEqual(self.body(), before)
        code, _, err = self.run_cli("tick", self.sid, "1", "--section", "deploy")
        self.assertIn("sections with items:", err)

    def test_crlf_files_keep_their_line_endings(self):
        story = self.store().get(self.sid)
        story.path.write_bytes(story.path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.run_cli("tick", self.sid, "1")
        raw = self.store().get(self.sid).path.read_bytes()
        self.assertIn(b"- [x] renders on mobile\r\n", raw)
        self.assertNotIn(b"\r\r", raw)

    def test_resume_numbers_the_acceptance_items(self):
        code, out, _ = self.run_cli("resume", self.sid)
        self.assertIn(f"Acceptance (tick with skald tick {self.sid} N):", out)
        self.assertIn("   4 [ ] numbered list item", out)
        data = json.loads(self.run_cli("resume", self.sid, "--json")[1])
        self.assertEqual(data["acceptance_items"][1], {"number": 2, "done": True, "text": "styled"})

    def test_mcp_tick_and_untick(self):
        server = McpServer(self.workspace())

        def call(name, **args):
            res = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})
            return res["result"]["isError"], res["result"]["content"][0]["text"]

        err, text = call("skald_tick", id=self.sid, items=[1, 4])
        self.assertFalse(err, text)
        self.assertEqual(json.loads(text)["changed"], [1, 4])
        err, text = call("skald_untick", id=self.sid, items=[4], section="Acceptance")
        self.assertEqual(json.loads(text)["changed"], [4])
        err, text = call("skald_tick", id=self.sid, items=["one"])
        self.assertTrue(err)
        self.assertIn("items must be a list of item numbers", text)
