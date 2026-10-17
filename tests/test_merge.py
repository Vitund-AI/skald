"""skald merge-file: git's merge driver for story files, by rule and through real git merges."""
import os
import subprocess
import sys
from pathlib import Path

from skald.merge import merge_story
from skald.store import parse_story_text

from .helpers import SkaldTestCase, git

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ["backlog", "ready", "in_progress", "review", "done"]


def story(status="ready", rank=10, tags=("a", "b"), updated="2026-10-01T00:00:00Z", title="Login form",
          prelude="## Requirements\n\nBuild it.\n", notes=(), **extra):
    fields = [f'title: "{title}"', f'status: "{status}"', f"rank: {rank}",
              "tags: [" + ", ".join(f'"{t}"' for t in tags) + "]", "blocked_by: []",
              'created_at: "2026-10-01T00:00:00Z"', f'updated_at: "{updated}"']
    fields += [f'{k}: "{v}"' for k, v in extra.items()]
    body = prelude + "".join(f"\n## [{who}] {stamp} UTC\n{text}\n" for who, stamp, text in notes)
    return "---\n" + "\n".join(fields) + "\n---\n" + body


class TestMergeRules(SkaldTestCase):
    def merged(self, base, ours, theirs):
        text, conflicted = merge_story(base, ours, theirs, COLUMNS)
        fields, body = parse_story_text(text, "merged")  # the result must always be a valid story
        return fields, body, conflicted

    def test_different_fields_and_notes_merge_cleanly(self):
        base = story()
        ours = story(status="in_progress", tags=("a", "b", "c"), updated="2026-10-02T00:00:00Z",
                     notes=[("claude", "2026-10-02 10:00", "ours")])
        theirs = story(rank=5, tags=("b", "d"), updated="2026-10-03T00:00:00Z",
                       notes=[("codex", "2026-10-01 09:00", "theirs")])
        fields, body, conflicted = self.merged(base, ours, theirs)
        self.assertFalse(conflicted)
        self.assertEqual((fields["status"], fields["rank"]), ("in_progress", 5))  # each changed on one side
        self.assertEqual(fields["tags"], ["b", "c", "d"])                         # a removed, c and d added
        self.assertEqual(fields["updated_at"], "2026-10-03T00:00:00Z")            # the later
        self.assertLess(body.index("theirs"), body.index("ours"))                 # notes by timestamp

    def test_both_changed_the_same_field(self):
        base = story()
        ours = story(status="review", rank=3, title="Ours", updated="2026-10-02T00:00:00Z")
        theirs = story(status="in_progress", rank=7, title="Theirs", updated="2026-10-03T00:00:00Z")
        fields, _, _ = self.merged(base, ours, theirs)
        self.assertEqual(fields["status"], "review")                    # further along the workflow
        self.assertEqual((fields["rank"], fields["title"]), (7, "Theirs"))  # the most recent edit
        fields, _, _ = self.merged(base, theirs, ours)                  # symmetric whichever side is ours
        self.assertEqual((fields["status"], fields["rank"], fields["title"]), ("review", 7, "Theirs"))

    def test_a_note_on_both_sides_is_kept_once_and_a_removed_one_stays_removed(self):
        shared = ("claude", "2026-10-02 10:00", "claimed")
        old = ("jon", "2026-10-01 08:00", "stale remark")
        base = story(notes=[old])
        _, body, _ = self.merged(base, story(notes=[old, shared]), story(notes=[shared]))
        self.assertEqual(body.count("claimed"), 1)
        self.assertNotIn("stale remark", body)

    def test_fields_added_and_removed(self):
        base = story(assignee="claude")
        fields, _, _ = self.merged(base, story(), story(assignee="claude", parent="abc123"))
        self.assertNotIn("assignee", fields)          # ours removed it, theirs left it alone
        self.assertEqual(fields["parent"], "abc123")  # theirs added it

    def test_a_real_body_conflict_stays_in_the_body(self):
        base = story(prelude="## Requirements\n\nBuild it.\n")
        ours = story(prelude="## Requirements\n\nBuild it with React.\n", notes=[("claude", "2026-10-02 10:00", "n1")])
        theirs = story(prelude="## Requirements\n\nBuild it with Vue.\n", tags=("a", "b", "c"))
        fields, body, conflicted = self.merged(base, ours, theirs)
        self.assertTrue(conflicted)
        self.assertEqual(fields["tags"], ["a", "b", "c"])  # the front matter merged and parses
        self.assertIn("<<<<<<< ours", body)
        self.assertIn("Build it with React.", body)
        self.assertIn("Build it with Vue.", body)
        self.assertIn("n1", body)                          # notes are outside the conflict

    def test_an_unparseable_side_falls_back_to_a_line_merge(self):
        broken = "not a story\n"
        text, conflicted = merge_story(story(), broken, story(rank=4), COLUMNS)
        self.assertTrue(conflicted)
        self.assertIn("<<<<<<<", text)


