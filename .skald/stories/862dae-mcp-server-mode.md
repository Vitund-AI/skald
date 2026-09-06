---
title: "MCP server mode"
status: "review"
rank: 190
tags: ["agents"]
blocked_by: []
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-06T07:08:04Z"
---
## Requirements

skald mcp exposing the store as MCP tools over stdio (list, next, show, new, mv, claim, note, tag, block) so agents without shell access can use it. Stdlib JSON-RPC only.

## [claude] 2026-09-06 07:08 UTC
Implemented: skald mcp serves JSON-RPC over stdio with initialize, ping, tools/list, tools/call and batches. Thirteen tools mirror the CLI (D26). Register with: claude mcp add skald -- skald mcp.
