"""Store behaviour: ranks, dependencies, cross-project refs, columns, archive, registry."""
import json
import os
import shutil
from pathlib import Path

from skald.config import ProjectConfig
from skald.errors import ConfigError, ConflictError, NotFoundError, SkaldError
from skald.registry import Registry, UserConfig, Workspace, config_home, find_skald_dir

from .helpers import SAMPLE_CONFIG_COLUMNS, SkaldTestCase, git


class TestStoreBasics(SkaldTestCase):
    def test_create_writes_canonical_file(self):
        s = self.store()
        story, warnings = s.create("Hello World", tags=["B", "a"], body="Do it")
        self.assertEqual(warnings, [])
        self.assertRegex(story.path.name, r"^[0-9a-f]{6}-hello-world\.md$")
        raw = story.path.read_text()
        self.assertTrue(raw.startswith('---\ntitle: "Hello World"\nstatus: "backlog"\nrank: 10\ntags: ["a", "b"]\nblocked_by: []\n'))
        self.assertTrue(raw.endswith("---\n## Requirements\n\nDo it\n"))
        self.assertNotIn("assignee", raw)

    def test_ids_unique_and_prefix_lookup(self):
        s = self.store()
        ids = {s.create(f"s{i}")[0].id for i in range(30)}
        self.assertEqual(len(ids), 30)
        some = sorted(ids)[0]
        self.assertEqual(s.get(some[:6]).id, some)
        with self.assertRaises(NotFoundError):
            s.resolve("zzz")
        with self.assertRaises(SkaldError):
            s.resolve("")
        with self.assertRaises(SkaldError):
            s.resolve("other:abc123")

    def test_ambiguous_prefix(self):
        self.write_raw("abc111-one.md", '---\ntitle: "one"\nstatus: "backlog"\n---\n')
        self.write_raw("abc222-two.md", '---\ntitle: "two"\nstatus: "backlog"\n---\n')
        s = self.store()
        with self.assertRaises(SkaldError) as cm:
            s.resolve("abc")
        self.assertIn("ambiguous", str(cm.exception))
        self.assertEqual(s.resolve("abc1"), "abc111")

    def test_ranks_on_create_move_and_reorder(self):
        s = self.store()
        a, _ = s.create("a")
        b, _ = s.create("b")
        c, _ = s.create("c", status="ready")
        self.assertEqual([a.rank, b.rank, c.rank], [10, 20, 10])
        a2, _ = s.update(a.id, status="ready")
        self.assertEqual(a2.rank, 20)
        a3, _ = s.update(a.id, title="renamed")
        self.assertEqual((a3.rank, a3.title), (20, "renamed"))
        s.reorder("ready", [a.id, c.id])
        idx = s.index()
        self.assertEqual((idx[a.id].rank, idx[c.id].rank), (10, 20))
        d, _ = s.create("d", status="ready")
        s.reorder("ready", [d.id])
        idx = s.index()
        self.assertEqual([idx[d.id].rank, idx[a.id].rank, idx[c.id].rank], [10, 20, 30])
        with self.assertRaises(SkaldError):
            s.reorder("backlog", [a.id])
        with self.assertRaises(SkaldError):
            s.reorder("nope", [])

    def test_move_and_order_in_one_update(self):
        s = self.store()
        a, _ = s.create("a", status="ready")
        b, _ = s.create("b", status="ready")
        c, _ = s.create("c")
        c2, warnings = s.update(c.id, status="ready", order=[a.id, c.id, b.id])
        self.assertEqual(warnings, [])
        idx = s.index()
        self.assertEqual([idx[a.id].rank, idx[c.id].rank, idx[b.id].rank], [10, 20, 30])
        self.assertEqual((c2.status, c2.rank), ("ready", 20))

    def test_update_validation(self):
        s = self.store()
        a, _ = s.create("a")
        for kwargs in ({"status": "nope"}, {"title": "  "}, {"rank": "5"}, {"tags": "a,b"}, {"assignee": 3}):
            with self.subTest(str(kwargs)):
                with self.assertRaises(SkaldError):
                    s.update(a.id, **kwargs)
        with self.assertRaises(SkaldError):
            s.create("x", status="nope")

    def test_notes_and_body(self):
        s = self.store()
        a, _ = s.create("a")
        s.append_note(a.id, "first\nline two", author="agent")
        s.append_note(a.id, "  second  ", author="Jon Baker")
        body = s.get(a.id).body
        self.assertRegex(body, r"^## Requirements\n\n## \[agent\] \d{4}-\d\d-\d\d \d\d:\d\d UTC\nfirst\nline two\n\n## \[Jon Baker\] .*\nsecond\n$")
        with self.assertRaises(SkaldError):
            s.append_note(a.id, "   ")
        with self.assertRaises(SkaldError):
            s.append_note(a.id, "x", author="a]b")
        sha = s.body_sha(s.get(a.id))
        s.write_body(a.id, "new body\n", sha)
        with self.assertRaises(ConflictError):
            s.write_body(a.id, "other\n", sha)
        s.write_body(a.id, "forced\n", None)
        self.assertEqual(s.get(a.id).body, "forced\n")

    def test_checklist_in_story_dict(self):
        s = self.store()
        a, _ = s.create("a", body="- [x] one\n- [ ] two\n")
        self.assertEqual(s.story_dict(a)["checklist"], {"done": 1, "total": 2})

    def test_delete_and_dependents(self):
        s = self.store()
        a, _ = s.create("a")
        b, _ = s.create("b", blocked_by=[a.id])
        with self.assertRaises(ConflictError):
            s.delete(a.id)
        # --force clears the references it would otherwise orphan, and says so.
        kid, _ = s.create("kid", parent=a.id)
        notes = []
        s.delete(a.id, force=True, notes=notes)
        self.assertFalse(a.path.exists())
        self.assertEqual(sorted(notes), sorted([f"removed {a.id} from blocked_by of {b.id}", f"cleared parent of {kid.id}"]))
        self.assertEqual(s.get(b.id).blocked_by, [])
        self.assertEqual(s.get(kid.id).parent, "")
        self.assertEqual(s.check(), ([], []))
        s.delete(b.id)
        self.assertEqual(s.check(), ([], []))

    def test_new_does_not_duplicate_the_requirements_heading(self):
        s = self.store()
        a, _ = s.create("a", body="## Requirements\n\nDo the thing.\n")
        self.assertEqual(a.body.count("## Requirements"), 1)
        b, _ = s.create("b", body="Do the thing.\n")
        self.assertTrue(b.body.startswith("## Requirements\n\nDo the thing."))

    def test_archive_selected_ids(self):
        s = self.store()
        a, _ = s.create("a", status="done")
        b, _ = s.create("b", status="done")
        c, _ = s.create("c", status="ready")
        with self.assertRaises(SkaldError):
            s.archive(ids=[a.id, c.id])
        self.assertTrue(a.path.exists())
        with self.assertRaises(NotFoundError):
            s.archive(ids=["zzzzzz"])
        self.assertEqual([x.id for x in s.archive(ids=[b.id[:3], b.id])], [b.id])
        self.assertEqual(sorted(x.id for x in s.load_all()[0]), sorted([a.id, c.id]))

    def test_load_all_skips_corrupt_and_check_reports(self):
        s = self.store()
        s.create("good")
        self.write_raw("bad000-broken.md", "no fence\n")
        self.write_raw("aaaaaa-x.md", '---\ntitle: "x"\n<<<<<<< HEAD\nstatus: "ready"\n=======\nstatus: "done"\n>>>>>>> other\n---\n')
        self.write_raw("Notes.md", "hello")
        stories, warnings = s.load_all()
        self.assertEqual(len(stories), 1)
        self.assertEqual(len(warnings), 3)
        problems, _ = s.check()
        self.assertTrue(any("conflict markers" in p for p in problems))
        self.assertTrue(any("Notes.md" in p for p in problems))
        self.assertTrue(any("bad000" in p for p in problems))

    def test_write_preserves_unknown_fields(self):
        from .test_format import SAMPLE

        self.write_raw("abcdef-sample.md", SAMPLE.replace('"other:c4d811"', '"7b21e0"'))
        self.write_raw("7b21e0-dep.md", '---\ntitle: "dep"\nstatus: "done"\n---\n')
        s = self.store()
        s.update("abcdef", status="in_progress")
        raw = (s.stories_dir / "abcdef-sample.md").read_text()
        self.assertIn('status: "in_progress"', raw)
        self.assertIn("estimate: 3\n", raw)
        self.assertIn('assignee: "claude"\n', raw)
        self.assertTrue(raw.endswith("this line looks like a fence but is body\n"))


