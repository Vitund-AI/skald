---
title: "Machine-local project index with auto-registration"
status: "review"
rank: 70
tags: ["core"]
blocked_by: []
created_at: "2026-09-06T07:04:41Z"
updated_at: "2026-09-06T07:04:41Z"
---
## Requirements

Every command registers the current project in ~/.config/skald/projects.json. skald projects lists, skald projects rm forgets, -p NAME and --all-projects act across projects.

## [claude] 2026-09-06 07:04 UTC
Implemented in registry.py. init is reserved for creating the layout (D8). Re-registering a name from another path updates the path with a notice (D10).
