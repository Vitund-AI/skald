"""Every CLI command through its entry function."""
import io
import json
import os
import sys
from pathlib import Path

from skald import cli
from skald.config import ProjectConfig
from skald.registry import Registry

from .helpers import SAMPLE_CONFIG_COLUMNS, SkaldTestCase, git

HEADERS = ["ID", "STATUS", "RANK", "BLOCKED", "ASSIGNEE", "TAGS", "TITLE"]


class TestInit(SkaldTestCase):
    def test_init_fresh_repo_then_rerun_is_safe(self):
        repo = self.make_repo("fresh", init_skald=False)
        code, out, err = self.run_cli("init", cwd=repo)
        self.assertEqual(code, 0, err)
        self.assertIn("created", out)
        self.assertIn("project 'fresh'", out)
        self.assertTrue((repo / ".skald" / "stories" / ".gitkeep").exists())
        self.assertTrue((repo / ".skald" / "AGENTS.md").exists())
        cfg = json.loads((repo / ".skald" / "config.json").read_text())
        self.assertEqual((cfg["name"], cfg["format"]), ("fresh", 1))
        self.assertEqual(Registry(self.home).path_of("fresh"), (repo / ".skald").resolve())
        (repo / ".skald" / "AGENTS.md").write_text("custom")
        code, out, err = self.run_cli("init", cwd=repo)
        self.assertEqual(code, 0, err)
        self.assertIn("found", out)
        self.assertIn("kept existing AGENTS.md", out)
        self.assertEqual((repo / ".skald" / "AGENTS.md").read_text(), "custom")
        code, out, _ = self.run_cli("init", "--name", "Renamed Thing", cwd=repo)
        self.assertIn("renamed project to 'renamed-thing'", out)

    def test_init_from_subdirectory_and_migration(self):
        sub = self.repo / "src"
        sub.mkdir()
        (self.skald_dir / "skald.py").write_text("legacy")
        git(self.repo, "config", "alias.skald", cli.OLD_ALIAS)
        code, out, err = self.run_cli("init", cwd=sub)
        self.assertEqual(code, 0, err)
        self.assertFalse((self.skald_dir / "skald.py").exists())
        self.assertIn("removed vendored", out)
        self.assertIn("removed the 0.1 git alias", out)
        self.assertNotIn("skald", git(self.repo, "config", "--list"))

    def test_agents_md_matches_package_template(self):
        code, _, _ = self.run_cli("init")
        self.assertEqual((self.skald_dir / "AGENTS.md").read_text(), cli.agents_template())


