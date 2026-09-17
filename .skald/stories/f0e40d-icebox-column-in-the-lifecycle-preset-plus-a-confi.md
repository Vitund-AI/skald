---
title: "Icebox column in the lifecycle preset, plus a configurable default_status for new stories"
status: "review"
rank: 20
tags: ["roadmap"]
blocked_by: []
assignee: "agent"
created_at: "2026-09-17T06:09:24Z"
updated_at: "2026-09-17T06:15:12Z"
---
## Requirements

Standardise how users park work that is decided-not-now but not won't-do: an Icebox column (backlog role) in the lifecycle preset, placed far-left as cold storage.

Because skald new defaults to the first backlog column, an icebox-first column would capture new stories. Fix generally: a new project config.json key default_status naming the column new stories default to (validated against column keys; falls back to today's first-backlog behaviour when unset). Thread it through store.create (already uses config.default_key) and the board's New-story modal (currently hardcodes first backlog role), and surface it in the board payload.

- LIFECYCLE_COLUMNS gains icebox (backlog) first; skald init --columns lifecycle also writes default_status: idea so new cards still start in Idea.
- Convention (docs): park to Icebox; revive to Idea/Plan, never straight to Ready, because the plan may be stale. Contrast with won't-do (closed): icebox is backlog-role so it is never archived or written to the changelog, and never appears in ready/next.
- Lightweight: transitions are NOT enforced (see idea 05e3b1).

Docs: SPEC (config keys + lifecycle preset + convention), conventions.md, board.md, cli.md regen + init --columns help, CHANGELOG, DECISIONS. Update tests that assert the lifecycle preset.