class TestDependencies(SkaldTestCase):
    def test_unmet_missing_and_warnings(self):
        s = self.store()
        a, _ = s.create("a", status="done")
        b, _ = s.create("b", status="ready")
        c, warnings = s.create("c", status="ready", blocked_by=[a.id, b.id])
        self.assertEqual(s.unmet(c), [b.id])
        self.assertEqual(len(warnings), 1)
        self.assertIn(f"{b.id} (ready)", warnings[0])
        self.write_raw("ffffff-ghost.md", '---\ntitle: "g"\nstatus: "ready"\nblocked_by: ["000000"]\n---\n')
        ghost = s.get("ffffff")
        self.assertEqual(s.unmet(ghost), ["000000"])
        self.assertIn("000000 (missing)", s.unmet_warning(ghost))
        with self.assertRaises(NotFoundError):
            s.create("x", blocked_by=["123456"])

    def test_warns_on_ready_active_done_only_when_changed(self):
        s = self.store()
        a, _ = s.create("a")
        b, _ = s.create("b", blocked_by=[a.id])
        for status in ("ready", "in_progress", "review", "done"):
            _, warnings = s.update(b.id, status=status)
            self.assertEqual(len(warnings), 1, status)
        _, warnings = s.update(b.id, status="backlog")
        self.assertEqual(warnings, [])
        s.update(a.id, status="done")
        _, warnings = s.update(b.id, status="in_progress")
        self.assertEqual(warnings, [])
        _, warnings = s.update(b.id, status="in_progress", title="x")
        self.assertEqual(warnings, [])

    def test_self_and_cycle(self):
        s = self.store()
        a, _ = s.create("a")
        b, _ = s.create("b", blocked_by=[a.id])
        with self.assertRaises(SkaldError):
            s.update(a.id, blocked_by=[a.id])
        _, warnings = s.update(a.id, blocked_by=[b.id])
        self.assertTrue(any("cycle" in w for w in warnings))
        problems, _ = s.check()
        self.assertEqual(len([p for p in problems if "cycle" in p]), 1)

    def test_next_and_claim(self):
        s = self.store()
        a, _ = s.create("a", status="ready")
        b, _ = s.create("b", status="ready", assignee="bob")
        c, _ = s.create("c", status="ready", blocked_by=[a.id])
        self.assertEqual(s.next_story().id, a.id)
        s.update(a.id, status="done")
        self.assertEqual(s.next_story().id, c.id)          # b is bob's; c is unblocked and unassigned
        self.assertEqual(s.next_story(for_author="bob").id, b.id)
        self.assertEqual(s.next_story(for_author="alice").id, c.id)
        claimed, warnings = s.claim(c.id, "alice")
        self.assertEqual((claimed.assignee, claimed.status), ("alice", "in_progress"))
        again, _ = s.claim(c.id, "carol")
        self.assertEqual((again.assignee, again.status), ("carol", "in_progress"))
        with self.assertRaises(SkaldError):
            s.claim(c.id, " ")