class TestStoryCommands(SkaldTestCase):
    def test_full_flow(self):
        a = self.new("Implement WireGuard", "--tags", "Infra,v1.0", "--body", "- [ ] wg0\n- [x] plan")
        b = self.new("Set up CI", "--status", "ready")
        c = self.new('Write "docs"', "--status", "ready", "--blocked-by", f"{a},{b}")
        self.assertRegex(a, r"^[0-9a-f]{6}$")

        code, out, err = self.run_cli("ls")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0].split(), HEADERS)
        self.assertEqual(len(lines), 4)
        self.assertIn(",".join(sorted([a, b])), out)
        self.assertIn("infra,v1.0", out)

        code, out, _ = self.run_cli("ls", "--unblocked", "--json")
        self.assertEqual([s["id"] for s in json.loads(out)], [a, b])
        self.assertEqual(json.loads(out)[0]["checklist"], {"done": 1, "total": 2})
        code, out, _ = self.run_cli("ls", "--tag", "INFRA", "--json")
        self.assertEqual([s["id"] for s in json.loads(out)], [a])
        code, out, _ = self.run_cli("ls", "--status", "ready", "--json")
        self.assertEqual([s["id"] for s in json.loads(out)], [b, c])

        code, out, _ = self.run_cli("next", "--json")
        self.assertEqual((code, json.loads(out)["id"]), (0, b))

        code, out, err = self.run_cli("move", c[:3], "in_progress")
        self.assertEqual(code, 0)
        self.assertIn(f"moved {c} to in_progress", out)
        self.assertIn(f"WARNING: {c} has unmet dependencies: ", err)
        self.assertIn(f"{a} (backlog)", err)

        code, out, err = self.run_cli("claim", b, "--as", "claude")
        self.assertEqual(code, 0, err)
        self.assertIn(f"{b} claimed by claude, now in_progress", out)
        code, out, _ = self.run_cli("ls", "--assignee", "claude", "--json")
        self.assertEqual([s["id"] for s in json.loads(out)], [b])
        code, out, err = self.run_cli("set", b, "assignee=")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.store().get(b).assignee, "")

        code, out, err = self.run_cli("tag", c, "+Docs", "-nothing")
        self.assertEqual(code, 0, err)
        self.assertIn("docs", out)
        code, out, err = self.run_cli("block", c, f"-{a}")
        self.assertEqual(code, 0, err)
        self.assertIn(f"blocked_by: {b}", out)
        code, out, err = self.run_cli("block", b, f"+{c}")
        self.assertIn("WARNING: dependency cycle", err)

        code, out, err = self.run_cli("set", c, "title=Docs rewritten", "rank=5")
        self.assertEqual(code, 0, err)
        code, out, _ = self.run_cli("show", c, "--json")
        d = json.loads(out)
        self.assertEqual((d["title"], d["rank"], d["status"], d["project"]), ("Docs rewritten", 5, "in_progress", "alpha"))
        self.assertIn("body_sha256", d)

        code, out, err = self.run_cli("note", c, "Claimed it")
        self.assertEqual(code, 0, err)
        code, out, _ = self.run_cli("show", c)
        self.assertTrue(out.startswith('---\ntitle: "Docs rewritten"\n'))
        self.assertIn("## [agent] ", out)
        self.assertTrue(out.endswith("Claimed it\n"))

        code, out, _ = self.run_cli("check")
        self.assertEqual(code, 2)
        self.assertIn("PROBLEM: dependency cycle", out)

        code, out, err = self.run_cli("rm", c)
        self.assertEqual(code, 1)
        self.assertIn("--force", err)
        code, out, err = self.run_cli("rm", c, "--force")
        self.assertEqual(code, 0, err)

    def test_identity_from_env_and_flag(self):
        a = self.new("a")
        os.environ["SKALD_AUTHOR"] = "env-bot"
        self.run_cli("note", a, "one")
        self.run_cli("note", a, "two", "--as", "flag-bot")
        body = self.store().get(a).body
        self.assertIn("## [env-bot]", body)
        self.assertIn("## [flag-bot]", body)
        os.environ.pop("SKALD_AUTHOR")
        self.assertEqual(cli.cli_identity(None), "agent")

    def test_human_identity_order(self):
        ws = self.workspace()
        self.assertEqual(cli.human_identity(ws.user, self.repo), "Alpha Tester")
        ws.user.set("author", "Jon")
        self.assertEqual(cli.human_identity(ws.user, self.repo), "Jon")
        os.environ["SKALD_AUTHOR"] = "env"
        self.assertEqual(cli.human_identity(ws.user, self.repo), "env")
        os.environ.pop("SKALD_AUTHOR")
        git(self.repo, "config", "--unset", "user.name")
        ws.user.unset("author")
        os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
        os.environ["GIT_CONFIG_SYSTEM"] = os.devnull
        try:
            self.assertEqual(cli.human_identity(ws.user, self.repo), "human")
        finally:
            os.environ.pop("GIT_CONFIG_GLOBAL")
            os.environ.pop("GIT_CONFIG_SYSTEM")

    def test_next_when_nothing_ready_and_done_hidden(self):
        a = self.new("a", "--status", "done")
        code, out, err = self.run_cli("next")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("no ready", err)
        code, out, _ = self.run_cli("ls", "--json")
        self.assertEqual(json.loads(out), [])
        code, out, _ = self.run_cli("ls", "--all", "--json")
        self.assertEqual([s["id"] for s in json.loads(out)], [a])

    def test_stdin_body_and_note(self):
        real_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO("Requirements from stdin\n")
            a = self.new("a", "--body", "-")
            sys.stdin = io.StringIO("note from stdin")
            code, _, err = self.run_cli("note", a, "-", "--as", "human")
        finally:
            sys.stdin = real_stdin
        self.assertEqual(code, 0, err)
        body = self.store().get(a).body
        self.assertIn("Requirements from stdin\n", body)
        self.assertTrue(body.endswith("note from stdin\n"))

    def test_errors_and_exit_codes(self):
        code, _, err = self.run_cli("show", "zzz")
        self.assertEqual(code, 1)
        self.assertIn("ERROR: no story matches", err)
        self.write_raw("bad000-x.md", "garbage")
        code, _, err = self.run_cli("show", "bad000")
        self.assertEqual(code, 2)
        code, out, err = self.run_cli("ls")
        self.assertEqual(code, 0)
        self.assertIn("WARNING: skipping corrupt story", err)
        a = self.new("a")
        for argv in (("set", a, "status=done"), ("set", a, "rank=x"), ("tag", a), ("tag", a, "plain"), ("move", a, "nowhere")):
            code, _, err = self.run_cli(*argv)
            self.assertEqual(code, 1, argv)
        code, _, _ = self.run_cli()
        self.assertEqual(code, 1)
        code, _, err = self.run_cli("ls", cwd=self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("no .skald directory", err)

    def test_templates_and_columns(self):
        code, out, _ = self.run_cli("templates")
        self.assertIn("no templates", out)
        (self.skald_dir / "templates").mkdir()
        (self.skald_dir / "templates" / "bug.md").write_text("## Steps\n")
        code, out, _ = self.run_cli("templates")
        self.assertEqual(out.strip(), "bug")
        a = self.new("crash", "--template", "bug")
        self.assertTrue(self.store().get(a).body.startswith("## Steps"))
        code, out, _ = self.run_cli("columns")
        self.assertIn("in_progress  In progress  active", out)
        code, out, _ = self.run_cli("columns", "--json")
        self.assertEqual(json.loads(out)[0]["key"], "backlog")

    def test_archive_commands(self):
        a = self.new("a", "--status", "done")
        code, out, _ = self.run_cli("archive", "--dry-run")
        self.assertIn(f"would archive {a}", out)
        code, out, _ = self.run_cli("archive")
        self.assertIn(f"archived {a}", out)
        code, out, _ = self.run_cli("ls", "--all", "--json")
        self.assertEqual(json.loads(out), [])
        code, out, _ = self.run_cli("ls", "--all", "--archived", "--json")
        self.assertTrue(json.loads(out)[0]["archived"])
        code, out, _ = self.run_cli("unarchive", a)
        self.assertIn("unarchived", out)
        r = self.new("r", "--status", "ready")
        code, out, err = self.run_cli("archive", a, r)
        self.assertNotEqual(code, 0)
        self.assertIn(r, err)
        code, out, _ = self.run_cli("archive", a)
        self.assertIn(f"archived {a}", out)
        code, out, _ = self.run_cli("unarchive", a)
        code, out, _ = self.run_cli("archive")
        code, out, _ = self.run_cli("archive")
        self.assertIn("nothing to archive", out)


class TestProjectsAndConfig(SkaldTestCase):
    def test_projects_and_cross_project_cli(self):
        beta = self.make_repo("beta")
        code, out, _ = self.run_cli("projects")
        self.assertIn("alpha", out)
        self.assertIn("beta", out)
        dep = self.new("dep", "--status", "ready", cwd=beta)
        a = self.new("needs dep", "--status", "ready", "--blocked-by", f"beta:{dep}")
        code, out, _ = self.run_cli("ls", "--json")
        self.assertEqual(json.loads(out)[0]["unmet"], [f"beta:{dep}"])
        code, out, err = self.run_cli("-p", "beta", "move", dep, "done")
        self.assertEqual(code, 0, err)
        code, out, _ = self.run_cli("ls", "--unblocked", "--json")
        self.assertEqual([s["id"] for s in json.loads(out)], [a])
        code, out, err = self.run_cli("-p", "beta", "block", dep, f"+alpha:{a}")
        self.assertEqual(code, 0, err)
        code, out, _ = self.run_cli("ls", "--all-projects", "--all", "--json")
        self.assertEqual(sorted(s["project"] for s in json.loads(out)), ["alpha", "beta"])
        code, out, _ = self.run_cli("ls", "--all-projects", "--all", cwd=self.tmp)
        self.assertIn(f"alpha:{a}", out)
        self.assertIn(f"beta:{dep}", out)
        code, out, _ = self.run_cli("next", "--all-projects", "--json", cwd=self.tmp)
        self.assertEqual(json.loads(out)["id"], a)
        code, out, _ = self.run_cli("projects", "rm", "beta")
        self.assertIn("forgot", out)
        code, out, err = self.run_cli("-p", "beta", "ls")
        self.assertEqual(code, 1)
        code, _, err = self.run_cli("check")
        self.assertEqual(code, 0)
        self.assertIn("not registered", err)

    def test_projects_checkouts_use_and_claims_elsewhere(self):
        a = self.new("Shared", "--status", "ready")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        wt = self.tmp / "alpha-wt"
        git(self.repo, "worktree", "add", "-q", "-b", "feature", str(wt))
        code, out, _ = self.run_cli("projects")
        self.assertIn("worktree on feature", out)
        self.assertIn(str((wt / ".skald").resolve()), out)
        code, out, _ = self.run_cli("projects", "--json")
        cos = json.loads(out)[0]["checkouts"]
        self.assertEqual([(c["worktree"], c["branch"]) for c in cos], [(True, "feature")])
        # A command in the worktree does not move the project; it says where the primary is.
        code, out, err = self.run_cli("ls", cwd=wt)
        self.assertEqual(code, 0)
        self.assertIn("recorded beside", err)
        self.assertEqual(Registry(self.home).path_of("alpha"), self.skald_dir.resolve())
        # Claim in the worktree without committing: the primary sees it.
        code, out, err = self.run_cli("claim", a, "--as", "worker", cwd=wt)
        self.assertEqual(code, 0, err)
        code, out, _ = self.run_cli("context", "--as", "claude")
        self.assertIn("Claimed on other branches or in other checkouts:", out)
        self.assertIn(f"worker on feature (in_progress), uncommitted in {(wt / '.skald').resolve()}", out)
        code, out, err = self.run_cli("next", "--json")
        self.assertEqual((code, out.strip()), (1, ""))
        self.assertIn("worker", err)
        code, out, err = self.run_cli("claim", a, "--as", "claude")
        self.assertIn("worker", err)
        # use: the worktree becomes the primary, then back.
        code, out, _ = self.run_cli("projects", "use", cwd=wt)
        self.assertIn("now points at", out)
        self.assertEqual(Registry(self.home).path_of("alpha"), (wt / ".skald").resolve())
        code, out, _ = self.run_cli("-p", "alpha", "show", a, "--json", cwd=self.tmp)
        self.assertEqual(json.loads(out)["assignee"], "worker")
        code, out, _ = self.run_cli("projects", "use", str(self.repo))
        self.assertEqual(Registry(self.home).path_of("alpha"), self.skald_dir.resolve())
        code, out, _ = self.run_cli("projects", "use", str(self.tmp / "nowhere"))
        self.assertEqual(code, 1)
        # The primary goes away: the listing promotes the worktree and -p works from anywhere.
        code, out, _ = self.run_cli("projects", "use", cwd=wt)  # worktree is primary; the main checkout is recorded
        code, out, _ = self.run_cli("projects", "use", str(self.repo))
        import shutil
        shutil.rmtree(self.repo / ".skald")
        code, out, err = self.run_cli("projects", cwd=self.tmp)
        self.assertIn("moved from", err)
        self.assertIn("gone", err)
        self.assertEqual(Registry(self.home).path_of("alpha"), (wt / ".skald").resolve())
        code, out, err = self.run_cli("-p", "alpha", "show", a, "--json", cwd=self.tmp)
        self.assertEqual(code, 0, err)

    def test_config_command(self):
        code, out, _ = self.run_cli("config")
        self.assertIn('port = 8321', out)
        code, out, _ = self.run_cli("config", "author", "Jon")
        self.assertEqual(out.strip(), 'author = "Jon"')
        code, out, _ = self.run_cli("config", "author")
        self.assertEqual(out.strip(), '"Jon"')
        code, out, _ = self.run_cli("config", "author", "--unset")
        code, out, _ = self.run_cli("config", "author")
        self.assertEqual(out.strip(), '""')
        code, _, err = self.run_cli("config", "colour", "red")
        self.assertEqual(code, 1)


class TestGitCommands(SkaldTestCase):
    def test_status_check_hook_commit_log_changelog(self):
        code, out, _ = self.run_cli("status")
        self.assertIn("project:  alpha", out)
        self.assertIn("branch:   ", out)
        self.assertIn("uncommitted story changes: 1 file(s)", out)  # config.json; the empty stories dir is invisible to git
        a = self.new("a", "--status", "ready")
        code, out, _ = self.run_cli("check", "--hook")
        self.assertEqual(code, 2)
        self.assertIn("uncommitted story file(s)", out)
        code, out, _ = self.run_cli("check")
        self.assertEqual((code, out.strip()), (0, "ok"))

        code, out, err = self.run_cli("commit")
        self.assertEqual(code, 0, err)
        self.assertIn("committed", out)
        self.assertIn("skald: update", git(self.repo, "log", "-1", "--format=%s"))
        code, out, _ = self.run_cli("commit")
        self.assertIn("nothing to commit", out)
        code, out, _ = self.run_cli("check", "--hook")
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli("status", "--json")
        info = json.loads(out)
        self.assertEqual((info["uncommitted"], info["ready_unblocked"]), ([], 1))

        code, out, _ = self.run_cli("log", a)
        self.assertIn("skald: update", out)
        code, out, _ = self.run_cli("log", a, "--json")
        self.assertEqual(len(json.loads(out)), 1)

        first = git(self.repo, "rev-parse", "HEAD").strip()
        self.run_cli("move", a, "done")
        b = self.new("b", "--status", "done")
        c = self.new("c")
        self.run_cli("commit", "-m", "finish a and b")
        code, out, _ = self.run_cli("changelog", "--since", first)
        self.assertIn(f"- a ({a})", out)
        self.assertIn(f"- b ({b})", out)
        self.assertNotIn(c, out)
        self.run_cli("archive")
        self.run_cli("commit", "-m", "archive")
        code, out, _ = self.run_cli("changelog", "--since", first, "--json")
        self.assertEqual(sorted(d["id"] for d in json.loads(out)), sorted([a, b]))
        code, out, _ = self.run_cli("changelog", "--since", "HEAD", "--until", "HEAD")
        self.assertIn("(nothing)", out)
        code, _, err = self.run_cli("changelog", "--since", "nope")
        self.assertEqual(code, 1)
        self.assertIn("unknown git ref", err)

    def test_commit_only_touches_skald(self):
        (self.repo / "code.py").write_text("print(1)\n")
        self.new("a")
        code, out, err = self.run_cli("commit", "-m", "stories only")
        self.assertEqual(code, 0, err)
        status = git(self.repo, "status", "--porcelain")
        self.assertIn("code.py", status)
        self.assertNotIn(".skald", status)

    def test_hooks_print_and_install(self):
        code, out, _ = self.run_cli("hooks", "claude")
        snippet = json.loads(out)
        self.assertEqual(snippet["hooks"]["Stop"][0]["hooks"][0]["command"], "skald check")
        settings = self.repo / ".claude" / "settings.json"
        settings.parent.mkdir()
        settings.write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]}, "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo bye"}]}]}}))
        code, out, _ = self.run_cli("hooks", "claude", "--install", "--strict")
        data = json.loads(settings.read_text())
        self.assertEqual(data["permissions"], {"allow": ["Bash(ls)"]})
        stop_cmds = [h["command"] for e in data["hooks"]["Stop"] for h in e["hooks"]]
        self.assertEqual(stop_cmds, ["echo bye", "skald check --hook"])
        self.assertEqual(len(data["hooks"]["SessionStart"]), 1)
        self.assertEqual(data["hooks"]["SessionStart"][0]["hooks"][0]["command"], "skald context")
        code, out, _ = self.run_cli("hooks", "claude", "--as", "claude")
        self.assertEqual(json.loads(out)["hooks"]["SessionStart"][0]["hooks"][0]["command"], "skald context --as claude")
        self.run_cli("hooks", "claude", "--install")
        data = json.loads(settings.read_text())
        stop_cmds = [h["command"] for e in data["hooks"]["Stop"] for h in e["hooks"]]
        self.assertEqual(stop_cmds, ["echo bye", "skald check"])


