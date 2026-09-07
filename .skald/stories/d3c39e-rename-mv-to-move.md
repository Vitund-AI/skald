---
title: "Rename mv to move"
status: "review"
rank: 360
tags: ["cli"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-07T19:34:04Z"
updated_at: "2026-09-07T19:34:22Z"
---
## Requirements

## Requirements

mv carries file semantics (source path, destination path). skald move <id> <column> is the Kanban verb and does not suggest the file is relocated. Keep mv as a hidden alias for one release. See D43.

## [claude] 2026-09-07 19:34 UTC · result
Renamed across CLI, docs, agent contract, skill, and tests. The alias is dispatched by the same handler, and command_reference() lists each parser once so the Help panel shows only move.
