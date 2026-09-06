"""Store behaviour: ranks, dependencies, cross-project refs, columns, archive, registry."""
import json
import os
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
        s.delete(a.id, force=True)
        self.assertFalse(a.path.exists())
        problems, _ = s.check()
        self.assertTrue(any("missing story" in p for p in problems))
        s.delete(b.id)
        self.assertEqual(s.check(), ([], []))

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
        (s.templates_dir / "bug.md").write_text("## Steps\n\n1.\n\n## Expected\n")
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
            self.assertEqual(config_home(), self.tmp / "xdg" / "skald")
        finally:
            os.environ.pop("XDG_CONFIG_HOME")

    def test_register_move_remove(self):
        r = Registry(self.home)
        self.assertEqual([e["name"] for e in r.entries()], ["alpha"])
        self.assertIsNone(r.register("alpha", self.skald_dir))
        other = self.make_repo("moved", init_skald=False)
        (other / ".skald" / "stories").mkdir(parents=True)
        notice = r.register("alpha", other / ".skald")
        self.assertIn("moved", notice)
        self.assertEqual(Registry(self.home).path_of("alpha"), (other / ".skald").resolve())
        r.remove("alpha")
        with self.assertRaises(NotFoundError):
            r.remove("alpha")
        self.assertEqual(r.entries(), [])

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
