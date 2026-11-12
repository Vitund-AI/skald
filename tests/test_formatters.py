"""Keeping Prettier off .skald/: what `skald init` writes and what `skald doctor` says (D87)."""
import json

from skald import doctor
from skald.formatters import ensure_prettierignore, ignores_skald, prettier_evidence

from .helpers import SkaldTestCase


class TestPrettierIgnore(SkaldTestCase):
    def fresh(self, name="web"):
        return self.make_repo(name, init_skald=False)

    def init(self, repo):
        code, out, err = self.run_cli("init", cwd=repo)
        self.assertEqual(code, 0, err)
        return out

    def test_no_prettier_no_file(self):
        repo = self.fresh()
        (repo / "package.json").write_text(json.dumps({"devDependencies": {"eslint": "9"}}))
        out = self.init(repo)
        self.assertFalse((repo / ".prettierignore").exists())
        self.assertNotIn("prettierignore", out)

    def test_created_when_prettier_is_configured(self):
        for i, evidence in enumerate((".prettierrc", "prettier.config.mjs", "package.json")):
            with self.subTest(evidence=evidence):
                repo = self.fresh(f"p{i}")
                if evidence == "package.json":
                    (repo / evidence).write_text(json.dumps({"devDependencies": {"prettier": "^3.6.2"}}))
                else:
                    (repo / evidence).write_text("{}")
                out = self.init(repo)
                self.assertIn(f"created .prettierignore with .skald/ (Prettier is configured here: {evidence})", out)
                self.assertIn(".skald/\n", (repo / ".prettierignore").read_text())

    def test_prettier_key_in_package_json_counts(self):
        repo = self.fresh()
        (repo / "package.json").write_text(json.dumps({"prettier": {"semi": False}}))
        self.assertEqual(prettier_evidence(repo), "package.json")

    def test_appended_once_keeping_line_endings(self):
        repo = self.fresh()
        (repo / ".prettierignore").write_bytes(b"dist\r\nbuild")  # CRLF, no final newline
        out = self.init(repo)
        self.assertIn("added .skald/ to .prettierignore", out)
        self.assertEqual((repo / ".prettierignore").read_bytes(), b"dist\r\nbuild\r\n.skald/\r\n")
        out = self.init(repo)  # rerunning init is the upgrade path, and it is idempotent
        self.assertIn(".prettierignore already skips .skald/", out)
        self.assertEqual((repo / ".prettierignore").read_bytes(), b"dist\r\nbuild\r\n.skald/\r\n")

    def test_existing_covering_lines_are_respected(self):
        for line in (".skald", "/.skald/", "**/.skald", ".skald/**"):
            self.assertTrue(ignores_skald(f"node_modules\n  {line}  \n"), line)
        self.assertFalse(ignores_skald("# .skald/\n.skaldx\n!.skald/\n"))
        repo = self.fresh()
        (repo / ".prettierignore").write_text("/.skald\n")
        self.assertEqual(ensure_prettierignore(repo), ".prettierignore already skips .skald/")
        self.assertEqual((repo / ".prettierignore").read_text(), "/.skald\n")

    def test_unreadable_package_json_is_no_evidence(self):
        repo = self.fresh()
        (repo / "package.json").write_text("{ not json")
        self.assertIsNone(prettier_evidence(repo))

    def test_doctor(self):
        rows = lambda: [r for r in doctor.run(self.repo) if r["name"] == "prettier"]  # noqa: E731
        self.assertEqual(rows(), [])                                    # no Prettier: nothing to say
        (self.repo / ".prettierrc").write_text("{}")                    # Prettier added after init
        [row] = rows()
        self.assertEqual(row["level"], "warn")
        self.assertIn(".prettierrc", row["detail"])
        self.assertIn("rerun skald init", row["fix"])
        self.run_cli("init")
        [row] = rows()
        self.assertEqual(row["level"], "ok")
