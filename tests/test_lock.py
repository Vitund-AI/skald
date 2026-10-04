"""Concurrent mutations take turns: no lost update, one claim at a time, no rank collisions."""
import os
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

from .helpers import SkaldTestCase

ROOT = Path(__file__).resolve().parents[1]
N = 8

# Each child imports skald first, then waits at the start line, so the commands race for real.
CHILD = textwrap.dedent("""
    import os, sys, time
    from skald import cli
    go = sys.argv[1]
    while not os.path.exists(go):
        time.sleep(0.001)
    sys.exit(cli.main(sys.argv[2:]))
""")


class TestConcurrentMutations(SkaldTestCase):
    def race(self, commands):
        """Run each argv in its own process, released together; return (code, stdout, stderr) per command."""
        go = self.tmp / f"go-{time.monotonic_ns()}"
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(p for p in (str(ROOT / "src"), os.environ.get("PYTHONPATH", "")) if p),
                   PYTHONUTF8="1")
        procs = [subprocess.Popen([sys.executable, "-c", CHILD, str(go), *argv], cwd=self.repo, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                 for argv in commands]
        time.sleep(0.5)  # let every child import and reach the start line
        go.touch()
        out = []
        for p in procs:
            stdout, stderr = p.communicate(timeout=120)
            out.append((p.returncode, stdout, stderr))
        for code, _, err in out:
            self.assertEqual(code, 0, err)
        return out

    def test_concurrent_tags_are_all_kept(self):
        sid = self.new("Shared story")
        self.race([["tag", sid, f"+t{i}"] for i in range(N)])
        self.assertEqual(sorted(self.store().get(sid).tags), sorted(f"t{i}" for i in range(N)))

    def test_concurrent_claims_take_turns(self):
        sid = self.new("Contested story", "--status", "ready")
        out = self.race([["claim", sid, "--as", f"agent{i}"] for i in range(N)])
        # Serialised, exactly one claimant found the story free; every later one saw it taken.
        took_free = [err for _, _, err in out if "was assigned to" not in err]
        self.assertEqual(len(took_free), 1, [e for _, _, e in out])
        story = self.store().get(sid)
        self.assertIn(story.assignee, {f"agent{i}" for i in range(N)})
        self.assertEqual(story.status, "in_progress")

    def test_concurrent_creates_get_distinct_ranks(self):
        self.race([["new", f"Story {i}", "--status", "ready"] for i in range(N)])
        stories = [s for s in self.store().load_all()[0] if s.status == "ready"]
        self.assertEqual(len(stories), N)
        self.assertEqual(len({s.rank for s in stories}), N, [s.rank for s in stories])
        self.assertEqual(len({s.id for s in stories}), N)

    def test_threads_in_one_process_take_turns(self):
        # The board server's request threads each open their own Store on the same directory.
        sid = self.new("Threaded story")
        errors = []

        def tag(i):
            try:
                self.store().edit_tags(sid, [f"t{i}"])
            except Exception as e:  # pragma: no cover - surfaced by the assertion below
                errors.append(e)

        threads = [threading.Thread(target=tag, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(sorted(self.store().get(sid).tags), sorted(f"t{i}" for i in range(N)))

    def test_lock_is_reentrant_outside_the_repo_and_times_out(self):
        from skald.errors import LockTimeoutError
        from skald.lock import lock_path, project_lock

        path = lock_path(self.skald_dir)
        self.assertNotIn(self.repo.resolve(), path.resolve().parents)  # never in git status
        with project_lock(self.skald_dir):
            with project_lock(self.skald_dir):  # a locked method calling another
                pass
            # Another process cannot take it while this one holds it.
            env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), SKALD_LOCK_TIMEOUT="0.2")
            proc = subprocess.run([sys.executable, "-m", "skald", "tag", self.new("x"), "+y"],
                                  cwd=self.repo, env=env, capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SKALD_LOCK_TIMEOUT", proc.stderr)
        with self.assertRaises(LockTimeoutError):
            done = threading.Event()

            def hold():
                with project_lock(self.skald_dir):
                    done.wait(5)

            t = threading.Thread(target=hold)
            t.start()
            time.sleep(0.1)
            try:
                with project_lock(self.skald_dir, timeout=0.1):
                    pass
            finally:
                done.set()
                t.join()
