"""The MCP stdio server: protocol handshake and every tool."""
import io
import json

from skald.mcp import McpServer, TOOLS

from .helpers import SkaldTestCase


class TestMcp(SkaldTestCase):
    def rpc(self, server, method, params=None, msg_id=1):
        return server.handle({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})

    def call(self, server, name, **args):
        res = self.rpc(server, "tools/call", {"name": name, "arguments": args})
        payload = res["result"]["content"][0]["text"]
        if res["result"]["isError"]:
            return None, payload
        return json.loads(payload), None

    def test_handshake_and_tool_list(self):
        server = McpServer(self.workspace())
        res = self.rpc(server, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {}})
        self.assertEqual(res["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(res["result"]["serverInfo"]["name"], "skald")
        self.assertIsNone(server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertEqual(self.rpc(server, "ping")["result"], {})
        names = [t["name"] for t in self.rpc(server, "tools/list")["result"]["tools"]]
        self.assertEqual(names, [t["name"] for t in TOOLS])
        for t in TOOLS:
            self.assertEqual(t["inputSchema"]["type"], "object")
        self.assertEqual(self.rpc(server, "nope")["error"]["code"], -32601)
        self.assertEqual(self.rpc(server, "tools/call", {"name": "skald_nope"})["error"]["code"], -32602)

    def test_tools_end_to_end(self):
        server = McpServer(self.workspace())
        status, _ = self.call(server, "skald_status")
        self.assertEqual(status["project"], "alpha")
        cols, _ = self.call(server, "skald_columns")
        self.assertEqual(cols[0]["key"], "backlog")

        created, _ = self.call(server, "skald_new", title="First", tags=["x"], body="- [ ] a")
        a = created["story"]["id"]
        second, _ = self.call(server, "skald_new", title="Second", status="ready", blocked_by=[a])
        b = second["story"]["id"]
        self.assertEqual(len(second["warnings"]), 1)

        listed, _ = self.call(server, "skald_list")
        self.assertEqual([s["id"] for s in listed], [a, b])
        listed, _ = self.call(server, "skald_list", unblocked=True)
        self.assertEqual([s["id"] for s in listed], [a])
        nxt, _ = self.call(server, "skald_next")
        self.assertIsNone(nxt["story"])
        moved, _ = self.call(server, "skald_move", id=a, status="ready")
        nxt, _ = self.call(server, "skald_next")
        self.assertEqual(nxt["story"]["id"], a)
        claimed, _ = self.call(server, "skald_claim", id=a[:3], **{"as": "claude"})
        self.assertEqual((claimed["story"]["assignee"], claimed["story"]["status"]), ("claude", "in_progress"))
        noted, _ = self.call(server, "skald_note", id=a, text="hello", **{"as": "claude"})
        self.assertIn("## [claude] ", noted["body"])
        shown, _ = self.call(server, "skald_show", id=a)
        self.assertIn("hello", shown["body"])
        updated, _ = self.call(server, "skald_set", id=a, title="Renamed", rank=5)
        self.assertEqual((updated["story"]["title"], updated["story"]["rank"]), ("Renamed", 5))
        tagged, _ = self.call(server, "skald_tag", id=a, add=["Y"], remove=["x"])
        self.assertEqual(tagged["story"]["tags"], ["y"])
        blocked, _ = self.call(server, "skald_block", id=b, remove=[a])
        self.assertEqual(blocked["story"]["blocked_by"], [])
        blocked, _ = self.call(server, "skald_block", id=a, add=[b])
        self.assertEqual(blocked["story"]["blocked_by"], [b])
        check, _ = self.call(server, "skald_check")
        self.assertTrue(check["ok"])
        ctx, _ = self.call(server, "skald_context", **{"as": "claude"})
        self.assertEqual([m["id"] for m in ctx["mine"]], [a])
        self.call(server, "skald_note", id=a, text="state of play", kind="handoff", **{"as": "claude"})
        res, _ = self.call(server, "skald_resume", id=a)
        self.assertEqual(res["latest"]["kind"], "handoff")
        self.assertIn("requirements", res)
        self.assertIn("sections", res)
        res, _ = self.call(server, "skald_resume", id=a, full=True)
        self.assertIn("body", res)
        _, err = self.call(server, "skald_resume", id=a, section="nope")
        self.assertIn("no section", err)
        self.call(server, "skald_note", id=a, text="Which port?", kind="question")
        ctx, _ = self.call(server, "skald_context", **{"as": "claude"})
        self.assertEqual([w["id"] for w in ctx["waiting"]], [a])
        res, _ = self.call(server, "skald_resume", id=a)
        self.assertEqual(len(res["open_questions"]), 1)
        ans, _ = self.call(server, "skald_answer", id=a, text="5000", **{"as": "jon"})
        self.assertEqual((ans["closed_questions"], ans["questions"]["open"]), (1, 0))
        aud, _ = self.call(server, "skald_audit", id=a, note=False)
        self.assertEqual((aud["noted"], aud["paths"]["checked"]), (False, 0))
        self.assertIn("paths", aud["summary"][0])

        _, err = self.call(server, "skald_show", id="zzz")
        self.assertIn("ERROR: no story matches", err)
        _, err = self.call(server, "skald_move", id=a, status="nope")
        self.assertIn("invalid status", err)
        _, err = self.call(server, "skald_set", id=a)
        self.assertIn("nothing to set", err)
        _, err = self.call(server, "skald_show")
        self.assertIn("bad arguments", err)

    def test_serve_loop_over_streams(self):
        server = McpServer(self.workspace())
        lines = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            "not json",
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "skald_columns", "arguments": {}}}),
            json.dumps([{"jsonrpc": "2.0", "id": 3, "method": "ping"}, {"jsonrpc": "2.0", "id": 4, "method": "ping"}]),
        ]
        out = io.StringIO()
        server.serve(io.StringIO("\n".join(lines) + "\n"), out)
        responses = [json.loads(l) for l in out.getvalue().splitlines()]
        self.assertEqual(responses[0]["id"], 1)
        self.assertEqual(responses[1]["error"]["code"], -32700)
        self.assertEqual(responses[2]["id"], 2)
        self.assertIn("backlog", responses[2]["result"]["content"][0]["text"])
        self.assertEqual([r["id"] for r in responses[3]], [3, 4])
