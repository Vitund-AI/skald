"""skald render, staleness detection, commit integration, and hook installers."""
import json
import os
import stat

from skald import cli
from skald import render as rnd
from skald.config import ProjectConfig

from .helpers import SAMPLE_CONFIG_COLUMNS, SkaldTestCase, git


class TestRender(SkaldTestCase):
    def seed(self):
        a = self.new("Login form", "--tags", "epic:auth,area:web", "--status", "ready", "--body", "- [x] one\n- [ ] two")
        b = self.new("Session store", "--tags", "epic:auth", "--status", "done")
        c = self.new("Pipe | in title", "--blocked-by", a)
        return a, b, c

    def test_markdown_content_and_determinism(self):
        a, b, c = self.seed()
        code, out, err = self.run_cli("render", "--stdout")
        self.assertEqual(code, 0, err)
        self.assertRegex(out.splitlines()[0], r"^<!-- skald-render [0-9a-f]{16} -->$")
        self.assertIn("# alpha backlog", out)
        self.assertIn("**2 open**", out)
        self.assertIn("| `epic:auth` | ▰▰▰▰▰▱▱▱▱▱ 50% | 1 | 1 |", out)
        self.assertIn(f"[{a}](stories/{a}-login-form.md)", out)      # relative to .skald/README.md
        self.assertIn("| 1/2 |", out)
        self.assertIn(f"🔒 `{a}`", out)
        self.assertIn("Pipe \\| in title", out)
        self.assertIn("<details><summary><strong>Done (1)</strong></summary>", out)
        code, again, _ = self.run_cli("render", "--stdout")
        self.assertEqual(out, again)

    def test_write_default_path_enable_and_stale_check(self):
        self.seed()
        code, out, _ = self.run_cli("render")
        self.assertEqual(out.strip(), "rendered .skald/README.md")
        readme = self.skald_dir / "README.md"
        self.assertTrue(readme.exists())
        code, out, err = self.run_cli("check")
        self.assertEqual(code, 0)
        self.assertNotIn("out of date", err)
        self.new("changes things")
        code, out, err = self.run_cli("check")
        self.assertEqual(code, 0)                      # a warning, not a problem
        self.assertIn("README.md is out of date", err)
        code, out, _ = self.run_cli("render", "--enable")
        self.assertIn("enabled automatic rendering", out)
        cfg = json.loads((self.skald_dir / "config.json").read_text())
        self.assertEqual(cfg["render"], {"path": ".skald/README.md", "format": "md"})
        self.assertEqual(rnd.render_settings(self.store()), {"path": ".skald/README.md", "format": "md", "archived": False})

    def test_html_custom_path_and_links(self):
        a, b, c = self.seed()
        code, out, _ = self.run_cli("render", "--format", "html", "--out", "docs/board.html")
        self.assertEqual(out.strip(), "rendered docs/board.html")
        text = (self.repo / "docs" / "board.html").read_text()
        self.assertIn("<!-- skald-render ", text)
        self.assertIn(f'href="../.skald/stories/{a}-login-form.md"', text)
        self.assertIn("Pipe | in title", text)
        self.assertIn('class="card blocked"', text)
        self.assertNotIn("<script", text)

    def test_archived_and_unknown_status_sections(self):
        ProjectConfig.from_dict({"name": "alpha", "columns": SAMPLE_CONFIG_COLUMNS}).save(self.skald_dir / "config.json")
        a = self.new("gone", "--status", "done")
        self.run_cli("archive")
        self.write_raw("bbbbbb-odd.md", '---\ntitle: "odd"\nstatus: "testing"\n---\n')
        code, out, _ = self.run_cli("render", "--stdout")
        self.assertIn("## Unknown status", out)
        self.assertNotIn("Archived", out)
        code, out, _ = self.run_cli("render", "--stdout", "--archived")
        self.assertIn("<details><summary><strong>Archived (1)</strong></summary>", out)
        self.assertIn("Won't do (0)", out)

    def test_commit_rerenders_when_enabled(self):
        self.seed()
        self.run_cli("render", "--enable")
        self.run_cli("commit", "-m", "first")
        self.new("later story")
        code, out, err = self.run_cli("commit", "-m", "second")
        self.assertEqual(code, 0, err)
        self.assertEqual(git(self.repo, "status", "--porcelain").strip(), "")
        readme = (self.skald_dir / "README.md").read_text()
        self.assertIn("later story", readme)
        code, out, err = self.run_cli("check")
        self.assertNotIn("out of date", err)

    def test_commit_includes_render_outside_skald(self):
        self.seed()
        self.run_cli("render", "--enable", "--out", "BACKLOG.md")
        code, out, err = self.run_cli("commit", "-m", "with root file")
        self.assertEqual(code, 0, err)
        self.assertIn("BACKLOG.md", git(self.repo, "show", "--stat", "--format=", "HEAD"))
        self.assertEqual(git(self.repo, "status", "--porcelain").strip(), "")

    def test_stage_flag(self):
        self.seed()
        code, out, _ = self.run_cli("render", "--stage")
        self.assertIn("staged .skald/README.md", out)
        self.assertIn("A  .skald/README.md", git(self.repo, "status", "--porcelain"))


class TestHookInstallers(SkaldTestCase):
    def test_git_hook_install_and_refuse_to_clobber(self):
        code, out, err = self.run_cli("hooks", "git")
        self.assertIn("skald render --stage", out)
        self.assertIn("pre-commit", err)
        code, out, _ = self.run_cli("hooks", "git", "--install")
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        self.assertTrue(hook.exists())
        if os.name != "nt":
            self.assertTrue(hook.stat().st_mode & stat.S_IXUSR)
        self.assertIn("skald check || exit 1", hook.read_text())
        self.assertIn("enabled automatic rendering", out)
        self.assertEqual(json.loads((self.skald_dir / "config.json").read_text())["render"]["path"], ".skald/README.md")
        code, out, _ = self.run_cli("hooks", "git", "--install")   # ours: overwritten quietly
        self.assertEqual(code, 0)
        hook.write_text("#!/bin/sh\necho custom\n")
        code, out, err = self.run_cli("hooks", "git", "--install")
        self.assertEqual(code, 1)
        self.assertIn("not Skald's", err)
        self.assertEqual(hook.read_text(), "#!/bin/sh\necho custom\n")

    def test_github_workflow_install(self):
        code, out, err = self.run_cli("hooks", "github")
        self.assertIn("name: skald", out)
        self.assertIn("branches: [master]", out)
        code, out, _ = self.run_cli("hooks", "github", "--install")
        wf = self.repo / ".github" / "workflows" / "skald.yml"
        self.assertTrue(wf.exists())
        text = wf.read_text()
        self.assertIn("pip install skald-kanban", text)
        self.assertNotIn("git+https://", text)
        self.assertIn("skald check", text)
        self.assertIn("skald render --out .skald/README.md", text)
        self.assertIn("[skip ci]", text)
        self.assertIn("skald diff --since \"origin/${{ github.base_ref }}\" --until HEAD --markdown", text)
        self.assertIn("pull-requests: write", text)
        self.assertIn("contents: read", text)
        # The render commit must be attributed to the Actions bot: a bare
        # USERNAME@users.noreply.github.com address credits whoever owns that
        # GitHub username.
        self.assertIn('git config user.name "github-actions[bot]"', text)
        self.assertIn("41898282+github-actions[bot]@users.noreply.github.com", text)
        self.assertNotIn("skald@users.noreply.github.com", text)
        code, out, err = self.run_cli("hooks", "github", "--install")
        self.assertEqual(code, 1)
        self.assertIn("not overwriting", err)
