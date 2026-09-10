---
title: "Lifecycle columns: idea and plan before ready, an init preset, and a plan-to-ready warning on open questions"
status: "done"
rank: 60
tags: ["core", "docs"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T05:09:37Z"
updated_at: "2026-09-10T18:04:04Z"
---
## Requirements

A lifecycle from ideation through planning and discussion to execution: idea (backlog role), plan (backlog role), ready, in_progress, review, done. Waiting on a human is a condition, not a stage, so it stays a derived flag (questions story) rather than a column.

- skald init --columns lifecycle writes that column set; the default set is unchanged.
- Moving a story from a backlog-role column into a ready-role column while it has open questions warns, advisory, like unchecked acceptance on the move to done.
- Docs: stories.md documents the lifecycle set beside the design-record layout; SPEC 3 and 4.4; cli.md; CHANGELOG; DECISIONS (why questions are not a column).
- This repository switches to the lifecycle columns to dogfood them.

## Acceptance
- [x] init --columns lifecycle and a test
- [x] Warning on the backlog-to-ready move with open questions
- [x] Docs synced; this repo's config.json uses the lifecycle set

## [claude] 2026-09-10 05:24 UTC · result
COLUMN_PRESETS in config.py with the lifecycle set; init --columns default|lifecycle (existing config.json untouched, with a notice). update() warns on a backlog-role to ready-role move with open questions. This repository now uses the lifecycle set; the one backlog story moved to idea. Docs: stories.md The lifecycle set, SPEC 3 and 4.4, cli.md, CHANGELOG, D55. 131 tests pass.
