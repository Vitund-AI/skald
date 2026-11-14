"""Dependency graph generation, the graph command, the Mermaid block in render, skill and pointer installers."""
import json
import os
import subprocess
import sys
from pathlib import Path

from skald.graph import build_graph, to_dot, to_mermaid

from .helpers import SkaldTestCase

ROOT = Path(__file__).resolve().parents[1]


class TestGraph(SkaldTestCase):
    def seed(self):
        s = self.store()
        a, _ = s.create("Base", status="done")
        b, _ = s.create("Middle", status="ready", blocked_by=[a.id])
        c, _ = s.create("Top", blocked_by=[b.id, "other:abc123"])
        d, _ = s.create("Loner")
        return s, a, b, c, d

    def test_build_graph_nodes_edges_cycles(self):
        s, a, b, c, d = self.seed()
        g = build_graph(s, s.load_all()[0])
        ids = [n["id"] for n in g["nodes"]]
        self.assertEqual(sorted(ids), sorted([a.id, b.id, c.id, "other:abc123"]))
        self.assertNotIn(d.id, ids)
        ext = next(n for n in g["nodes"] if n["id"] == "other:abc123")
        self.assertEqual((ext["external"], ext["status"], ext["role"]), (True, "unavailable", "unknown"))
        e_ab = next(e for e in g["edges"] if e["from"] == a.id)
        self.assertEqual((e_ab["to"], e_ab["satisfied"], e_ab["cycle"]), (b.id, True, False))
        e_ext = next(e for e in g["edges"] if e["external"])
        self.assertTrue(e_ext["missing"])
        g_all = build_graph(s, s.load_all()[0], include_isolated=True)
        self.assertIn(d.id, [n["id"] for n in g_all["nodes"]])
        s.update(a.id, blocked_by=[c.id])           # a -> b -> c -> a
        g = build_graph(s, s.load_all()[0])
        self.assertTrue(all(e["cycle"] for e in g["edges"] if not e["external"]))

    def test_mermaid_and_dot(self):
        s, a, b, c, d = self.seed()
        g = build_graph(s, s.load_all()[0])
        mm = to_mermaid(g)
        self.assertTrue(mm.startswith("flowchart LR\n"))
        self.assertIn(f'n_{a.id}["{a.id}<br/>Base"]', mm)
        self.assertIn(f"n_{a.id} --> n_{b.id}", mm)
        self.assertIn("n_other__abc123 -.-> n_" + c.id, mm)
        self.assertIn('[/"other:abc123<br/>(in other)"/]', mm)
        self.assertIn("classDef done", mm)
        self.assertIn(f"class n_{a.id} done", mm)
        dot = to_dot(g)
        self.assertTrue(dot.startswith('digraph "alpha"'))
        self.assertIn(f'"{a.id}" -> "{b.id}"', dot)
        self.assertIn("style=dashed", dot)

    def test_mermaid_is_the_same_in_every_process(self):
        # String hashing differs per process, so anything ordered by a set would change run to
        # run; the rendered board must not, or CI re-renders and commits a board nobody changed.
        graph = {"nodes": [{"id": i, "title": i, "external": False, "role": r}
                           for i, r in (("a1", "unknown"), ("b2", "backlog"), ("c3", "done"), ("d4", "active"),
                                        ("e5", "ready"), ("f6", "custom"), ("g7", "closed"))],
                 "edges": []}
        script = "import json, sys; from skald.graph import to_mermaid; print(to_mermaid(json.loads(sys.argv[1])))"
        outs = set()
        for seed in ("0", "1", "2", "3", "4", "5", "6", "7"):
            env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(ROOT / "src"))
            proc = subprocess.run([sys.executable, "-c", script, json.dumps(graph)], env=env,
                                  capture_output=True, text=True, check=True)
            outs.add(proc.stdout)
        self.assertEqual(len(outs), 1)
        classes = [line.split()[-1] for line in outs.pop().splitlines() if line.startswith("    class ")]
        self.assertEqual(classes, ["backlog", "ready", "active", "done", "closed", "unknown", "custom"])

    def test_graph_command_and_render_block(self):
        code, out, err = self.run_cli("graph")
        self.assertEqual(out.strip(), "flowchart LR")
        self.assertIn("no dependencies", err)
        s, a, b, c, d = self.seed()
        code, out, _ = self.run_cli("graph")
        self.assertIn("-->", out)
        code, out, _ = self.run_cli("graph", "--format", "json")
        self.assertEqual(json.loads(out)["project"], "alpha")
        code, out, _ = self.run_cli("graph", "--format", "dot", "--all")
        self.assertIn(d.id, out)
        code, out, _ = self.run_cli("render", "--stdout")
        self.assertIn("## Dependencies\n\n```mermaid\nflowchart LR", out)
        self.assertIn("```\n", out)


class TestClaudeSkillAndPointer(SkaldTestCase):
    def test_hooks_claude_writes_skill(self):
        code, out, _ = self.run_cli("hooks", "claude", "--install")
        skill = self.repo / ".claude" / "skills" / "skald" / "SKILL.md"
        self.assertTrue(skill.exists())
        text = skill.read_text()
        self.assertTrue(text.startswith("---\nname: skald\ndescription: "))
        self.assertIn("# Working with Skald", text)
        self.assertIn("wrote .claude/skills/skald/SKILL.md", out)

    def test_init_pointer_cases(self):
        from skald.cli import POINTER

        repo = self.make_repo("fresh", init_skald=False)
        code, out, _ = self.run_cli("init", cwd=repo)
        self.assertIn("created", out)
        self.assertIn(POINTER, (repo / "AGENTS.md").read_text())
        (repo / "CLAUDE.md").write_text("# Notes\n")
        code, out, _ = self.run_cli("init", cwd=repo)
        self.assertIn("added the Skald pointer to CLAUDE.md", out)
        self.assertIn("AGENTS.md already points", out)
        self.assertEqual((repo / "CLAUDE.md").read_text(), "# Notes\n\n" + POINTER + "\n")
        code, out, _ = self.run_cli("init", cwd=repo)
        self.assertIn("CLAUDE.md already points", out)