class TestMergeDriverInGit(SkaldTestCase):
    """The driver as git runs it: installed by `skald hooks git --install`, then real merges and cherry-picks."""

    def setUp(self):
        super().setUp()
        env = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = os.pathsep.join(p for p in (str(ROOT / "src"), env) if p)
        self.addCleanup(lambda: os.environ.__setitem__("PYTHONPATH", env) if env is not None else os.environ.pop("PYTHONPATH", None))
        code, out, err = self.run_cli("hooks", "git", "--install")
        self.assertEqual(code, 0, err)
        self.assertIn("merge=skald", (self.repo / ".gitattributes").read_text())
        # Tests have no `skald` on PATH, so point the driver and the hooks at this interpreter.
        exe = Path(sys.executable).as_posix()
        git(self.repo, "config", "merge.skald.driver", f'"{exe}" -m skald merge-file %O %A %B %P')
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        hook.write_text(hook.read_text().replace("skald ", f'"{exe}" -m skald '))
        self.sid = self.new("Login form", "--status", "ready", "--tags", "a,b")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        self.main = git(self.repo, "symbolic-ref", "--short", "HEAD").strip()

    def on_branch(self, name, *commands):
        git(self.repo, "checkout", "-qb", name, self.main)
        for argv in commands:
            code, _, err = self.run_cli(*argv)
            self.assertEqual(code, 0, err)
        git(self.repo, "commit", "-qam", name)
        git(self.repo, "checkout", "-q", self.main)

    def test_parallel_agents_merge_without_conflict(self):
        self.on_branch("agent-one", ("claim", self.sid, "--as", "claude"), ("note", self.sid, "one", "--as", "claude"),
                       ("tag", self.sid, "+c"))
        self.on_branch("agent-two", ("note", self.sid, "two", "--as", "codex"), ("tag", self.sid, "-a", "+d"),
                       ("set", self.sid, "rank=3"))
        git(self.repo, "merge", "-q", "--no-edit", "agent-one")
        proc = subprocess.run(["git", "merge", "--no-edit", "agent-two"], cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        s = self.store().get(self.sid)
        self.assertEqual((s.status, s.assignee, s.rank), ("in_progress", "claude", 3))
        self.assertEqual(sorted(s.tags), ["b", "c", "d"])
        self.assertEqual([n["text"] for n in s.notes()], ["one", "two"])
        # The rendered board did not conflict either: the merge kept a copy, check calls it stale, render fixes it.
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertNotIn("<<<<<<<", (self.repo / ".skald" / "README.md").read_text())
        code, _, err = self.run_cli("check")
        self.assertEqual(code, 0, err)
        self.assertIn("README.md", err)  # the stale-render warning
        self.run_cli("render")
        self.assertEqual(self.run_cli("check")[2], "")

    def test_cherry_pick_merges_too(self):
        self.on_branch("agent-one", ("note", self.sid, "picked", "--as", "claude"))
        code, _, _ = self.run_cli("note", self.sid, "on main", "--as", "jon")
        git(self.repo, "commit", "-qam", "main note")
        sha = git(self.repo, "rev-parse", "agent-one").strip()
        proc = subprocess.run(["git", "cherry-pick", sha], cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(sorted(n["text"] for n in self.store().get(self.sid).notes()), ["on main", "picked"])

    def test_doctor_reports_the_driver(self):
        from skald import doctor

        merge = [r for r in doctor.run(self.repo) if r["name"] == "merge"]
        self.assertEqual([r["level"] for r in merge], ["ok"])
        git(self.repo, "config", "--unset", "merge.skald.driver")
        merge = [r for r in doctor.run(self.repo) if r["name"] == "merge"]
        self.assertEqual([r["level"] for r in merge], ["warn"])
