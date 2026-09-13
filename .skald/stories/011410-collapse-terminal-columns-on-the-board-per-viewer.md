---
title: "Collapse terminal columns on the board, per viewer"
status: "idea"
rank: 110
tags: ["roadmap"]
blocked_by: []
created_at: "2026-09-13T23:56:02Z"
updated_at: "2026-09-13T23:56:02Z"
---
## Requirements

Let a viewer collapse a finished column so it stops crowding the active board.

- A per-viewer control collapses any terminal column (done or closed role) to a thin labeled strip showing the column label and its story count; click to expand.
- State lives in `localStorage`, private to the viewer and non-destructive: no config change and no data change. The column and its stories still exist and still count everywhere (dependencies, release, facets, swimlanes).
- Discoverable: the collapsed strip shows the count so nothing is hidden silently, and expanding is one click.
- Generalises beyond won't-do: a large Done column collapses the same way.

## Why

A closed or won't-do column, and a big Done column, clutter the active board. Hiding is a viewing preference, not a property of the board, so it belongs per-viewer in `localStorage` rather than in config. Keeps the lightweight feel and adds no schema.