class TestCrossProject(SkaldTestCase):
    def setUp(self):
        super().setUp()
        self.beta = self.make_repo("beta")

    def test_reference_states(self):
        ws = self.workspace()
        alpha, beta = ws.open("alpha"), ws.open("beta")
        dep, _ = beta.create("beta dep", status="ready")
        story, warnings = alpha.create("needs beta", status="ready", blocked_by=[f"beta:{dep.id}"])
        self.assertEqual(story.blocked_by, [f"beta:{dep.id}"])
        self.assertIn(f"beta:{dep.id} (ready)", warnings[0])
        beta.update(dep.id, status="done")
        self.assertEqual(alpha.unmet(story), [])
        beta.archive()
        states = alpha.dep_states(alpha.get(story.id))
        self.assertEqual((states[0].state, states[0].satisfied), ("archived", True))
        with self.assertRaises(NotFoundError):
            alpha.create("bad", blocked_by=["beta:000000"])
        with self.assertRaises(SkaldError):
            alpha.create("bad", blocked_by=["Beta Project:000000"])

    def test_unregistered_project_is_unavailable_warning(self):
        ws = self.workspace()
        alpha = ws.open("alpha")
        story, warnings = alpha.create("x", status="ready", blocked_by=["gamma:abc123"])
        self.assertEqual(alpha.dep_states(story)[0].state, "unavailable")
        self.assertIn("gamma:abc123 (unavailable)", warnings[0])
        problems, warns = alpha.check()
        self.assertEqual(problems, [])
        self.assertTrue(any("not registered" in w for w in warns))
        Registry(self.home).remove("beta")
        self.assertIsNone(self.workspace().open("beta"))

    def test_dependents_include_qualified_refs(self):
        ws = self.workspace()
        alpha, beta = ws.open("alpha"), ws.open("beta")
        a, _ = alpha.create("a")
        b, _ = alpha.create("b", blocked_by=[f"alpha:{a.id}"])
        self.assertEqual([d.id for d in alpha.dependents(a.id)], [b.id])


class TestColumns(SkaldTestCase):
    def setUp(self):
        super().setUp()
        ProjectConfig.from_dict({"name": "alpha", "columns": SAMPLE_CONFIG_COLUMNS}).save(self.skald_dir / "config.json")

    def test_closed_satisfies_with_warning_and_limits(self):
        s = self.store()
        self.assertEqual(s.config.keys, ["backlog", "ready", "doing", "qa", "done", "wont_do"])
        x, _ = s.create("old idea", status="ready")
        y, _ = s.create("depends", blocked_by=[x.id])
        s.update(x.id, status="wont_do")
        self.assertEqual(s.unmet(s.get(y.id)), [])
        _, warnings = s.update(y.id, status="qa")
        self.assertTrue(any("closed" in w for w in warnings))
        z, _ = s.create("z")
        _, warnings = s.update(z.id, status="doing")
        self.assertEqual(warnings, [])
        w, _ = s.create("w")
        _, warnings = s.update(w.id, status="doing")
        self.assertTrue(any("over its limit (2/1)" in w for w in warnings))
        with self.assertRaises(SkaldError):
            s.update(w.id, status="review")
        self.assertEqual(s.claim(y.id, "me")[0].status, "qa")  # already active: status unchanged

    def test_unknown_status_sorts_last_and_check_reports(self):
        s = self.store()
        a, _ = s.create("a")
        self.write_raw("bbbbbb-x.md", '---\ntitle: "x"\nstatus: "testing"\n---\n')
        stories, _ = s.load_all()
        self.assertEqual([x.id for x in stories][-1], "bbbbbb")
        problems, _ = s.check()
        self.assertTrue(any("not a column" in p for p in problems))


class TestArchive(SkaldTestCase):
    def test_archive_and_unarchive(self):
        s = self.store()
        a, _ = s.create("a", status="done")
        b, _ = s.create("b", status="ready", blocked_by=[a.id])
        self.assertEqual([x.id for x in s.archive(dry_run=True)], [a.id])
        self.assertTrue(a.path.exists())
        moved = s.archive()
        self.assertEqual([x.id for x in moved], [a.id])
        self.assertTrue((s.archive_dir / a.path.name).exists())
        self.assertEqual(s.unmet(s.get(b.id)), [])
        self.assertEqual([x.id for x in s.load_all()[0]], [b.id])
        self.assertEqual(len(s.load_all(include_archived=True)[0]), 2)
        self.assertTrue(s.get(a.id).archived)
        with self.assertRaises(ConflictError):
            s.update(a.id, title="nope")
        with self.assertRaises(ConflictError):
            s.delete(a.id)
        s.unarchive(a.id)
        self.assertFalse(s.get(a.id).archived)
        with self.assertRaises(SkaldError):
            s.unarchive(a.id)


class TestTemplates(SkaldTestCase):
    def test_new_from_template(self):
        s = self.store()
        s.templates_dir.mkdir()
        with open(s.templates_dir / "bug.md", "w", newline="\n") as fh:
            fh.write("## Steps\n\n1.\n\n## Expected\n")
        self.assertEqual(s.templates(), ["bug"])
        story, _ = s.create("crash", template="bug", body="extra")
        self.assertEqual(story.body, "## Steps\n\n1.\n\n## Expected\n\nextra\n")
        with self.assertRaises(NotFoundError):
            s.create("x", template="feature")


