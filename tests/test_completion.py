"""Shell completion candidates and the scripts that ask for them."""
import json

from skald.completion import SCRIPTS, complete

from .helpers import SAMPLE_CONFIG_COLUMNS, SkaldTestCase, git, prefix


class TestCompletion(SkaldTestCase):
    def setUp(self):
        super().setUp()
        cfg = json.loads((self.skald_dir / "config.json").read_text())
        cfg["columns"] = SAMPLE_CONFIG_COLUMNS
        (self.skald_dir / "config.json").write_text(json.dumps(cfg))
        self.a = self.new("Add login", "--tags", "auth,epic:accounts")
        self.b = self.new("Fix logout", "--tags", "auth", "--status", "done")
        self.c = self.new("Write docs")
        self.run_cli("block", self.c, f"+{self.a}")
        (self.skald_dir / "templates").mkdir()
        (self.skald_dir / "templates" / "bug.md").write_text("## Requirements\n")
        self.make_repo("beta")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-q", "-m", "init")
        git(self.repo, "branch", "feature")

    def values(self, *words, cword=None):
        words = list(words)
        if cword is None:
            cword = len(words) - 1
        return [v for v, _ in complete(self.workspace(), words, cword)]

    def cands(self, *words):
        return dict(complete(self.workspace(), list(words), len(words) - 1))

    def test_commands_and_global_options(self):
        names = self.values("")
        self.assertIn("move", names)
        self.assertIn("completion", names)
        self.assertNotIn("mv", names)
        self.assertNotIn("_complete", names)
        self.assertEqual(self.values("mo"), ["move"])
        self.assertIn("--project", self.values("--"))
        self.assertEqual(self.values("-p", ""), ["alpha", "beta"])
        self.assertEqual(self.values("-p", "beta", "mov"), ["move"])

    def test_ids_with_titles_and_status(self):
        c = self.cands("move", "")
        self.assertEqual(set(c), {self.a, self.b, self.c})
        self.assertEqual(c[self.a], "Add login  (backlog)")
        self.assertEqual(self.values("show", self.a[:2]), [self.a])
        self.assertEqual(self.values("mv", ""), self.values("move", ""))
        self.assertEqual(self.values("move", self.a, ""), [c["key"] for c in SAMPLE_CONFIG_COLUMNS])
        self.assertEqual(self.values("move", self.a, "w"), ["wont_do"])
        self.assertEqual(self.values("move", self.a, "done", ""), [])

    def test_flags_values_and_choices(self):
        flags = self.values("ls", "--")
        self.assertIn("--status", flags)
        self.assertIn("--json", flags)
        self.assertEqual(self.values("ls", "--status", "q"), ["qa"])
        self.assertEqual(self.values("new", "x", "--template", ""), ["bug"])
        self.assertEqual(self.values("render", "--format", ""), ["md", "html"])
        self.assertEqual(self.values("note", self.a, "hi", "--kind", "h"), ["handoff"])
        self.assertEqual(self.values("new", "x", "--tags", "auth,"), ["auth,epic:accounts"])
        self.assertEqual(self.values("new", "x", "--tags", ""), ["auth", "epic:accounts"])
        self.assertEqual(self.values("new", "x", "--status=r"), ["--status=ready"])
        self.assertIn("agent", self.values("claim", self.a, "--as", ""))
        # a flag already used is not offered again unless it takes a value
        self.assertNotIn("--json", self.values("ls", "--json", "--"))

    def test_tag_block_set_and_archive(self):
        c = self.cands("tag", self.c, "")
        self.assertEqual(set(c), {"+auth", "+epic:accounts"})
        c = self.cands("tag", self.a, "")
        self.assertEqual(set(c), {"-auth", "-epic:accounts"})
        c = self.cands("block", self.c, "")
        self.assertEqual(set(c), {f"+{self.b}", f"-{self.a}"})
        self.assertEqual(self.values("set", self.a, ""), ["title=", "rank=", "assignee="])
        self.assertIn("assignee=agent", self.values("set", self.a, "assignee="))
        self.assertEqual(self.values("archive", ""), [self.b])
        self.assertEqual(self.values("archive", self.b, ""), [])
        self.run_cli("archive", self.b)
        self.assertEqual(self.values("unarchive", ""), [self.b])
        self.assertNotIn(self.b, self.values("move", ""))

    def test_refs_facets_config_projects_hooks(self):
        self.assertIn("feature", self.values("show", self.a, "--branch", ""))
        self.assertIn("feature", self.values("diff", "--since", "f"))
        self.assertEqual(self.values("facets", ""), ["epic"])
        self.assertIn("author", self.values("config", ""))
        self.assertEqual(self.values("config", "push", ""), ["true", "false"])
        self.assertEqual(self.values("projects", ""), ["rm", "use"])
        self.assertEqual(self.values("projects", "rm", ""), ["alpha", "beta"])
        self.assertEqual(self.values("hooks", ""), ["claude", "git", "github"])
        self.assertEqual(self.values("completion", "z"), ["zsh"])
        self.assertEqual(self.values("server", ""), ["start", "stop", "status", "token"])

    def test_outside_a_project_degrades(self):
        cwd = self.tmp / "nowhere"
        cwd.mkdir()
        code, out, err = self.run_cli("_complete", "--", "1", "move", "", cwd=cwd)
        self.assertEqual((code, out), (0, ""))
        code, out, err = self.run_cli("_complete", "--", "0", "mo", cwd=cwd)
        self.assertEqual(out.strip(), "move\tmove a story to a column")

    def test_cli_and_scripts(self):
        code, out, _ = self.run_cli("_complete", "--", "1", "move", prefix(self.a, [self.b]))
        self.assertEqual(code, 0)
        self.assertEqual(out.split("\t")[0], self.a)
        code, out, _ = self.run_cli("_complete", "--", "x")
        self.assertEqual(code, 1)
        for shell in ("bash", "zsh", "fish"):
            code, out, _ = self.run_cli("completion", shell)
            self.assertEqual((code, out), (0, SCRIPTS[shell]))
            self.assertIn("skald _complete --", out)
        self.assertIn("complete -o default -F _skald skald", SCRIPTS["bash"])
        self.assertIn("_git_skald", SCRIPTS["bash"])
        self.assertIn("compdef _skald skald", SCRIPTS["zsh"])
        self.assertIn("_git-skald", SCRIPTS["zsh"])
        self.assertIn("complete -c skald", SCRIPTS["fish"])
        self.assertIn("__fish_seen_subcommand_from skald", SCRIPTS["fish"])
        code, out, _ = self.run_cli("--help")
        self.assertIn("completion", out)
        self.assertNotIn("_complete", out)