class TestCustomColumnsCLI(SkaldTestCase):
    def test_mv_into_custom_columns(self):
        ProjectConfig.from_dict({"name": "alpha", "columns": SAMPLE_CONFIG_COLUMNS}).save(self.skald_dir / "config.json")
        a = self.new("a")
        code, out, err = self.run_cli("move", a, "qa")
        self.assertEqual(code, 0, err)
        code, out, err = self.run_cli("move", a, "review")
        self.assertEqual(code, 1)
        self.assertIn("columns: backlog, ready, doing, qa, done, wont_do", err)
        code, out, err = self.run_cli("move", a, "wont_do")
        code, out, _ = self.run_cli("ls", "--json")
        self.assertEqual(json.loads(out), [])
        code, out, _ = self.run_cli("status")
        self.assertIn("wont_do=1", out)


class TestBranchCommands(SkaldTestCase):
    def setUp(self):
        super().setUp()
        self.a = self.new("on both", "--status", "ready")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "checkout", "-qb", "feature")
        self.b = self.new("only on feature")
        self.run_cli("move", self.a, "done")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "feature work")
        git(self.repo, "checkout", "-q", "master")

    def test_branches_ls_and_show(self):
        code, out, _ = self.run_cli("branches")
        self.assertEqual(code, 0)
        self.assertIn("*  master", out)
        self.assertRegex(out, r"feature\s+2\s+1\s+0\s+1")
        code, out, _ = self.run_cli("branches", "--json")
        data = {d["name"]: d for d in json.loads(out)}
        self.assertEqual((data["feature"]["only_there"], data["feature"]["differ"]), ([self.b], [self.a]))
        self.assertTrue(data["master"]["current"])

        code, out, _ = self.run_cli("ls", "--branch", "feature", "--all", "--json")
        self.assertEqual({s["id"]: s["status"] for s in json.loads(out)}, {self.a: "done", self.b: "backlog"})
        code, out, _ = self.run_cli("ls", "--all-branches")
        self.assertIn(f"feature  {self.b}  backlog  -", out)
        self.assertIn(f"feature  {self.a}  done     ready", out)
        code, out, _ = self.run_cli("ls", "--all-branches", "--json")
        self.assertEqual({d["id"]: d["here"] for d in json.loads(out)}, {self.b: None, self.a: "ready"})

        code, out, _ = self.run_cli("show", self.b, "--branch", "feature")
        self.assertIn('title: "only on feature"', out)
        code, _, err = self.run_cli("show", self.b)
        self.assertEqual(code, 1)
        code, _, err = self.run_cli("ls", "--branch", "nope")
        self.assertEqual(code, 1)
        self.assertIn("unknown git ref", err)
        self.assertEqual(git(self.repo, "status", "--porcelain").strip(), "")