class TestRegistry(SkaldTestCase):
    def test_config_home_resolution(self):
        self.assertEqual(config_home(), self.home)
        os.environ.pop("SKALD_HOME")
        os.environ["XDG_CONFIG_HOME"] = str(self.tmp / "xdg")
        try:
            if os.name == "nt":
                # %APPDATA% wins over XDG on Windows by design.
                self.assertTrue(str(config_home()).endswith("skald"))
            else:
                self.assertEqual(config_home(), self.tmp / "xdg" / "skald")
        finally:
            os.environ.pop("XDG_CONFIG_HOME")

    def test_register_move_remove(self):
        r = Registry(self.home)
        self.assertEqual([e["name"] for e in r.entries()], ["alpha"])
        self.assertIsNone(r.register("alpha", self.skald_dir))
        # A second checkout while the primary still exists is recorded beside it, not in its place.
        other = self.make_repo("second", init_skald=False)
        (other / ".skald" / "stories").mkdir(parents=True)
        notice = r.register("alpha", other / ".skald")
        self.assertIn("recorded beside", notice)
        self.assertEqual(Registry(self.home).path_of("alpha"), self.skald_dir.resolve())
        self.assertIsNone(r.register("alpha", other / ".skald"))
        cos = r.checkouts("alpha")
        self.assertEqual([c["primary"] for c in cos], [True, False])
        self.assertEqual(Path(cos[1]["path"]), (other / ".skald").resolve())
        self.assertFalse(cos[1]["worktree"])
        self.assertEqual(len(set(c["id"] for c in cos)), 2)
        self.assertEqual(r.entries()[0]["checkouts"][0]["path"], cos[1]["path"])
        # `use` swaps them.
        r.use("alpha", other / ".skald")
        self.assertEqual(Registry(self.home).path_of("alpha"), (other / ".skald").resolve())
        self.assertEqual(Path(r.checkouts("alpha")[1]["path"]), self.skald_dir.resolve())
        r.use("alpha", self.skald_dir)
        self.assertEqual(r.path_of("alpha"), self.skald_dir.resolve())
        # A checkout whose directory has gone is forgotten on the next listing.
        shutil.rmtree(other)
        self.assertEqual([c["primary"] for c in r.checkouts("alpha")], [True])
        self.assertNotIn("checkouts", Registry(self.home).projects["alpha"])
        # When the primary itself has gone, the next checkout to run a command takes over: a moved repository.
        moved = self.make_repo("moved", init_skald=False)
        (moved / ".skald" / "stories").mkdir(parents=True)
        os.chdir(self.tmp)  # Windows cannot remove the current directory
        shutil.rmtree(self.repo)
        notice = r.register("alpha", moved / ".skald")
        self.assertIn("moved", notice)
        self.assertEqual(Registry(self.home).path_of("alpha"), (moved / ".skald").resolve())
        r.remove("alpha")
        with self.assertRaises(NotFoundError):
            r.remove("alpha")
        self.assertEqual(r.entries(), [])

    def test_missing_primary_promotes_a_surviving_checkout(self):
        r = Registry(self.home)
        other = self.make_repo("second", init_skald=False)
        (other / ".skald" / "stories").mkdir(parents=True)
        ProjectConfig("alpha").save(other / ".skald" / "config.json")
        r.register("alpha", other / ".skald")
        os.chdir(self.tmp)  # Windows cannot remove the current directory
        shutil.rmtree(self.repo)
        # Any listing promotes the survivor and says so; a fresh registry sees the new primary.
        cos = Registry(self.home).checkouts("alpha")
        self.assertEqual([(c["primary"], c["exists"]) for c in cos], [(True, True)])
        self.assertEqual(Path(cos[0]["path"]), (other / ".skald").resolve())
        fresh = Registry(self.home)
        self.assertEqual(fresh.path_of("alpha"), (other / ".skald").resolve())
        self.assertNotIn("checkouts", fresh.projects["alpha"])
        # Opening by name through a registry that still holds the stale path also promotes, with a notice.
        stale = Registry(self.home)
        stale.projects["alpha"]["path"] = str(self.skald_dir)
        stale.projects["alpha"]["checkouts"] = [str((other / ".skald").resolve())]
        ws = Workspace(stale, UserConfig(self.home))
        self.assertEqual(ws.open("alpha").dir, (other / ".skald").resolve())
        self.assertTrue(any("moved from" in n and "gone" in n for n in ws.notices))
        # With no survivor the project stays, listed as missing.
        shutil.rmtree(other)
        entries = Registry(self.home).entries()
        self.assertEqual([(e["name"], e["exists"]) for e in entries], [("alpha", False)])

    def test_worktrees_are_checkouts_and_claims_there_are_seen(self):
        st = self.store()
        st.create("On main", status="ready")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "seed")
        wt = self.tmp / "alpha-wt"
        git(self.repo, "worktree", "add", "-q", "-b", "feature", str(wt))
        r = Registry(self.home)
        cos = r.checkouts("alpha")
        self.assertEqual([(c["primary"], c["worktree"]) for c in cos], [(True, False), (False, True)])
        self.assertEqual(Path(cos[1]["path"]), (wt / ".skald").resolve())
        # An uncommitted claim in the worktree is a claim elsewhere, before any commit.
        ws = self.workspace()
        wt_store = ws.open_checkout("alpha", cos[1]["id"])
        self.assertEqual(wt_store.dir, (wt / ".skald").resolve())
        sid = st.load_all()[0][0].id
        wt_store.claim(sid, "other")
        others = ws.other_checkouts(st)
        self.assertEqual([o.dir for o in others], [wt_store.dir])
        claims = st.claims_elsewhere(checkouts=others)
        self.assertEqual(claims[sid], [{"branch": "feature", "assignee": "other", "status": "in_progress",
                                        "checkout": str(wt_store.dir)}])
        # The primary is untouched and still open by name; the worktree store is not cached under the name.
        self.assertEqual(ws.open("alpha").dir, self.skald_dir.resolve())
        self.assertIsNone(ws.open_checkout("alpha", "nope"))
        # Committing in the worktree does not double-count: the working tree stands in for its branch.
        git(wt, "add", "-A")
        git(wt, "commit", "-qm", "claim")
        claims = st.claims_elsewhere(checkouts=ws.other_checkouts(st))
        self.assertEqual(len(claims[sid]), 1)
        self.assertEqual(len(st.claims_elsewhere()[sid]), 1)

    def test_user_config_types(self):
        u = UserConfig(self.home)
        self.assertEqual(u.get("port"), 8321)
        u.set("port", "9000")
        u.set("push", "yes")
        u.set("author", "Jon")
        again = UserConfig(self.home)
        self.assertEqual((again.get("port"), again.get("push"), again.get("author")), (9000, True, "Jon"))
        with self.assertRaises(SkaldError):
            u.set("port", "abc")
        with self.assertRaises(SkaldError):
            u.set("push", "maybe")
        with self.assertRaises(SkaldError):
            u.get("colour")
        u.unset("author")
        self.assertEqual(UserConfig(self.home).get("author"), "")

    def test_workspace_current_and_autoregister(self):
        Registry(self.home).remove("alpha")
        (self.skald_dir / "config.json").unlink()
        ws = self.workspace()
        store = ws.current()
        self.assertEqual(store.name, "alpha")
        self.assertTrue((self.skald_dir / "config.json").exists())
        self.assertTrue(any("wrote" in n for n in ws.notices))
        self.assertEqual(Registry(self.home).path_of("alpha"), self.skald_dir.resolve())
        sub = self.repo / "src" / "deep"
        sub.mkdir(parents=True)
        self.assertEqual(find_skald_dir(sub), self.skald_dir)
        os.environ["SKALD_DIR"] = str(self.skald_dir)
        self.assertEqual(find_skald_dir(Path("/")), self.skald_dir.resolve())
        os.environ.pop("SKALD_DIR")
        with self.assertRaises(NotFoundError):
            self.workspace().current(start=Path(self.tmp))
        with self.assertRaises(NotFoundError):
            self.workspace().current("nope")
        (self.skald_dir / "config.json").write_text('{"name": "alpha", "format": 42}')
        with self.assertRaises(ConfigError):
            self.workspace().current()


