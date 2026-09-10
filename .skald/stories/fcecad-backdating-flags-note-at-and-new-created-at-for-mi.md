---
title: "Backdating flags: note --at and new --created-at for migration scripts"
status: "done"
rank: 110
tags: ["cli"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T05:09:38Z"
updated_at: "2026-09-10T18:04:04Z"
---
## Requirements

A migration script that brings an existing Markdown backlog into Skald needs to backdate notes and creation stamps. Two explicit flags, default now: skald note --at "YYYY-MM-DD HH:MM" and skald new --created-at .... The skald import command from the design-record feature request (item 7) is deferred until a script has been used on one bucket and the mapping has settled; these are the primitives it would need regardless.

## Acceptance
- [x] note --at writes the given stamp in the heading; new --created-at sets created_at and updated_at
- [x] Invalid stamps are rejected; cli.md, CHANGELOG

## [claude] 2026-09-10 05:47 UTC · result
util.parse_when accepts YYYY-MM-DD HH:MM (UTC), an ISO instant, or a bare date. note --at backdates the heading; new --created-at sets created_at and updated_at and skips the touch. Invalid stamps are rejected with a message naming the forms. MCP note takes at, new takes created_at. Tests on the CLI and MCP; SPEC 6, stories.md, cli.md, CHANGELOG. skald import stays deferred until a script has been used on one bucket.
