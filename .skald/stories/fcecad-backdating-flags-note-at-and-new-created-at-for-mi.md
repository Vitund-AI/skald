---
title: "Backdating flags: note --at and new --created-at for migration scripts"
status: "ready"
rank: 80
tags: ["cli"]
blocked_by: []
created_at: "2026-09-10T05:09:38Z"
updated_at: "2026-09-10T05:09:38Z"
---
## Requirements

A migration script that brings an existing Markdown backlog into Skald needs to backdate notes and creation stamps. Two explicit flags, default now: skald note --at "YYYY-MM-DD HH:MM" and skald new --created-at .... The skald import command from the design-record feature request (item 7) is deferred until a script has been used on one bucket and the mapping has settled; these are the primitives it would need regardless.

## Acceptance
- [ ] note --at writes the given stamp in the heading; new --created-at sets created_at and updated_at
- [ ] Invalid stamps are rejected; cli.md, CHANGELOG
