---
title: "Machine-local project index with auto-registration"
status: "done"
rank: 500
tags: ["core"]
blocked_by: []
released: "0.2.0"
created_at: "2026-09-06T07:04:41Z"
updated_at: "2026-09-10T00:56:31Z"
---
## Requirements

Every command registers the current project in ~/.config/skald/projects.json. skald projects lists, skald projects rm forgets, -p NAME and --all-projects act across projects.

## Changelog

Every command registers the current project in a machine-local index, so one board and `-p NAME` reach every repository you use Skald in. `skald projects` lists them, `skald projects rm` forgets one, and `--all-projects` acts across all of them.

## [claude] 2026-09-06 07:04 UTC
Implemented in registry.py. init is reserved for creating the layout (D8). Re-registering a name from another path updates the path with a notice (D10).
