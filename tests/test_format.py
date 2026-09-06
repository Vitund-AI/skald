"""Story file format, project config, and pure helpers."""
import json
import unittest

from skald import store as st
from skald.config import DEFAULT_COLUMNS, ProjectConfig
from skald.errors import ConfigError, CorruptStoryError
from skald.util import checklist_progress, slugify

SAMPLE = """---
title: "Implement WireGuard overlay network"
status: "ready"
rank: 20
tags: ["infrastructure", "v1.0"]
blocked_by: ["7b21e0", "other:c4d811"]
assignee: "claude"
created_at: "2026-09-05T10:00:00Z"
updated_at: "2026-09-06T08:12:41Z"
estimate: 3
---
## Requirements

Configure wg0.

---
this line looks like a fence but is body
"""


class TestFormat(unittest.TestCase):
    def test_round_trip_preserves_body_and_unknown_fields(self):
        fields, body = st.parse_story_text(SAMPLE, "sample.md")
        self.assertEqual(fields["title"], "Implement WireGuard overlay network")
        self.assertEqual(fields["tags"], ["infrastructure", "v1.0"])
        self.assertEqual(fields["blocked_by"], ["7b21e0", "other:c4d811"])
        self.assertEqual(fields["assignee"], "claude")
        self.assertEqual(fields["estimate"], 3)
        self.assertTrue(body.startswith("## Requirements\n"))
        self.assertIn("\n---\nthis line looks like a fence", body)
        self.assertEqual(st.serialise_story(fields, body), SAMPLE)

    def test_empty_assignee_is_dropped(self):
        fields, _ = st.parse_story_text('---\ntitle: "t"\nstatus: "backlog"\nassignee: "  "\n---\n')
        self.assertNotIn("assignee", fields)
        self.assertNotIn("assignee", st.serialise_story(fields, ""))

    def test_crlf_body_is_preserved(self):
        text = "---\r\ntitle: \"x\"\r\nstatus: \"backlog\"\r\n---\r\nline one\r\nline two\r\n"
        fields, body = st.parse_story_text(text)
        self.assertEqual(body, "line one\r\nline two\r\n")
        self.assertEqual(fields["title"], "x")

    def test_missing_optional_fields_default(self):
        fields, body = st.parse_story_text('---\ntitle: "t"\nstatus: "backlog"\n---\n')
        self.assertEqual(fields["rank"], 0)
        self.assertEqual(fields["tags"], [])
        self.assertEqual(fields["blocked_by"], [])
        self.assertEqual(body, "")

    def test_any_status_string_parses(self):
        # Column membership is a store-level check so config edits never make files corrupt.
        fields, _ = st.parse_story_text('---\ntitle: "t"\nstatus: "qa"\n---\n')
        self.assertEqual(fields["status"], "qa")

    def test_corrupt_cases_name_the_line(self):
        cases = {
            "no fence": ("title: x\n", "line 1"),
            "unclosed": ('---\ntitle: "x"\n', "closing '---' fence not found"),
            "bad line": ('---\ntitle "x"\n---\n', "line 2"),
            "not json": ('---\ntitle: unquoted\nstatus: "backlog"\n---\n', "line 2"),
            "block list": ('---\ntitle: "x"\nstatus: "backlog"\ntags:\n  - a\n---\n', "line 4"),
            "empty status": ('---\ntitle: "x"\nstatus: ""\n---\n', "'status'"),
            "empty title": ('---\ntitle: " "\nstatus: "backlog"\n---\n', "'title'"),
            "bool rank": ('---\ntitle: "x"\nstatus: "backlog"\nrank: true\n---\n', "'rank'"),
            "duplicate": ('---\ntitle: "x"\ntitle: "y"\nstatus: "backlog"\n---\n', "duplicate"),
            "bad assignee": ('---\ntitle: "x"\nstatus: "backlog"\nassignee: 3\n---\n', "'assignee'"),
        }
        for name, (text, needle) in cases.items():
            with self.subTest(name):
                with self.assertRaises(CorruptStoryError) as cm:
                    st.parse_story_text(text, "f.md")
                self.assertIn(needle, str(cm.exception))

    def test_helpers(self):
        self.assertEqual(slugify('Write docs: the "guide"!'), "write-docs-the-guide")
        self.assertEqual(slugify("!!!"), "")
        self.assertEqual(st.id_from_filename("a3f9c2-some-slug.md"), "a3f9c2")
        self.assertIsNone(st.id_from_filename("notes.md"))
        self.assertEqual(st.split_ref("proj:abc123"), ("proj", "abc123"))
        self.assertEqual(st.split_ref("abc123"), (None, "abc123"))
        self.assertEqual(checklist_progress("- [ ] a\n- [x] b\n* [X] c\n1. [ ] d\nnot [ ] one"), (2, 4))


class TestProjectConfig(unittest.TestCase):
    def test_defaults_and_roles(self):
        c = ProjectConfig("demo")
        self.assertEqual(c.keys, [col["key"] for col in DEFAULT_COLUMNS])
        self.assertEqual(c.default_key, "backlog")
        self.assertEqual(c.first_active_key, "in_progress")
        self.assertTrue(c.is_terminal("done"))
        self.assertFalse(c.is_terminal("review"))
        self.assertTrue(c.warns_on("in_progress"))
        self.assertFalse(c.warns_on("backlog"))
        self.assertEqual(c.index("nope"), len(c.columns))

    def test_round_trip_and_extra_keys(self):
        data = {"format": 1, "name": "x", "columns": [
            {"key": "todo", "label": "To do", "role": "ready"},
            {"key": "doing", "label": "Doing", "role": "active", "limit": 2},
            {"key": "nope", "label": "Won't do", "role": "closed"},
        ], "custom": {"a": 1}}
        c = ProjectConfig.from_dict(data)
        self.assertEqual(c.to_dict(), data)
        self.assertEqual(c.default_key, "todo")
        self.assertTrue(c.is_closed("nope"))
        self.assertEqual(c.column("doing").limit, 2)

    def test_validation(self):
        bad = [
            ({"name": "Bad Name"}, "invalid project name"),
            ({"name": "x", "format": 99}, "newer"),
            ({"name": "x", "columns": []}, "non-empty"),
            ({"name": "x", "columns": [{"key": "A", "role": "done"}]}, "key"),
            ({"name": "x", "columns": [{"key": "a", "role": "weird"}]}, "role"),
            ({"name": "x", "columns": [{"key": "a", "role": "backlog"}]}, "done"),
            ({"name": "x", "columns": [{"key": "a", "role": "done"}, {"key": "a", "role": "done"}]}, "duplicate"),
            ({"name": "x", "columns": [{"key": "a", "role": "done", "limit": 0}]}, "limit"),
        ]
        for data, needle in bad:
            with self.subTest(str(data)):
                with self.assertRaises(ConfigError) as cm:
                    ProjectConfig.from_dict(data)
                self.assertIn(needle, str(cm.exception))

    def test_save_and_load(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            ProjectConfig("demo").save(p)
            loaded = ProjectConfig.load(p)
            self.assertEqual(loaded.name, "demo")
            self.assertEqual(json.loads(p.read_text())["format"], 1)
            p.write_text("{not json")
            with self.assertRaises(ConfigError):
                ProjectConfig.load(p)


if __name__ == "__main__":
    unittest.main()
