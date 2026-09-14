"""skald digest: what changed since you last looked, grouped by story."""
import json

from skald import cli

from .helpers import SkaldTestCase, git


class TestDigest(SkaldTestCase):
    def _commit(self, msg: str) -> None:
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", msg)

    def test_since_parsing(self):
        self.assertEqual(cli._digest_since("1d"), ("1 days ago", True, "the last 1d"))
        self.assertEqual(cli._digest_since("6h"), ("6 hours ago", True, "the last 6h"))
        self.assertEqual(cli._digest_since("30m"), ("30 minutes ago", True, "the last 30m"))
        self.assertEqual(cli._digest_since("2w"), ("2 weeks ago", True, "the last 2w"))
        self.assertEqual(cli._digest_since("HEAD~3"), ("HEAD~3", False, "HEAD~3..HEAD"))
        self.assertEqual(cli._digest_since("abc1234"), ("abc1234", False, "abc1234..HEAD"))

    def test_digest_groups_moves_notes_questions(self):
        a = self.new("Design schema", "--status", "ready")
        b = self.new("Build API", "--status", "ready")
        self._commit("add stories")
        self.run_cli("claim", a, "--as", "claude")  # ready -> in_progress
        self.run_cli("note", a, "Started work", "--as", "claude", "--kind", "handoff")
        self.run_cli("note", b, "Which auth scheme?", "--as", "claude", "--kind", "question")
        self._commit("progress")

        code, out, err = self.run_cli("digest", "--since", "HEAD~1")
        self.assertEqual(code, 0, err)
        self.assertIn("2 stories changed", out)
        self.assertIn(f"{a}  Design schema   in_progress", out)
        self.assertIn("moved ready -> in_progress", out)
        self.assertIn("latest (handoff", out)
        self.assertIn("Q1 asks: Which auth scheme?", out)

        code, out, _ = self.run_cli("digest", "--since", "HEAD~1", "--json")
        d = json.loads(out)
        self.assertEqual({s["id"] for s in d["stories"]}, {a, b})
        by = {s["id"]: s for s in d["stories"]}
        self.assertEqual(by[a]["moves"], [["ready", "in_progress"]])
        self.assertEqual(len(by[b]["questions"]), 1)

        # the cap points at activity for the rest
        code, out, _ = self.run_cli("digest", "--since", "HEAD~1", "--limit", "1")
        self.assertIn("... and 1 more: skald activity --since HEAD~1", out)

    def test_digest_empty_range(self):
        self.new("A story", "--status", "ready")
        self._commit("one")
        code, out, err = self.run_cli("digest", "--since", "HEAD")
        self.assertEqual(code, 0, err)
        self.assertIn("Nothing changed", out)
