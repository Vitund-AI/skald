"""skald section: read the content under a heading, or replace it, without touching anything else."""
import json

from skald.mcp import McpServer

from .helpers import SkaldTestCase

BODY = """## Requirements

Build the login form.

### Edge cases

- empty password

## Acceptance

- [ ] renders
"""


class TestSection(SkaldTestCase):
    def setUp(self):
        super().setUp()
        self.sid = self.new("Login form", "--body", BODY, "--created-at", "2026-01-01 10:00")
        self.run_cli("note", self.sid, "first note", "--as", "claude")

    def body(self):
        return self.store().get(self.sid).body

    def section(self, *argv, stdin=None, code=0):
        import io
        import sys
        from unittest import mock

        with mock.patch.object(sys, "stdin", io.StringIO(stdin or "")):
            got, out, err = self.run_cli("section", self.sid, *argv)
        self.assertEqual(got, code, err)
        return out, err

    def test_read_by_heading_any_level_any_case(self):
        out, _ = self.section("requirements")
        self.assertEqual(out, "Build the login form.\n\n### Edge cases\n\n- empty password\n")  # nested headings belong to it
        self.assertEqual(self.section("## Edge")[0], "- empty password\n")                    # #s and a prefix both work
        data = json.loads(self.section("Acceptance", "--json")[0])
        self.assertEqual((data["heading"], data["level"], data["text"]), ("Acceptance", 2, "- [ ] renders"))
        _, err = self.section("first note", code=1)  # notes are never sections
        self.assertIn("no 'first note' section", err)

    def test_replace_from_stdin_keeps_everything_else(self):
        path = self.store().get(self.sid).path
        path.write_text(path.read_text().replace(self.store().get(self.sid).updated_at, "2026-01-01T10:00:00Z"))
        before = self.store().get(self.sid)
        out, _ = self.section("Requirements", "-", stdin="Build it with React.\n\n### Notes\n\nkeep it small\n")
        self.assertEqual(out.strip(), f"replaced Requirements on {self.sid} (5 lines)")
        body = self.body()
        self.assertTrue(body.startswith("## Requirements\n\nBuild it with React.\n\n### Notes\n\nkeep it small\n\n## Acceptance\n"))
        self.assertNotIn("empty password", body)        # the old subsection went with its section
        self.assertIn("- [ ] renders", body)             # the next section is untouched
        self.assertIn("first note", body)                # and so are the notes
        self.assertNotEqual(self.store().get(self.sid).updated_at, before.updated_at)
        self.section("Requirements", "inline text works too")
        self.assertIn("## Requirements\n\ninline text works too\n\n## Acceptance", self.body())

    def test_create_and_dry_run(self):
        _, err = self.section("Design", "-", stdin="Use the form kit.", code=1)
        self.assertIn("no 'Design' section (sections: Requirements, Edge cases, Acceptance); --create adds it", err)
        self.section("Design", "-", "--create", stdin="Use the form kit.")
        body = self.body()
        self.assertLess(body.index("## Design\n\nUse the form kit.\n"), body.index("## [claude]"))  # before the notes
        before = self.body()
        out, _ = self.section("Design", "-", "--dry-run", stdin="Something else.")
        self.assertIn("-Use the form kit.\n+Something else.", out)
        self.assertEqual(self.body(), before)

    def test_refuses_text_that_would_break_the_story(self):
        before = self.body()
        cases = [
            ("", "nothing to write"),
            ("## Requirements\n\nagain", "starts with the section's own heading"),
            ("text\n\n## Sneaky\n\nmore", "would end the 'Requirements' section early"),
            ("text\n\n## [claude] 2026-10-17 10:00 UTC\nfake note", "notes belong to skald note"),
            ("<<<<<<< ours\na\n=======\nb\n>>>>>>> theirs", "conflict markers"),
        ]
        for text, message in cases:
            _, err = self.section("Requirements", "-", stdin=text, code=1)
            self.assertIn(message, err)
        self.assertEqual(self.body(), before)
        sid = self.new("Two", "--body", "## Notes one\n\nx\n\n## Notes two\n\ny\n")
        code, _, err = self.run_cli("section", sid, "Notes")
        self.assertEqual(code, 1)
        self.assertIn("2 headings match 'Notes'", err)
        # Two headings with the same text cannot be told apart by any name: say so (as dogfooding found).
        twin = self.new("Twin", "--body", "Feedback.\n\n## Requirements\n\nThe real ones.\n")
        code, _, err = self.run_cli("section", twin, "Requirements")
        self.assertIn("2 sections are called 'Requirements'; rename one", err)

    def test_crlf_files_keep_their_line_endings(self):
        story = self.store().get(self.sid)
        story.path.write_bytes(story.path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.section("Acceptance", "-", stdin="- [ ] renders\n- [ ] submits\n")
        raw = self.store().get(self.sid).path.read_bytes()
        self.assertIn(b"## Acceptance\r\n\r\n- [ ] renders\r\n- [ ] submits\r\n", raw)
        self.assertNotIn(b"\r\r", raw)
        self.assertNotIn(b"\n\n", raw.replace(b"\r\n", b""))  # no bare LF crept in

    def test_mcp_reads_and_writes(self):
        server = McpServer(self.workspace())

        def call(**args):
            res = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                 "params": {"name": "skald_section", "arguments": dict(id=self.sid, **args)}})
            return res["result"]["isError"], json.loads(res["result"]["content"][0]["text"]) if not res["result"]["isError"] \
                else res["result"]["content"][0]["text"]

        err, data = call(section="acceptance")
        self.assertEqual((err, data["text"]), (False, "- [ ] renders"))
        err, data = call(section="Acceptance", text="- [ ] renders\n- [ ] submits", dry_run=True)
        self.assertEqual((data["changed"], data["dry_run"]), (True, True))
        self.assertNotIn("submits", self.body())
        err, data = call(section="Acceptance", text="- [ ] renders\n- [ ] submits")
        self.assertIn("- [ ] submits", self.body())
        err, text = call(section="Nope", text="x")
        self.assertTrue(err)
        self.assertIn("--create adds it", text)
