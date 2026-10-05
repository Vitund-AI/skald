"""The examples/ scripts, run end to end against a throwaway project."""
import json
import os
import subprocess
import sys
from pathlib import Path

from .helpers import SkaldTestCase

ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "examples" / "github-issues" / "sync.py"


def issue(number, title, state="OPEN", labels=(), comments=(), body="Steps to reproduce."):
    return {
        "number": number, "title": title, "state": state, "body": body,
        "url": f"https://github.com/acme/widgets/issues/{number}",
        "createdAt": f"2026-03-0{number}T09:30:00Z",
        "author": {"login": "reporter"},
        "labels": [{"name": n} for n in labels],
        "comments": [{"author": {"login": who}, "body": text, "createdAt": f"2026-03-0{number}T1{i}:00:00Z"}
                     for i, (who, text) in enumerate(comments)],
    }


class TestGitHubSyncExample(SkaldTestCase):
    def sync(self, issues, *argv):
        fixture = self.tmp / "issues.json"
        fixture.write_text(json.dumps(issues))
        # The child interpreter needs src/ the way tests/__init__.py gives it to this one.
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(p for p in (str(ROOT / "src"), os.environ.get("PYTHONPATH", "")) if p))
        proc = subprocess.run([sys.executable, str(SYNC), "--from-json", str(fixture), "--json", *argv],
                              capture_output=True, text=True, cwd=self.repo, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_imports_once_then_reports_drift(self):
        issues = [
            issue(1, "Crash on save", labels=["Type: Bug", "good first issue"],
                  comments=[("alice", "Seen on 2.1 too."), ("bob", "Fix incoming.")]),
            issue(2, "Old request", state="CLOSED"),
            issue(3, "-v flag is ignored", body="Café crashes 💥 when run with -v."),
        ]
        # A dry run reports and writes nothing.
        out = self.sync(issues, "--dry-run")
        self.assertEqual([r["issue"] for r in out["created"]], [1, 3])
        self.assertEqual(self.store().load_all()[0], [])

        # Open issues import; the closed one does not by default.
        out = self.sync(issues)
        self.assertEqual([r["issue"] for r in out["created"]], [1, 3])
        s = self.store()
        one = s.get(out["created"][0]["id"])
        self.assertEqual(one.title, "Crash on save")
        self.assertEqual(sorted(one.tags), ["gh:1", "good-first-issue", "type:bug"])
        self.assertTrue(one.created_at.startswith("2026-03-01T09:30"))
        self.assertIn("Imported from [acme/widgets#1](https://github.com/acme/widgets/issues/1).", one.body)
        self.assertEqual([(n["author"], n["kind"], n["text"]) for n in one.notes()],
                         [("alice", "comment", "Seen on 2.1 too."), ("bob", "comment", "Fix incoming.")])
        three = s.get(out["created"][1]["id"])
        self.assertEqual(three.title, "-v flag is ignored")
        self.assertIn("Café crashes 💥", three.body)

        # A re-run creates nothing and reports no drift.
        out = self.sync(issues)
        self.assertEqual(out["created"], [])
        self.assertEqual(out["already_imported"], 2)
        self.assertEqual(out["drift"], [])

        # --state all picks up the closed issue, once.
        out = self.sync(issues, "--state", "all")
        self.assertEqual([r["issue"] for r in out["created"]], [2])
        self.assertEqual(self.sync(issues, "--state", "all")["created"], [])

        # Drift is reported both ways, and nothing is changed.
        ids = {int(t[3:]): st.id for st in self.store().load_all()[0] for t in st.tags if t.startswith("gh:")}
        self.store().update(ids[3], status="done")
        issues[0]["state"] = "CLOSED"
        issues[0]["title"] = "Crash on save (Windows)"
        drift = self.sync(issues)["drift"]
        self.assertIn(f"issue #1 is closed on GitHub, but story {ids[1]} is still backlog", drift)
        self.assertIn(f"issue #1 is titled 'Crash on save (Windows)'; story {ids[1]} says 'Crash on save'", drift)
        self.assertIn(f"story {ids[3]} is done, but issue #3 is still open", drift)
        self.assertEqual(self.store().get(ids[1]).title, "Crash on save")

    def test_bots_closed_issues_and_failures(self):
        # Shapes the first run on real data turned up: bot logins, closed issues, an issue that cannot import.
        issues = [
            issue(1, "Merged change", state="CLOSED", comments=[("github-actions[bot]", "Backlog changes: none.")]),
            issue(2, "   "),
            issue(3, "Still open"),
        ]
        fixture = self.tmp / "issues.json"
        fixture.write_text(json.dumps(issues))
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(p for p in (str(ROOT / "src"), os.environ.get("PYTHONPATH", "")) if p))
        proc = subprocess.run([sys.executable, str(SYNC), "--from-json", str(fixture), "--state", "all", "--json"],
                              capture_output=True, text=True, cwd=self.repo, env=env)
        self.assertEqual(proc.returncode, 1, proc.stderr)  # one issue failed, the rest imported
        out = json.loads(proc.stdout)
        self.assertEqual([r["issue"] for r in out["created"]], [1, 3])
        self.assertEqual([f["issue"] for f in out["failed"]], [2])
        stories = {t: s for s in self.store().load_all()[0] for t in s.tags if t.startswith("gh:")}
        self.assertEqual(stories["gh:1"].status, "done")      # closed issue: finished work
        self.assertEqual(stories["gh:3"].status, "backlog")
        self.assertEqual([n["author"] for n in stories["gh:1"].notes()], ["github-actions (bot)"])
        # Re-run: nothing duplicated, and a closed issue in done is not drift.
        again = self.sync(issues[:1] + issues[2:], "--state", "all")
        self.assertEqual((again["created"], again["drift"], again["already_imported"]), ([], [], 2))

