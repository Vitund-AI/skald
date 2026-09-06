---
title: "Compact output and skald context for agent orientation"
status: "review"
rank: 230
tags: ["agents"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T19:01:42Z"
updated_at: "2026-09-06T19:06:43Z"
---
## Requirements

One token-bounded orientation block: my assigned stories with last note, the next unblocked story, blockers, uncommitted story files. --compact on ls and next drops verbose fields from JSON.

## [claude] 2026-09-06 19:06 UTC
Implemented: skald context --as NAME (text and JSON) and --compact on ls/next; MCP skald_context. Context shows mine with last note and handoff flag, next, blocked ready stories, stale claims, claims elsewhere, uncommitted files.