class TestFacetCommands(SkaldTestCase):
    def test_facets_epics_and_cross_project(self):
        code, out, _ = self.run_cli("facets")
        self.assertIn("no facet tags", out)
        a = self.new("a", "--tags", "epic:auth,area:web", "--status", "ready")
        self.new("b", "--tags", "epic:auth", "--status", "done")
        code, out, _ = self.run_cli("facets")
        self.assertRegex(out, r"epic\s+auth\s+2\s+1\s+1\s+50%")
        self.assertIn("area  web", out)
        code, out, _ = self.run_cli("epics")
        self.assertNotIn("area", out)
        code, out, _ = self.run_cli("facets", "area", "--json")
        self.assertEqual(json.loads(out)["area"]["web"]["ids"], [a])
        beta = self.make_repo("beta")
        self.new("c", "--tags", "epic:auth", cwd=beta)
        code, out, _ = self.run_cli("epics", "--all-projects", "--json", cwd=self.tmp)
        auth = json.loads(out)["epic"]["auth"]
        self.assertEqual(auth["total"], 3)
        self.assertTrue(all(":" in i for i in auth["ids"]))
        code, out, _ = self.run_cli("ls", "--all-projects", "--tag", "epic:auth", "--all", "--json", cwd=self.tmp)
        self.assertEqual(len(json.loads(out)), 3)


