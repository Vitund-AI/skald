"""skald export: a flat, single-file dump of the backlog in json, jsonl, or csv."""
import csv
import io
import json

from .helpers import SkaldTestCase


class TestExport(SkaldTestCase):
    def setUp(self):
        super().setUp()
        self.a = self.new("First, with a comma", "--tags", "backend,area:api,area:cli")
        self.b = self.new("Second", "--status", "ready", "--tags", "release:1.0", "--blocked-by", self.a)

    def records(self, *extra):
        code, out, _ = self.run_cli("export", "--format", "json", *extra)
        self.assertEqual(code, 0)
        return json.loads(out)

    def test_json_shape_and_fields(self):
        recs = self.records()
        self.assertEqual([r["id"] for r in recs], [self.a, self.b])  # sorted, both present
        a = next(r for r in recs if r["id"] == self.a)
        self.assertEqual(a["project"], "alpha")
        self.assertEqual(a["title"], "First, with a comma")
        self.assertEqual(a["role"], "backlog")
        self.assertEqual(sorted(a["tags"]), ["area:api", "area:cli", "backend"])
        self.assertEqual(a["facets"], {"area": ["api", "cli"]})   # grouped by key, multi-value
        b = next(r for r in recs if r["id"] == self.b)
        self.assertEqual(b["blocked_by"], [self.a])
        self.assertTrue(b["blocked"])                             # unmet dependency on a
        self.assertEqual(b["facets"], {"release": ["1.0"]})
        # A stable, documented field set is present.
        for key in ("status", "rank", "assignee", "parent", "stale", "open_questions",
                    "checklist_done", "checklist_total", "created_at", "updated_at", "released", "archived"):
            self.assertIn(key, a)

    def test_jsonl_is_one_object_per_line(self):
        code, out, _ = self.run_cli("export", "--format", "jsonl")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual([json.loads(line)["id"] for line in lines], [self.a, self.b])

    def test_csv_flattens_with_facet_columns_and_escaping(self):
        code, out, _ = self.run_cli("export", "--format", "csv")
        self.assertEqual(code, 0)
        rows = list(csv.reader(io.StringIO(out)))
        header, a_row = rows[0], rows[1]
        self.assertIn("facet.area", header)
        self.assertIn("facet.release", header)
        row = dict(zip(header, a_row, strict=True))
        self.assertEqual(row["id"], self.a)
        self.assertEqual(row["title"], "First, with a comma")   # csv.reader round-trips the quoted comma
        self.assertEqual(row["facet.area"], "api|cli")          # multi-value joined
        self.assertEqual(row["blocked"], "false")

    def test_archived_flag_includes_shipped_stories(self):
        self.run_cli("move", self.a, "done")
        self.run_cli("archive")
        self.assertEqual([r["id"] for r in self.records()], [self.b])            # archived excluded by default
        with_archived = [r["id"] for r in self.records("--archived")]
        self.assertIn(self.a, with_archived)
        arch = next(r for r in self.records("--archived") if r["id"] == self.a)
        self.assertTrue(arch["archived"])

    def test_out_writes_file_and_keeps_stdout_clean(self):
        target = self.repo / "backlog.jsonl"
        code, out, _ = self.run_cli("export", "--format", "jsonl", "--out", str(target))
        self.assertEqual(code, 0)
        self.assertEqual(out, "")                                # the "wrote" note goes to stderr
        lines = target.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
