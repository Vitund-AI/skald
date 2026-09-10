---
title: "Compact output and skald context for agent orientation"
status: "done"
rank: 150
tags: ["agents"]
blocked_by: []
assignee: "claude"
released: "0.2.0"
created_at: "2026-09-06T19:01:42Z"
updated_at: "2026-09-10T00:56:31Z"
---
## Requirements

One token-bounded orientation block: my assigned stories with last note, the next unblocked story, blockers, uncommitted story files. --compact on ls and next drops verbose fields from JSON.

## Changelog

`skald context --as NAME` prints one orientation block: your assigned stories with their last note, the next unblocked story, blockers, stale claims, claims elsewhere, and uncommitted story files. `--compact` on `ls` and `next` trims the JSON.

## [claude] 2026-09-06 19:06 UTC
Implemented: skald context --as NAME (text and JSON) and --compact on ls/next; MCP skald_context. Context shows mine with last note and handoff flag, next, blocked ready stories, stale claims, claims elsewhere, uncommitted files.
