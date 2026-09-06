"""Skald test suite. Run with:  python3 -m unittest"""
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import skald  # noqa: E402


SAMPLE = """---
title: "Implement WireGuard overlay network"
status: "ready"
rank: 20
tags: ["infrastructure", "v1.0"]
blocked_by: ["7b21e0", "c4d811"]
created_at: "2026-09-05T10:00:00Z"
updated_at: "2026-09-06T08:12:41Z"
estimate: 3
---
## Requirements

Configure wg0.

---
this line looks like a fence but is body
"""


class TempStore(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skald-test-"))
        self.store = skald.Store(self.tmp / ".skald")
        self.store.stories_dir.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write_raw(self, name, text):
        path = self.store.stories_dir / name
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return path

    def read_raw(self, story):
        with open(story.path, encoding="utf-8", newline="") as fh:
            return fh.read()


# --------------------------------------------------------------------------
# File format
# --------------------------------------------------------------------------


class TestFormat(unittest.TestCase):
    def test_round_trip_preserves_body_and_unknown_fields(self):
        fields, body = skald.parse_story_text(SAMPLE, "sample.md")
        self.assertEqual(fields["title"], "Implement WireGuard overlay network")
        self.assertEqual(fields["tags"], ["infrastructure", "v1.0"])
        self.assertEqual(fields["estimate"], 3)
        self.assertTrue(body.startswith("## Requirements\n"))
        self.assertIn("\n---\nthis line looks like a fence", body)
        self.assertEqual(skald.serialise_story(fields, body), SAMPLE)

    def test_crlf_body_is_preserved(self):
        text = "---\r\ntitle: \"x\"\r\nstatus: \"backlog\"\r\n---\r\nline one\r\nline two\r\n"
        fields, body = skald.parse_story_text(text)
        self.assertEqual(body, "line one\r\nline two\r\n")
        self.assertEqual(fields["title"], "x")

    def test_missing_optional_fields_default(self):
        fields, body = skald.parse_story_text('---\ntitle: "t"\nstatus: "backlog"\n---\n')
        self.assertEqual(fields["rank"], 0)
        self.assertEqual(fields["tags"], [])
        self.assertEqual(fields["blocked_by"], [])
        self.assertEqual(body, "")

    def test_tags_are_normalised(self):
        fields, _ = skald.parse_story_text('---\ntitle: "t"\nstatus: "backlog"\ntags: ["B", " a ", "b", ""]\n---\n')
        self.assertEqual(fields["tags"], ["a", "b"])

    def test_corrupt_cases_name_the_line(self):
        cases = {
            "no fence": ("title: x\n", "line 1"),
            "unclosed": ('---\ntitle: "x"\n', "closing '---' fence not found"),
            "bad line": ('---\ntitle "x"\n---\n', "line 2"),
            "not json": ('---\ntitle: unquoted\nstatus: "backlog"\n---\n', "line 2"),
            "block list": ('---\ntitle: "x"\nstatus: "backlog"\ntags:\n  - a\n---\n', "line 4"),
            "bad status": ('---\ntitle: "x"\nstatus: "doing"\n---\n', "'status'"),
            "empty title": ('---\ntitle: " "\nstatus: "backlog"\n---\n', "'title'"),
            "bool rank": ('---\ntitle: "x"\nstatus: "backlog"\nrank: true\n---\n', "'rank'"),
            "duplicate": ('---\ntitle: "x"\ntitle: "y"\nstatus: "backlog"\n---\n', "duplicate"),
        }
        for name, (text, needle) in cases.items():
            with self.subTest(name):
                with self.assertRaises(skald.CorruptStoryError) as cm:
                    skald.parse_story_text(text, "f.md")
                self.assertIn(needle, str(cm.exception))

    def test_slugify(self):
        self.assertEqual(skald.slugify('Write docs: the "guide"!'), "write-docs-the-guide")
        self.assertEqual(skald.slugify("Ünïcödé only ÿ"), "ncd-only")
        self.assertEqual(len(skald.slugify("word " * 40)), 49)
        self.assertEqual(skald.slugify("!!!"), "")

    def test_id_from_filename(self):
        self.assertEqual(skald.id_from_filename("a3f9c2-some-slug.md"), "a3f9c2")
        self.assertEqual(skald.id_from_filename("a3f9c2.md"), "a3f9c2")
        self.assertIsNone(skald.id_from_filename("A3F9C2-x.md"))
        self.assertIsNone(skald.id_from_filename("notes.md"))


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------


class TestStore(TempStore):
    def test_create_writes_canonical_file(self):
        story, warnings = self.store.create("Hello World", tags=["B", "a"], body="Do it")
        self.assertEqual(warnings, [])
        self.assertRegex(story.path.name, r"^[0-9a-f]{6}-hello-world\.md$")
        raw = self.read_raw(story)
        self.assertTrue(raw.startswith('---\ntitle: "Hello World"\nstatus: "backlog"\nrank: 10\ntags: ["a", "b"]\nblocked_by: []\n'))
        self.assertTrue(raw.endswith("---\n## Requirements\n\nDo it\n"))
        self.assertRegex(story.fields["created_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_ids_unique_and_prefix_lookup(self):
        ids = {self.store.create(f"s{i}")[0].id for i in range(30)}
        self.assertEqual(len(ids), 30)
        some = sorted(ids)[0]
        self.assertEqual(self.store.resolve(some), some)
        self.assertEqual(self.store.get(some[:6]).id, some)
        with self.assertRaises(skald.NotFoundError):
            self.store.resolve("zzz")
        with self.assertRaises(skald.SkaldError):
            self.store.resolve("")

    def test_ambiguous_prefix(self):
        self.write_raw("abc111-one.md", '---\ntitle: "one"\nstatus: "backlog"\n---\n')
        self.write_raw("abc222-two.md", '---\ntitle: "two"\nstatus: "backlog"\n---\n')
        with self.assertRaises(skald.SkaldError) as cm:
            self.store.resolve("abc")
        self.assertIn("ambiguous", str(cm.exception))
        self.assertEqual(self.store.resolve("abc1"), "abc111")

    def test_unmet_and_blocked(self):
        a, _ = self.store.create("a", status="done")
        b, _ = self.store.create("b", status="ready")
        c, warnings = self.store.create("c", status="ready", blocked_by=[a.id, b.id, ])
        idx = self.store.index()
        self.assertEqual(self.store.unmet(c, idx), [b.id])
        self.assertEqual(len(warnings), 1)
        self.assertIn(f"{b.id} (ready)", warnings[0])
        # missing ids count as unmet
        self.write_raw("ffffff-ghost.md", f'---\ntitle: "g"\nstatus: "ready"\nblocked_by: ["000000"]\n---\n')
        ghost = self.store.get("ffffff")
        self.assertEqual(self.store.unmet(ghost, self.store.index()), ["000000"])
        self.assertIn("000000 (missing)", self.store.unmet_warning(ghost, self.store.index()))

    def test_create_unknown_blocker_is_error(self):
        with self.assertRaises(skald.NotFoundError):
            self.store.create("x", blocked_by=["123456"])

    def test_ranks_on_create_move_and_reorder(self):
        a, _ = self.store.create("a")
        b, _ = self.store.create("b")
        c, _ = self.store.create("c", status="ready")
        self.assertEqual([a.rank, b.rank, c.rank], [10, 20, 10])
        a2, _ = self.store.update(a.id, status="ready")
        self.assertEqual(a2.rank, 20)  # bottom of ready
        # same-status update does not change rank
        a3, _ = self.store.update(a.id, title="renamed")
        self.assertEqual(a3.rank, 20)
        self.assertEqual(a3.title, "renamed")
        changed = self.store.reorder("ready", [a.id, c.id])
        self.assertEqual({s.id for s in changed}, {a.id, c.id})
        idx = self.store.index()
        self.assertEqual((idx[a.id].rank, idx[c.id].rank), (10, 20))
        # reorder with a partial list keeps the rest after, in existing order
        d, _ = self.store.create("d", status="ready")
        self.store.reorder("ready", [d.id])
        idx = self.store.index()
        self.assertEqual([idx[d.id].rank, idx[a.id].rank, idx[c.id].rank], [10, 20, 30])
        with self.assertRaises(skald.SkaldError):
            self.store.reorder("backlog", [a.id])

    def test_move_and_order_in_one_update(self):
        a, _ = self.store.create("a", status="ready")
        b, _ = self.store.create("b", status="ready")
        c, _ = self.store.create("c")
        c2, warnings = self.store.update(c.id, status="ready", order=[a.id, c.id, b.id])
        self.assertEqual(warnings, [])
        idx = self.store.index()
        self.assertEqual([idx[a.id].rank, idx[c.id].rank, idx[b.id].rank], [10, 20, 30])
        self.assertEqual(c2.status, "ready")
        self.assertEqual(c2.rank, 20)

    def test_move_warns_only_on_forward_transitions_with_unmet(self):
        a, _ = self.store.create("a")
        b, _ = self.store.create("b", blocked_by=[a.id])
        for status in ("ready", "in_progress", "review", "done"):
            _, warnings = self.store.update(b.id, status=status)
            self.assertEqual(len(warnings), 1, status)
            self.assertIn("unmet dependencies", warnings[0])
        _, warnings = self.store.update(b.id, status="backlog")
        self.assertEqual(warnings, [])
        # once a is done there is no warning
        self.store.update(a.id, status="done")
        _, warnings = self.store.update(b.id, status="in_progress")
        self.assertEqual(warnings, [])
        # unchanged status does not warn
        _, warnings = self.store.update(b.id, status="in_progress", title="x")
        self.assertEqual(warnings, [])

    def test_blockers_self_and_cycle(self):
        a, _ = self.store.create("a")
        b, _ = self.store.create("b", blocked_by=[a.id])
        with self.assertRaises(skald.SkaldError):
            self.store.update(a.id, blocked_by=[a.id])
        a2, warnings = self.store.update(a.id, blocked_by=[b.id])
        self.assertEqual(a2.blocked_by, [b.id])
        self.assertTrue(any("cycle" in w for w in warnings))
        problems = self.store.check()
        self.assertEqual(len([p for p in problems if "cycle" in p]), 1)

    def test_update_validation(self):
        a, _ = self.store.create("a")
        with self.assertRaises(skald.SkaldError):
            self.store.update(a.id, status="nope")
        with self.assertRaises(skald.SkaldError):
            self.store.update(a.id, title="  ")
        with self.assertRaises(skald.SkaldError):
            self.store.update(a.id, rank="5")
        with self.assertRaises(skald.SkaldError):
            self.store.update(a.id, tags="a,b")

    def test_notes(self):
        a, _ = self.store.create("a")
        self.store.append_note(a.id, "first\nline two", author="agent")
        self.store.append_note(a.id, "  second  ", author="human")
        body = self.store.get(a.id).body
        self.assertRegex(body, r"^## Requirements\n\n## \[agent\] \d{4}-\d\d-\d\d \d\d:\d\d UTC\nfirst\nline two\n\n## \[human\] .*\nsecond\n$")
        with self.assertRaises(skald.SkaldError):
            self.store.append_note(a.id, "   ")
        with self.assertRaises(skald.SkaldError):
            self.store.append_note(a.id, "x", author="a]b")

    def test_write_body_conflict(self):
        a, _ = self.store.create("a")
        sha = self.store.body_sha(a)
        self.store.write_body(a.id, "new body\n", sha)
        self.assertEqual(self.store.get(a.id).body, "new body\n")
        with self.assertRaises(skald.ConflictError):
            self.store.write_body(a.id, "other\n", sha)
        self.store.write_body(a.id, "forced\n", None)
        self.assertEqual(self.store.get(a.id).body, "forced\n")

    def test_delete_refuses_dependency_unless_forced(self):
        a, _ = self.store.create("a")
        b, _ = self.store.create("b", blocked_by=[a.id])
        with self.assertRaises(skald.ConflictError):
            self.store.delete(a.id)
        self.store.delete(a.id, force=True)
        self.assertFalse(a.path.exists())
        problems = self.store.check()
        self.assertTrue(any("missing story" in p for p in problems))
        self.store.delete(b.id)
        self.assertEqual(self.store.check(), [])

    def test_load_all_skips_corrupt(self):
        self.store.create("good")
        self.write_raw("bad000-broken.md", "no fence\n")
        stories, warnings = self.store.load_all()
        self.assertEqual(len(stories), 1)
        self.assertEqual(len(warnings), 1)
        self.assertIn("bad000-broken.md", warnings[0])

    def test_check_finds_conflict_markers_and_bad_names(self):
        self.write_raw("aaaaaa-x.md", '---\ntitle: "x"\n<<<<<<< HEAD\nstatus: "ready"\n=======\nstatus: "done"\n>>>>>>> other\n---\n')
        self.write_raw("Notes.md", "hello")
        problems = self.store.check()
        self.assertTrue(any("conflict markers" in p for p in problems))
        self.assertTrue(any("Notes.md" in p for p in problems))

    def test_write_preserves_unknown_fields_and_body(self):
        path = self.write_raw("abcdef-sample.md", SAMPLE)
        self.store.update("abcdef", status="in_progress")
        with open(path, encoding="utf-8", newline="") as fh:
            raw = fh.read()
        self.assertIn('status: "in_progress"', raw)
        self.assertIn("estimate: 3\n", raw)
        self.assertTrue(raw.endswith("this line looks like a fence but is body\n"))
        # updated_at is regenerated; everything else identical
        self.assertIn('blocked_by: ["7b21e0", "c4d811"]', raw)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


class TestCLI(TempStore):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = skald.run(list(argv), store=self.store)
            except skald.SkaldError as e:
                print(f"ERROR: {e}", file=sys.stderr)
                code = e.exit_code
            except SystemExit as e:  # argparse
                code = int(e.code or 0)
        return code, out.getvalue(), err.getvalue()

    def new(self, *argv):
        code, out, err = self.run_cli("new", *argv)
        self.assertEqual(code, 0, err)
        return out.strip()

    def test_full_flow(self):
        a = self.new("Implement WireGuard", "--tags", "Infra,v1.0", "--body", "Configure wg0")
        b = self.new("Set up CI", "--status", "ready")
        c = self.new('Write "docs"', "--status", "ready", "--blocked-by", f"{a},{b}")
        self.assertRegex(a, r"^[0-9a-f]{6}$")

        code, out, err = self.run_cli("ls")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0].split(), ["ID", "STATUS", "RANK", "BLOCKED", "TAGS", "TITLE"])
        self.assertEqual(len(lines), 4)
        self.assertIn(",".join(sorted([a, b])), out)
        self.assertIn("infra,v1.0", out)

        code, out, _ = self.run_cli("ls", "--unblocked", "--json")
        self.assertEqual([s["id"] for s in json.loads(out)], [a, b])
        code, out, _ = self.run_cli("ls", "--tag", "INFRA", "--json")
        self.assertEqual([s["id"] for s in json.loads(out)], [a])
        code, out, _ = self.run_cli("ls", "--status", "ready", "--json")
        self.assertEqual([s["id"] for s in json.loads(out)], [b, c])

        code, out, _ = self.run_cli("next", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["id"], b)

        code, out, err = self.run_cli("mv", c[:3], "in_progress")
        self.assertEqual(code, 0)
        self.assertIn(f"moved {c} to in_progress", out)
        self.assertIn(f"WARNING: {c} has unmet dependencies: ", err)
        self.assertIn(f"{a} (backlog)", err)
        self.assertIn(f"{b} (ready)", err)

        code, out, err = self.run_cli("tag", c, "+Docs", "-nothing")
        self.assertEqual(code, 0, err)
        self.assertIn("docs", out)
        code, out, err = self.run_cli("block", c, f"-{a}")
        self.assertEqual(code, 0, err)
        self.assertIn(f"blocked_by: {b}", out)
        code, out, err = self.run_cli("block", a, f"+{c}")
        self.assertEqual(code, 0, err)
        self.assertNotIn("cycle", err)
        code, out, err = self.run_cli("block", b, f"+{c}")
        self.assertEqual(code, 0, err)
        self.assertIn("WARNING: dependency cycle", err)

        code, out, err = self.run_cli("set", c, "title=Docs rewritten", "rank=5")
        self.assertEqual(code, 0, err)
        code, out, _ = self.run_cli("show", c, "--json")
        d = json.loads(out)
        self.assertEqual((d["title"], d["rank"], d["status"]), ("Docs rewritten", 5, "in_progress"))
        self.assertIn("body", d)
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
        self.assertIn(f"deleted {c}", out)

    def test_next_when_nothing_ready(self):
        self.new("a")
        code, out, err = self.run_cli("next")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("no ready", err)

    def test_done_hidden_unless_all(self):
        a = self.new("a", "--status", "done")
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
        body = self.store.get(a).body
        self.assertIn("Requirements from stdin\n", body)
        self.assertIn("## [human] ", body)
        self.assertTrue(body.endswith("note from stdin\n"))

    def test_errors_and_exit_codes(self):
        code, _, err = self.run_cli("show", "zzz")
        self.assertEqual(code, 1)
        self.assertIn("ERROR: no story matches", err)
        self.write_raw("bad000-x.md", "garbage")
        code, _, err = self.run_cli("show", "bad000")
        self.assertEqual(code, 2)
        self.assertIn("line 1", err)
        code, out, err = self.run_cli("ls")
        self.assertEqual(code, 0)
        self.assertIn("WARNING: skipping corrupt story", err)
        a = self.new("a")
        code, _, err = self.run_cli("set", a, "status=done")
        self.assertEqual(code, 1)
        code, _, err = self.run_cli("set", a, "rank=x")
        self.assertEqual(code, 1)
        code, _, err = self.run_cli("tag", a)
        self.assertEqual(code, 1)
        code, _, err = self.run_cli("tag", a, "plain")
        self.assertEqual(code, 1)
        code, _, err = self.run_cli("mv", a, "nowhere")
        self.assertEqual(code, 2)  # argparse usage error
        code, _, _ = self.run_cli()
        self.assertEqual(code, 1)

    def test_check_ok_and_json(self):
        self.new("a")
        code, out, _ = self.run_cli("check")
        self.assertEqual((code, out.strip()), (0, "ok"))
        code, out, _ = self.run_cli("check", "--json")
        self.assertEqual(json.loads(out), {"ok": True, "problems": []})

    def test_init_is_idempotent_and_vendors_itself(self):
        shutil.rmtree(self.store.dir)
        code, out, err = self.run_cli("init")
        self.assertEqual(code, 0, err)
        self.assertTrue((self.store.stories_dir / ".gitkeep").exists())
        agents = self.store.dir / "AGENTS.md"
        self.assertEqual(agents.read_text(), skald.AGENTS_MD)
        vendored = self.store.dir / "skald.py"
        self.assertEqual(vendored.read_bytes(), Path(skald.__file__).read_bytes())
        agents.write_text("custom")
        code, out, err = self.run_cli("init")
        self.assertEqual(code, 0, err)
        self.assertEqual(agents.read_text(), "custom")
        self.assertIn("kept existing", out)


# --------------------------------------------------------------------------
# HTTP API
# --------------------------------------------------------------------------


class TestAPI(TempStore):
    def setUp(self):
        super().setUp()
        self.httpd = skald.SkaldServer(("127.0.0.1", 0), self.store, quiet=True)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        t.start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req) as res:
                raw = res.read()
                return res.status, (json.loads(raw) if raw else None)
        except HTTPError as e:
            raw = e.read()
            return e.code, (json.loads(raw) if raw else None)

    def test_index_and_404(self):
        with urlopen(self.base + "/") as res:
            self.assertEqual(res.status, 200)
            self.assertIn("text/html", res.headers["Content-Type"])
            self.assertIn(b"<title>Skald</title>", res.read())
        self.assertEqual(self.call("GET", "/nope")[0], 404)
        self.assertEqual(self.call("GET", "/api/nope")[0], 404)

    def test_crud_flow(self):
        status, data = self.call("POST", "/api/stories", {"title": "First", "tags": ["x"], "body": "Body"})
        self.assertEqual(status, 201)
        a = data["story"]["id"]
        self.assertEqual(data["warnings"], [])
        status, data = self.call("POST", "/api/stories", {"title": "Second", "status": "ready", "blocked_by": [a]})
        self.assertEqual(status, 201)
        b = data["story"]["id"]
        self.assertTrue(data["story"]["blocked"])
        self.assertEqual(len(data["warnings"]), 1)

        status, board = self.call("GET", "/api/board")
        self.assertEqual(status, 200)
        self.assertEqual(board["statuses"], skald.STATUSES)
        self.assertEqual([s["id"] for s in board["stories"]], [a, b])
        self.assertEqual(board["stories"][1]["unmet"], [a])

        status, one = self.call("GET", f"/api/stories/{a[:4]}")
        self.assertEqual(status, 200)
        self.assertEqual(one["body"], "## Requirements\n\nBody\n")
        self.assertEqual(one["body_sha256"], skald.sha256_text(one["body"]))

        # combined move and reorder, with a warning
        status, data = self.call("PATCH", f"/api/stories/{a}", {"status": "ready", "order": [a, b]})
        self.assertEqual(status, 200)
        self.assertEqual(data["story"]["rank"], 10)
        status, board = self.call("GET", "/api/board")
        self.assertEqual([(s["id"], s["rank"]) for s in board["stories"]], [(a, 10), (b, 20)])

        status, data = self.call("PATCH", f"/api/stories/{b}", {"status": "in_progress", "tags": ["y"], "title": "Second!"})
        self.assertEqual(status, 200)
        self.assertEqual(data["story"]["tags"], ["y"])
        self.assertIn("unmet dependencies", data["warnings"][0])
        status, data = self.call("PATCH", f"/api/stories/{b}", {"bogus": 1})
        self.assertEqual(status, 400)
        status, data = self.call("PATCH", f"/api/stories/{b}", {"status": "bogus"})
        self.assertEqual(status, 400)
        self.assertIn("error", data)

        # body with optimistic concurrency
        status, data = self.call("PUT", f"/api/stories/{a}/body", {"body": "edited\n", "base_sha256": one["body_sha256"]})
        self.assertEqual(status, 200)
        status, data = self.call("PUT", f"/api/stories/{a}/body", {"body": "stale\n", "base_sha256": one["body_sha256"]})
        self.assertEqual(status, 409)
        self.assertEqual(self.store.get(a).body, "edited\n")

        status, data = self.call("POST", f"/api/stories/{a}/notes", {"text": "hello"})
        self.assertEqual(status, 201)
        self.assertIn("## [human] ", data["body"])
        status, data = self.call("POST", f"/api/stories/{a}/notes", {"text": ""})
        self.assertEqual(status, 400)

        status, _ = self.call("DELETE", f"/api/stories/{a}")
        self.assertEqual(status, 409)
        status, _ = self.call("DELETE", f"/api/stories/{a}?force=1")
        self.assertEqual(status, 204)
        status, _ = self.call("GET", f"/api/stories/{a}")
        self.assertEqual(status, 404)
        status, _ = self.call("DELETE", f"/api/stories/{b}")
        self.assertEqual(status, 204)

    def test_bad_json(self):
        req = Request(self.base + "/api/stories", data=b"{not json", method="POST")
        req.add_header("Content-Type", "application/json")
        with self.assertRaises(HTTPError) as cm:
            urlopen(req)
        self.assertEqual(cm.exception.code, 400)

    def test_board_reports_corrupt_files(self):
        self.write_raw("bad000-x.md", "nope")
        status, board = self.call("GET", "/api/board")
        self.assertEqual(status, 200)
        self.assertEqual(len(board["warnings"]), 1)


# --------------------------------------------------------------------------
# Repository invariants
# --------------------------------------------------------------------------


class TestRepo(unittest.TestCase):
    def test_vendored_copy_matches_root(self):
        vendored = ROOT / ".skald" / "skald.py"
        if not vendored.exists():
            self.skipTest("no vendored copy in this checkout")
        self.assertEqual(vendored.read_bytes(), (ROOT / "skald.py").read_bytes())

    def test_agents_md_matches_embedded_template(self):
        agents = ROOT / ".skald" / "AGENTS.md"
        if not agents.exists():
            self.skipTest("no .skald/AGENTS.md in this checkout")
        self.assertEqual(agents.read_text(encoding="utf-8"), skald.AGENTS_MD)

    def test_own_backlog_is_clean(self):
        store = skald.Store(ROOT / ".skald")
        if not store.stories_dir.exists():
            self.skipTest("no .skald/stories in this checkout")
        self.assertEqual(store.check(), [])


if __name__ == "__main__":
    unittest.main()