class TestUserConfigCoercion(SkaldTestCase):
    def test_hand_edited_values_are_coerced(self):
        u = UserConfig(self.home)
        u.data.update({"stale_days": "7", "push": "yes", "port": "not a number", "author": None})
        u.save()
        again = UserConfig(self.home)
        self.assertEqual((again.get("stale_days"), again.get("push"), again.get("port"), again.get("author")), (7, True, 8321, ""))


class TestSnapshots(SkaldTestCase):
    def setUp(self):
        super().setUp()
        s = self.store()
        self.a, _ = s.create("on both", status="ready")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "checkout", "-qb", "feature")
        self.b, _ = s.create("only on feature")
        s.update(self.a.id, status="done")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "feature work")
        git(self.repo, "checkout", "-q", "master")

    def test_snapshot_reads_objects_not_worktree(self):
        s = self.store()
        snap = s.snapshot("feature")
        self.assertTrue(snap.readonly)
        self.assertEqual(snap.ref, "feature")
        ids = {x.id: x.status for x in snap.load_all()[0]}
        self.assertEqual(ids, {self.a.id: "done", self.b.id: "backlog"})
        self.assertEqual(s.get(self.a.id).status, "ready")          # worktree untouched
        self.assertEqual(git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").strip(), "master")
        self.assertEqual(snap.get(self.b.id[:3]).title, "only on feature")
        from skald.errors import NotFoundError, SkaldError
        with self.assertRaises(NotFoundError):
            snap.get("zzz")
        with self.assertRaises(NotFoundError):
            s.snapshot("no-such-branch")
        d = snap.story_dict(snap.get(self.b.id))
        self.assertEqual((d["ref"], d["project"], d["blocked"]), ("feature", "alpha", False))

    def test_branch_diff(self):
        s = self.store()
        diff = s.branch_diff(s.snapshot("feature"))
        self.assertEqual([x.id for x in diff["only_there"]], [self.b.id])
        self.assertEqual(diff["only_here"], [])
        self.assertEqual([(h.status, t.status) for h, t in diff["differ"]], [("ready", "done")])
        same = s.branch_diff(s.snapshot("master"))
        self.assertEqual((same["only_there"], same["only_here"], same["differ"]), ([], [], []))

    def test_snapshot_uses_config_at_ref_and_local_deps(self):
        s = self.store()
        git(self.repo, "checkout", "-q", "feature")
        ProjectConfig.from_dict({"name": "alpha", "columns": SAMPLE_CONFIG_COLUMNS}).save(self.skald_dir / "config.json")
        c, _ = self.store().create("dep", status="qa", blocked_by=[self.b.id, "other:abc123"])
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "custom columns")
        git(self.repo, "checkout", "-q", "master")
        snap = s.snapshot("feature")
        self.assertEqual(snap.config.keys, ["backlog", "ready", "doing", "qa", "done", "wont_do"])
        states = {d.ref: d.state for d in snap.dep_states(snap.get(c.id))}
        self.assertEqual(states, {self.b.id: "backlog", "other:abc123": "unavailable"})