class TestAgentOrientation(SkaldTestCase):
    def test_context_resume_and_note_kinds(self):
        a = self.new("Ship login", "--status", "ready", "--body", "Build it.\n\n## Acceptance\n\n- [ ] renders\n- [x] styled")
        b = self.new("Blocked one", "--status", "ready", "--blocked-by", a)
        code, out, _ = self.run_cli("context", "--as", "claude")
        self.assertIn("Nothing assigned to claude", out)
        self.assertIn(f"Next: {a}", out)
        self.assertIn(f"{b}  Blocked one  waiting on {a}", out)
        self.run_cli("claim", a, "--as", "claude")
        code, out, err = self.run_cli("note", a, "Use shared Button", "--as", "claude", "--kind", "decision")
        self.assertIn("(decision)", out)
        self.run_cli("note", a, "Done: scaffold. Next: submit handler.", "--as", "claude", "--kind", "handoff")
        code, out, _ = self.run_cli("context", "--as", "claude")
        self.assertIn(f"{a}  in_progress  Ship login  checklist 1/2  acceptance 1/2", out)
        self.assertIn("last note: ", out)
        self.assertIn("(handoff) Done: scaffold", out)
        self.assertIn(f"run: skald resume {a}", out)
        self.assertIn("Uncommitted story files", out)
        code, out, _ = self.run_cli("context", "--as", "claude", "--json")
        ctx = json.loads(out)
        self.assertEqual(ctx["mine"][0]["id"], a)
        self.assertTrue(ctx["mine"][0]["has_handoff"])
        self.assertNotIn("deps", ctx["mine"][0])

        code, out, _ = self.run_cli("resume", a)
        self.assertIn("status in_progress · assignee claude · checklist 1/2 · acceptance 1/2", out)
        self.assertIn("Build it.", out)
        self.assertIn("Decisions:", out)
        self.assertIn("Use shared Button", out)
        self.assertIn("Latest handoff", out)
        self.assertIn("Next: submit handler.", out)
        code, out, _ = self.run_cli("resume", a, "--json")
        d = json.loads(out)
        self.assertEqual((d["latest"]["kind"], d["note_count"], len(d["decisions"])), ("handoff", 2, 1))

        code, out, err = self.run_cli("move", a, "review")
        self.assertIn("acceptance criteria unchecked", err)
        code, _, err = self.run_cli("note", a, "x", "--kind", "Bad Kind")
        self.assertEqual(code, 1)

    def test_ls_and_next_compact(self):
        a = self.new("a", "--status", "ready")
        code, out, _ = self.run_cli("ls", "--json", "--compact")
        d = json.loads(out)[0]
        self.assertNotIn("filename", d)
        self.assertNotIn("deps", d)
        self.assertIn("unmet", d)
        code, out, _ = self.run_cli("next", "--json", "--compact")
        self.assertNotIn("filename", json.loads(out))


