"""``skald audit``: extraction on a fixture body, then a temp repository where each check has something to find."""
import json
import subprocess

from skald import audit

from .helpers import SkaldTestCase, git


class TestExtraction(SkaldTestCase):
    def test_extract_paths_lines_and_hashes(self):
        body = (
            "See src/skald/cli.py:1338 and src/skald/server.py:761-764, plus docs/api.md. "
            "Fixed in a1b2c3d and 0123456789abcdef0123456789abcdef01234567; not 1234567 (digits only), "
            "nor abcdefg (not hex). cli.py:12 cites a bare file; https://example.com/x.html is a URL, not a path, "
            "and abc1234.py is a file, not a hash. Ends with cafebabe9."
        )
        c = audit.extract(body)
        # A bare filename is a claim only with a line reference; abc1234.py is neither a path claim nor a hash.
        self.assertEqual(c["paths"], ["src/skald/cli.py", "src/skald/server.py", "docs/api.md", "cli.py"])
        self.assertEqual(c["lines"], [("src/skald/cli.py", 1338), ("src/skald/server.py", 764), ("cli.py", 12)])
        self.assertEqual(c["commits"], ["a1b2c3d", "0123456789abcdef0123456789abcdef01234567", "cafebabe9"])

    def test_story_ids_are_not_hashes(self):
        self.assertEqual(audit.extract("blocked by a3f9c2 and 3f9c2a")["commits"], [])


class TestAuditCommand(SkaldTestCase):
    def test_audit_checks_and_notes(self):
        (self.repo / "src").mkdir()
        (self.repo / "src" / "keep.py").write_text("line1\nline2\nline3\n")
        (self.repo / "src" / "gone.py").write_text("x\n")
        (self.repo / "top.py").write_text("only\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "seed")
        # The full sha: a short one can be all digits, which the extractor rightly reads as a number.
        sha = git(self.repo, "rev-parse", "HEAD").strip()
        body = (f"Reads src/keep.py:2 and src/keep.py:10, deletes src/gone.py, and cites top.py:1. "
                f"Landed in {sha}; the earlier attempt was deadbeef1.")
        sid = self.new("Design", "--body", body)
        (self.repo / "src" / "gone.py").unlink()
        code, out, err = self.run_cli("audit", sid, "--no-note", "--json")
        self.assertEqual(code, 0, err)
        r = json.loads(out)
        self.assertEqual(r["paths"], {"checked": 3, "missing": ["src/gone.py"]})
        self.assertEqual(r["lines"]["checked"], 3)
        self.assertEqual(r["lines"]["past_end"], [{"ref": "src/keep.py:10", "lines": 3}])
        self.assertEqual(r["commits"], {"checked": 2, "missing": ["deadbeef1"], "unchecked": False})
        self.assertFalse(r["changed_since"]["audited_before"])
        self.assertFalse(r["noted"])
        code, out, _ = self.run_cli("resume", sid)
        self.assertIn("never audited", out)
        # With the note: the story gains an audit note and resume reports it.
        code, out, err = self.run_cli("audit", sid, "--as", "claude")
        self.assertEqual(code, 0, err)
        self.assertIn(f"audit {sid}  Design", out)
        self.assertIn("1 missing: src/gone.py", out)
        self.assertIn("src/keep.py:10 (file has 3)", out)
        self.assertIn("1 not found: deadbeef1", out)
        self.assertIn(f"noted on {sid} (audit)", out)
        code, out, _ = self.run_cli("resume", sid)
        self.assertIn("last audited", out)
        # Backdate the audit note, change a referenced file, commit: it shows as changed since. (git's
        # --since has minute precision, so the seed commit from the same minute would count too.)
        path = self.skald_dir / "stories"
        f = next(path.glob(f"{sid}-*.md"))
        text = f.read_text()
        import re
        text = re.sub(r"## \[claude\] \d{4}-\d\d-\d\d \d\d:\d\d UTC · audit", "## [claude] 2020-01-01 00:00 UTC · audit", text)
        f.write_text(text)
        (self.repo / "src" / "keep.py").write_text("line1\nline2\nline3\nline4\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "grow keep.py")
        code, out, _ = self.run_cli("audit", sid, "--no-note", "--json")
        r = json.loads(out)
        self.assertTrue(r["changed_since"]["audited_before"])
        self.assertEqual(sorted(r["changed_since"]["paths"]), ["src/keep.py", "top.py"])
        self.assertEqual(r["lines"]["past_end"], [{"ref": "src/keep.py:10", "lines": 4}])
        code, out, _ = self.run_cli("resume", sid)
        self.assertIn("2 referenced file(s) changed since", out)

    def test_audit_notes_flag_and_mcp(self):
        sid = self.new("Plain", "--body", "No claims here.")
        self.run_cli("note", sid, "see nowhere/missing.py", "--as", "x")
        code, out, _ = self.run_cli("audit", sid, "--no-note", "--json")
        self.assertEqual(json.loads(out)["paths"]["checked"], 0)
        code, out, _ = self.run_cli("audit", sid, "--no-note", "--notes", "--json")
        self.assertEqual(json.loads(out)["paths"]["missing"], ["nowhere/missing.py"])