class TestFacets(SkaldTestCase):
    def test_facets_group_and_count(self):
        from skald.store import facets, split_facet

        self.assertEqual(split_facet("epic:auth"), ("epic", "auth"))
        self.assertEqual(split_facet("epic:a:b"), ("epic", "a:b"))
        self.assertIsNone(split_facet("plain"))
        self.assertIsNone(split_facet("epic:"))
        s = self.store()
        a, _ = s.create("a", tags=["epic:auth", "area:web"], status="ready")
        b, _ = s.create("b", tags=["epic:auth"], status="done")
        c, _ = s.create("c", tags=["epic:billing", "plain"])
        stories, _ = s.load_all(include_archived=True)
        f = facets(stories, s.config)
        self.assertEqual(list(f), ["area", "epic"])
        self.assertEqual(f["epic"]["auth"], {"total": 2, "done": 1, "open": 1, "ids": [a.id, b.id]})
        self.assertEqual(f["epic"]["billing"]["total"], 1)
        self.assertEqual(f["area"]["web"]["ids"], [a.id])


class TestNotesAndAcceptance(SkaldTestCase):
    def test_parse_notes_requirements_and_kinds(self):
        from skald.store import parse_notes, requirements_of

        s = self.store()
        a, _ = s.create("a", body="Do the thing.\n\n## Acceptance\n\n- [ ] one\n- [x] two\n")
        s.append_note(a.id, "first", "claude")
        s.append_note(a.id, "why", "claude", kind="decision")
        s.append_note(a.id, "state\nof play", "claude", kind="handoff")
        story = s.get(a.id)
        notes = story.notes()
        self.assertEqual([n["kind"] for n in notes], ["note", "decision", "handoff"])
        self.assertEqual(notes[2]["text"], "state\nof play")
        self.assertEqual(story.last_note("handoff")["text"], "state\nof play")
        self.assertEqual(story.last_note("blocker"), None)
        self.assertIn("## [claude] ", story.body)
        self.assertIn(" UTC · handoff\n", story.body)
        # requirements_of is the ## Requirements section only; the prelude is every section.
        self.assertEqual(requirements_of(story.body), "## Requirements\n\nDo the thing.")
        from skald.store import prelude_of, section_of, sections_of
        self.assertTrue(prelude_of(story.body).endswith("- [x] two"))
        self.assertEqual(sections_of(story.body), [{"heading": "Requirements", "lines": 1}, {"heading": "Acceptance", "lines": 2}])
        self.assertEqual(section_of(story.body, "acc"), "## Acceptance\n\n- [ ] one\n- [x] two")
        self.assertIsNone(section_of(story.body, "design"))
        # Without the heading, requirements are the whole prelude; a heading followed directly by a note is empty.
        self.assertEqual(requirements_of("Just prose.\n\n## [x] 2026-01-01 00:00 UTC\nnote"), "Just prose.")
        self.assertEqual(requirements_of("## Requirements\n## [x] 2026-01-01 00:00 UTC\nnote"), "## Requirements")
        self.assertEqual(sections_of("no headings"), [])
        d = story.to_dict()
        self.assertEqual(d["acceptance"], {"done": 1, "total": 2})
        self.assertEqual(d["checklist"], {"done": 1, "total": 2})
        compact = story.to_dict(compact=True)
        self.assertNotIn("filename", compact)
        self.assertNotIn("created_at", compact)
        with self.assertRaises(SkaldError):
            s.append_note(a.id, "x", "claude", kind="Not Valid")

    def test_parents_field_children_cycles_and_delete(self):
        from skald.errors import ConflictError, SkaldError
        from skald.store import parse_story_text, serialise_story
        s = self.store()
        epic, _ = s.create("Auth overhaul", tags=["epic:auth", "area:web", "plain"])
        child, _ = s.create("Login form", parent=epic.id, tags=["ui"])
        # Inherits the parent's facet tags only; the field is written in canonical position and round-trips.
        self.assertEqual(child.tags, ["area:web", "epic:auth", "ui"])
        self.assertEqual(s.get(child.id).parent, epic.id)
        text = child.path.read_text()
        self.assertLess(text.index("assignee") if "assignee" in text else text.index("parent"), text.index("created_at"))
        fields, body = parse_story_text(text, "x")
        self.assertEqual(serialise_story(fields, body), text)
        other, _ = s.create("No inherit", parent=epic.id, inherit=False)
        self.assertEqual(other.tags, [])
        # children and progress in story_dict.
        self.assertEqual([c.id for c in s.children(epic.id)], sorted([child.id, other.id], key=lambda i: [c.id for c in s.children(epic.id)].index(i)))
        d = s.story_dict(s.get(epic.id), s.index())
        self.assertEqual(d["children"], {"total": 2, "done": 0})
        self.assertNotIn("children", s.story_dict(s.get(child.id), s.index()))
        # Cross-project, self, and cycles are rejected at set time.
        with self.assertRaises(SkaldError):
            s.update(child.id, parent="other:abc123")
        with self.assertRaises(SkaldError):
            s.update(child.id, parent=child.id)
        with self.assertRaises(SkaldError):
            s.update(epic.id, parent=child.id)
        # Clearing.
        s.update(other.id, parent="-")
        self.assertEqual(s.get(other.id).parent, "")
        # rm refuses while children exist, like blocked_by.
        with self.assertRaises(ConflictError):
            s.delete(epic.id)
        # check: a dangling parent and a hand-made cycle are problems.
        child_path = s.get(child.id).path
        child_path.write_text(child_path.read_text().replace(f'parent: "{epic.id}"', 'parent: "ffffff"'))
        problems, _ = s.check()
        self.assertTrue(any("parent references missing story ffffff" in p for p in problems), problems)
        child_path.write_text(child_path.read_text().replace('parent: "ffffff"', f'parent: "{epic.id}"'))
        epic_path = s.get(epic.id).path
        epic_path.write_text(epic_path.read_text().replace('created_at:', f'parent: "{child.id}"\ncreated_at:'))
        problems, _ = s.check()
        self.assertTrue(any(p.startswith("parent cycle:") for p in problems), problems)
        epic_path.write_text(epic_path.read_text().replace(f'parent: "{child.id}"\n', ''))
        # Moving a parent to done with an open child warns; release warns too.
        _, w = s.update(epic.id, status="done")
        self.assertTrue(any("child(ren) still open" in x for x in w), w)
        from skald import release as rel
        plan = rel.plan(s, "9.9.9")
        self.assertTrue(any("ships with 1 child(ren) still open" in x for x in plan.warnings))

    def test_lanes_skip_next_and_warn_on_claim_and_move(self):
        import json as _json
        cfg_path = self.skald_dir / "config.json"
        data = _json.loads(cfg_path.read_text())
        data["facet_limits"] = {"lane": 1}
        cfg_path.write_text(_json.dumps(data))
        s = self.store()
        self.assertEqual(s.config.facet_limits, {"lane": 1})
        a, _ = s.create("Rewrite baseline, part 1", status="ready", tags=["lane:alembic"])
        b, _ = s.create("Rewrite baseline, part 2", status="ready", tags=["lane:alembic"])
        c, _ = s.create("Unrelated", status="ready", tags=["lane:docs"])
        # Nothing active: a is next.
        self.assertEqual(s.next_story().id, a.id)
        # a active locally: b is skipped with a warning, c is offered.
        _, w = s.claim(a.id, "one")
        self.assertEqual(w, [])
        notes = []
        self.assertEqual(s.next_story(for_author="two", warnings=notes).id, c.id)
        self.assertTrue(any(f"skipping {b.id}: lane lane:alembic is busy (1/1: {a.id})" in n for n in notes))
        # claim and move into an active column warn but proceed.
        _, w = s.claim(b.id, "two")
        self.assertTrue(any("enters a busy lane" in x for x in w), w)
        s.update(b.id, status="ready")
        _, w = s.update(b.id, status="in_progress")
        self.assertTrue(any("enters a busy lane: lane lane:alembic is busy" in x for x in w), w)
        s.update(b.id, status="ready")
        s.update(a.id, status="ready", assignee="")
        # A claim on another branch or in another checkout holds the lane too.
        elsewhere = {a.id: [{"branch": "feat/x", "assignee": "one", "status": "in_progress"}]}
        self.assertEqual(s.busy_lanes(elsewhere=elsewhere), {"lane": {"alembic": [a.id]}})
        self.assertEqual(s.lane_conflicts(s.get(b.id), s.busy_lanes(elsewhere=elsewhere)),
                         [f"lane lane:alembic is busy (1/1: {a.id})"])
        s.update(c.id, status="backlog")
        notes = []
        self.assertIsNone(s.next_story(for_author="two", elsewhere=elsewhere, warnings=notes))
        self.assertTrue(any(f"skipping {b.id}: lane lane:alembic is busy" in n for n in notes), notes)
        s.update(c.id, status="ready")
        # A limit of 2 admits two.
        data["facet_limits"] = {"lane": 2}
        cfg_path.write_text(_json.dumps(data))
        s = self.store()
        s.claim(a.id, "one")
        _, w = s.claim(b.id, "two")
        self.assertFalse(any("busy lane" in x for x in w), w)
        self.assertEqual(s.busy_lanes(), {"lane": {"alembic": [a.id, b.id]}})
        # Validation.
        from skald.config import ProjectConfig
        from skald.errors import ConfigError
        for bad in ({"lane": 0}, {"lane": "1"}, {"Bad Key": 1}, ["lane"]):
            data["facet_limits"] = bad
            cfg_path.write_text(_json.dumps(data))
            with self.assertRaises(ConfigError):
                ProjectConfig.load(cfg_path)

    def test_questions_close_only_when_a_decision_names_them(self):
        from skald.store import reopened_questions
        s = self.store()
        a, _ = s.create("a")
        self.assertEqual(s.get(a.id).open_questions(), [])
        s.append_note(a.id, "Postgres or SQLite?", "claude", kind="question")
        s.append_note(a.id, "progress", "claude")
        s.append_note(a.id, "Also: which port?", "claude", kind="question")
        qs = s.get(a.id).open_questions()
        self.assertEqual([(q["number"], q["text"]) for q in qs], [(1, "Postgres or SQLite?"), (2, "Also: which port?")])
        d = s.story_dict(s.get(a.id))
        self.assertEqual(d["questions"]["open"], 2)
        self.assertEqual([q["number"] for q in d["questions"]["items"]], [1, 2])
        self.assertNotIn("closed", d["questions"])
        self.assertEqual(s.story_dict(s.get(a.id), compact=True)["questions"], {"open": 2})
        # A plain decision closes nothing, whatever it says; check reports the questions it would once have closed.
        s.append_note(a.id, "SQLite, port 5000", "jon", kind="decision")
        self.assertEqual(len(s.get(a.id).open_questions()), 2)
        self.assertEqual([q["number"] for q in reopened_questions(s.get(a.id).notes())], [1, 2])
        _, warnings = s.check()
        self.assertTrue(any("Q1, Q2 open again" in w for w in warnings), warnings)
        # Several open and no target: refuse. A target by number or label closes that one; its number is stable.
        with self.assertRaises(SkaldError) as cm:
            s.answer(a.id, "SQLite", "jon")
        self.assertIn("2 questions are open (Q1, Q2)", str(cm.exception))
        story, closed = s.answer(a.id, "5000", "jon", question="Q2")
        self.assertEqual([q["number"] for q in closed], [2])
        self.assertIn("· decision\nAnswers Q2 [claude] ", story.body)
        self.assertEqual([q["number"] for q in story.open_questions()], [1])
        d = s.story_dict(story)
        self.assertEqual([(q["number"], q["closed_by"]["how"], q["closed_by"]["author"]) for q in d["questions"]["closed"]], [(2, "answered", "jon")])
        with self.assertRaises(SkaldError) as cm:
            s.answer(a.id, "again", "jon", question=2)
        self.assertIn("Q2 is already answered", str(cm.exception))
        with self.assertRaises(SkaldError):
            s.answer(a.id, "x", "jon", question=9)
        # One open and no target: it is the target. Withdraw records a drop. A new question gets the next number.
        s.append_note(a.id, "And auth?", "claude", kind="question")
        self.assertEqual([q["number"] for q in s.get(a.id).open_questions()], [1, 3])
        story, closed = s.answer(a.id, "Out of scope for this story.", "jon", question=3, withdraw=True)
        self.assertEqual(story.questions()[2]["closed_by"]["how"], "withdrawn")
        self.assertIn("Withdraws Q3 [claude] ", story.body)
        story, closed = s.answer(a.id, "SQLite.", "jon")
        self.assertEqual(([q["number"] for q in closed], story.open_questions()), ([1], []))
        self.assertEqual(reopened_questions(story.notes()), [])
        # Nothing open: refuse rather than write a second kind of plain decision. --all sweeps several.
        with self.assertRaises(SkaldError) as cm:
            s.answer(a.id, "x", "jon")
        self.assertIn("no open question", str(cm.exception))
        s.append_note(a.id, "Q4?", "claude", kind="question")
        s.append_note(a.id, "Q5?", "claude", kind="question")
        story, closed = s.answer(a.id, "Both moot.", "jon", all_open=True)
        self.assertEqual([q["number"] for q in closed], [4, 5])
        first_lines = story.notes()[-1]["text"].splitlines()[:2]
        self.assertTrue(all(l.startswith("Answers Q") for l in first_lines), first_lines)
        self.assertEqual(story.open_questions(), [])

    def test_acceptance_gate_warns_on_forward_moves(self):
        s = self.store()
        a, _ = s.create("a", body="## Acceptance\n\n- [ ] renders\n")
        _, w = s.update(a.id, status="ready")
        self.assertEqual(w, [])
        _, w = s.update(a.id, status="in_progress")          # first active: no gate
        self.assertEqual(w, [])
        _, w = s.update(a.id, status="review")               # forward past first active
        self.assertTrue(any("1 of 1 acceptance criteria unchecked" in x for x in w))
        _, w = s.update(a.id, status="in_progress")          # backwards: no gate
        self.assertEqual(w, [])
        _, w = s.update(a.id, status="done")
        self.assertTrue(any("acceptance" in x for x in w))
        s.write_body(a.id, "## Acceptance\n\n- [x] renders\n", None)
        _, w = s.update(a.id, status="review")
        self.assertEqual(w, [])


