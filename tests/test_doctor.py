"""skald doctor: environment and wiring checks."""
import json
import os

from skald import doctor

from .helpers import SkaldTestCase, git


class TestDoctor(SkaldTestCase):
    def _levels(self, out):
        return {line.split("] ", 1)[1].split(":", 1)[0]: line[1:5].strip()
                for line in out.splitlines() if line.startswith("[")}

    def test_healthy_project_passes(self):
        # a wired-up project: install the Claude hooks so nothing is red or yellow
        self.run_cli("hooks", "claude", "--install", "--as", "claude")
        code, out, err = self.run_cli("doctor")
        self.assertEqual(code, 0, out)
        lv = self._levels(out)
        self.assertEqual(lv["python"], "ok")
        self.assertEqual(lv["config.json"], "ok")
        self.assertEqual(lv["git identity"], "ok")
        self.assertEqual(lv["claude hooks"], "ok")
        self.assertEqual(lv["contract"], "ok")
        self.assertEqual(lv["backlog"], "ok")  # folds in `check`
        self.assertIn("all good", out)

    def test_broken_config_fails(self):
        (self.skald_dir / "config.json").write_text("{ not json")
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", out)
        self.assertIn("failed", out)

    def test_missing_git_identity_fails(self):
        # isolate from any global/system identity, then drop the local name
        for var, prev in (("GIT_CONFIG_GLOBAL", os.devnull), ("GIT_CONFIG_SYSTEM", os.devnull)):
            self._env_backup = getattr(self, "_env_backup", {})
            self._env_backup[var] = os.environ.get(var)
            os.environ[var] = prev
        self.addCleanup(lambda: [os.environ.__setitem__(k, v) if v is not None else os.environ.pop(k, None)
                                 for k, v in self._env_backup.items()])
        git(self.repo, "config", "--unset", "user.name")
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 1)
        self.assertEqual(self._levels(out)["git identity"], "FAIL")
        self.assertIn("git config user.name", out)

    def test_json_output(self):
        code, out, _ = self.run_cli("doctor", "--json")
        d = json.loads(out)
        self.assertTrue(d["ok"])
        self.assertEqual(d["failed"], 0)
        names = {c["name"] for c in d["checks"]}
        self.assertLessEqual({"python", "git", "config.json", "registry", "server", "backlog"}, names)

    def test_backlog_problem_is_folded_in(self):
        # a corrupt story makes `check` fail; doctor's backlog row reflects it
        (self.skald_dir / "stories" / "zzzzzz-bad.md").write_text("---\nnope\n---\n")
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 1)
        self.assertEqual(self._levels(out)["backlog"], "FAIL")

    def test_run_returns_structured_results(self):
        results = doctor.run(self.repo)
        by = {r["name"]: r for r in results}
        self.assertEqual(by["python"]["level"], doctor.OK)
        self.assertIn("home", by)
        self.assertNotIn("update", by)  # no cached update state, and doctor never queries the network

    def test_reports_cached_update_without_network(self):
        import json as _json

        from skald import update as upd
        (self.home / "update.json").write_text(_json.dumps({"checked_at": "2099-01-01T00:00:00Z", "latest": "99.0.0"}))
        # No network: doctor reads only the cache the board left behind.
        self.addCleanup(setattr, upd, "fetch_latest", upd.fetch_latest)

        def boom(timeout=upd.TIMEOUT):
            raise AssertionError("doctor must not hit the network")
        upd.fetch_latest = boom
        by = {r["name"]: r for r in doctor.run(self.repo)}
        self.assertIn("update", by)
        self.assertIn("99.0.0", by["update"]["detail"])