class TestGitLinkage(SkaldTestCase):
    def test_commit_trailers_and_commits_command(self):
        a = self.new("a")
        b = self.new("b")
        code, out, err = self.run_cli("commit", "-m", "two stories")
        self.assertEqual(code, 0, err)
        msg = git(self.repo, "log", "-1", "--format=%B")
        self.assertIn(f"Skald-Story: {a}", msg)
        self.assertIn(f"Skald-Story: {b}", msg)
        self.assertTrue(msg.startswith("two stories\n\n"))
        code, out, _ = self.run_cli("commits", a)
        self.assertIn("two stories", out)
        git(self.repo, "commit", "-q", "--allow-empty", "-m", f"feat: thing [{a}]")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "unrelated")
        code, out, _ = self.run_cli("commits", a, "--json")
        self.assertEqual([c["subject"] for c in json.loads(out)], [f"feat: thing [{a}]", "two stories"])
        code, out, _ = self.run_cli("commits", b)
        self.assertNotIn("feat: thing", out)
        self.run_cli("move", a, "ready")
        code, out, _ = self.run_cli("commit", "-m", "move", "--no-trailers")
        self.assertNotIn("Skald-Story", git(self.repo, "log", "-1", "--format=%B"))
        c = self.new("c")
        code, out, _ = self.run_cli("commits", c)
        self.assertIn("no commits reference", out)

    def test_diff_and_activity(self):
        a = self.new("first", "--status", "ready")
        self.run_cli("commit", "-m", "base")
        base = git(self.repo, "rev-parse", "HEAD").strip()
        self.run_cli("claim", a, "--as", "claude")
        self.run_cli("note", a, "progress", "--as", "claude")
        b = self.new("second", "--tags", "x")
        code, out, _ = self.run_cli("diff", "--since", base)
        self.assertIn(f"+ {b}  backlog      second", out)
        self.assertIn(f"~ {a}  first: status ready -> in_progress; assignee - -> claude; +1 note(s)", out)
        code, out, _ = self.run_cli("diff", "--since", base, "--json")
        d = json.loads(out)
        self.assertEqual([s["id"] for s in d["added"]], [b])
        self.assertEqual(d["changed"][0]["fields"]["status"], ["ready", "in_progress"])
        self.run_cli("commit", "-m", "work")
        self.run_cli("rm", b)
        self.run_cli("commit", "-m", "remove")
        code, out, _ = self.run_cli("diff", "--since", base, "--until", "HEAD", "--markdown")
        self.assertTrue(out.startswith("<!-- skald-diff -->"))
        self.assertIn("**Changed**", out)
        self.assertNotIn(b, out)                     # added then removed nets out
        code, out, _ = self.run_cli("diff", "--since", "HEAD", "--until", "HEAD")
        self.assertIn("no story changes", out)

        code, out, _ = self.run_cli("activity", "--since", base)
        self.assertIn(f"{a}  status ready -> in_progress  (first)", out)
        self.assertIn(f"{a}  +1 note(s)  (first)", out)
        self.assertIn(f"{b}  created (backlog)  (second)", out)
        self.assertIn(f"{b}  deleted  (second)", out)
        code, out, _ = self.run_cli("activity", "--json")     # default window covers everything here
        events = json.loads(out)
        self.assertTrue(any(e["event"] == "deleted" for e in events))
        self.assertNotIn("full", events[0])
        code, out, _ = self.run_cli("activity", "--since", "HEAD", "--until", "HEAD")
        self.assertIn("no backlog activity", out)