class TestClaimAwareness(SkaldTestCase):
    def test_stale_assignment_is_offered_and_takeover_warns(self):
        s = self.store()
        a, _ = s.create("pre-assigned", status="ready", assignee="bob")
        notes = []
        self.assertIsNone(s.next_story(for_author="alice", stale_days=3, warnings=notes))
        self.assertEqual(notes, [])
        # backdate the assignment
        raw = a.path.read_text().replace(a.fields["updated_at"], "2020-01-01T00:00:00Z")
        a.path.write_text(raw)
        notes = []
        self.assertEqual(s.next_story(for_author="alice", stale_days=3, warnings=notes).id, a.id)
        self.assertIn("untouched for 3+ days", notes[0])
        story, warnings = s.claim(a.id, "alice", stale_days=3)
        self.assertEqual(story.assignee, "alice")
        self.assertIn("was assigned to bob (stale); now alice", warnings[0])

    def test_claims_on_other_branches(self):
        s = self.store()
        a, _ = s.create("shared", status="ready")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "checkout", "-qb", "agent/two")
        s.claim(a.id, "codex")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "codex claims")
        git(self.repo, "checkout", "-q", "master")
        elsewhere = self.store().claims_elsewhere()
        self.assertEqual(elsewhere, {a.id: [{"branch": "agent/two", "assignee": "codex", "status": "in_progress"}]})
        notes = []
        self.assertIsNone(self.store().next_story(for_author="claude", elsewhere=elsewhere, warnings=notes))
        self.assertIn("claimed by codex on branch agent/two", notes[0])
        self.assertEqual(self.store().next_story(for_author="codex", elsewhere=elsewhere).id, a.id)
        story, warnings = self.store().claim(a.id, "claude", elsewhere=elsewhere)
        self.assertTrue(any("also claimed by codex" in w for w in warnings))


class TestDiffStates(SkaldTestCase):
    def test_diff_between_snapshots(self):
        from skald.store import diff_states

        s = self.store()
        a, _ = s.create("a", status="ready")
        b, _ = s.create("b")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "one")
        s.update(a.id, status="done", tags=["t"])
        s.append_note(b.id, "n")
        s.write_body(b.id, s.get(b.id).body + "extra\n", None)   # note plus body edit -> counts as notes only
        c, _ = s.create("c")
        s.delete(b.id)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "two")
        d = diff_states(s.snapshot("HEAD~1"), s.snapshot("HEAD"))
        self.assertEqual([x.id for x in d["added"]], [c.id])
        self.assertEqual([x.id for x in d["removed"]], [b.id])
        self.assertEqual(len(d["changed"]), 1)
        ch = d["changed"][0]
        self.assertEqual(ch["fields"]["status"], ("ready", "done"))
        self.assertEqual(ch["fields"]["tags"], ([], ["t"]))
        d2 = diff_states(None, s.snapshot("HEAD"))
        self.assertEqual(sorted(x.id for x in d2["added"]), sorted([a.id, c.id]))
