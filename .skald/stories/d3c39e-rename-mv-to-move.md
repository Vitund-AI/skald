---
title: "Rename mv to move"
status: "done"
rank: 260
tags: ["cli"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-07T19:34:04Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

mv carries file semantics (source path, destination path). skald move <id> <column> is the Kanban verb and does not suggest the file is relocated. Keep mv as a hidden alias for one release. See D43.

## Changelog

`skald mv` is now `skald move <id> <column>`, the Kanban verb. `mv` still works as a hidden alias for this release.

## [claude] 2026-09-07 19:34 UTC · result
Renamed across CLI, docs, agent contract, skill, and tests. The alias is dispatched by the same handler, and command_reference() lists each parser once so the Help panel shows only move.
