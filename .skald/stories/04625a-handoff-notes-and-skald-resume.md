---
title: "Handoff notes and skald resume"
status: "done"
rank: 130
tags: ["agents"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T19:01:42Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

note --kind handoff|decision|blocker stamps the heading; skald resume <id> prints requirements, checklist state, dependencies, and only the latest handoff so the next session starts from the state of play.

## Changelog

Notes can carry a kind: `--kind handoff`, `decision`, or `blocker` stamps the heading. `skald resume <id>` prints a story's requirements, checklist state, dependencies, and only the latest handoff, so the next session starts from the state of play.

## [claude] 2026-09-06 19:06 UTC
Implemented: note --kind (heading suffix · kind, D31), Story.notes/last_note, skald resume printing requirements, checklist and acceptance state, deps, decisions, and the latest handoff; MCP skald_resume. Contract updated to hand off before stopping.
