---
title: "Document attaching Skald's MCP server (skald mcp) to Cursor and other MCP clients"
status: "review"
rank: 50
tags: ["area:docs", "epic:integrations", "roadmap"]
blocked_by: []
assignee: "agent"
created_at: "2026-09-20T00:58:33Z"
updated_at: "2026-09-20T02:32:28Z"
---
## Requirements

v1 positioning: invite the broader agent ecosystem, not just Claude Code. skald mcp already serves the store as MCP tools over stdio, so this is documentation + an example, not new code.

- A docs page (and README pointer) showing the exact MCP client config to attach to skald mcp: Cursor first (native MCP support, largest AI-dev user base), then the generic shape that also covers Windsurf, Zed, and any MCP client (command: skald, args: [mcp], stdio transport; note SKALD_HOME / cwd so it resolves the project).
- Show what the agent gets (the MCP tool surface from cmd_mcp) and the AGENTS.md contract, so a Cursor/Windsurf user gets the same story-driven workflow as Claude Code.
- Consider an examples/ entry mirroring examples/model-routing.

Verify the current MCP tool list from src/skald/cli.py cmd_mcp before writing. No package code expected unless a gap surfaces.
