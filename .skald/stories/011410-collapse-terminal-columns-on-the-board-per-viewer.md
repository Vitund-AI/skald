---
title: "Collapse terminal columns on the board, per viewer"
status: "done"
rank: 40
tags: ["roadmap"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-13T23:56:02Z"
updated_at: "2026-09-14T00:01:22Z"
---
## Requirements

Let a viewer collapse a finished column so it stops crowding the active board.

- A per-viewer control collapses any terminal column (done or closed role) to a thin labeled strip showing the column label and its story count; click to expand.
- State lives in `localStorage`, private to the viewer and non-destructive: no config change and no data change. The column and its stories still exist and still count everywhere (dependencies, release, facets, swimlanes).
- Discoverable: the collapsed strip shows the count so nothing is hidden silently, and expanding is one click.
- Generalises beyond won't-do: a large Done column collapses the same way.

## Why

A closed or won't-do column, and a big Done column, clutter the active board. Hiding is a viewing preference, not a property of the board, so it belongs per-viewer in `localStorage` rather than in config. Keeps the lightweight feel and adds no schema.

## [agent] 2026-09-14 00:01 UTC · result
Board: a terminal column (done or closed role) renders a caret in its header that collapses it to a labeled strip showing its count; the whole strip expands on click. state.collapsed is a Set of column keys loaded per project from localStorage (skald.collapsed:<project>) in applyProject and saved on each toggle; render() redraws. Collapsing only hides the column's card list and drops its flex-grow so it shrinks to its header, so nothing is removed and the count stays visible; non-terminal columns get no caret. It is purely a viewing preference: no config, no data, no server change, and it works in read-only branch views too. Verified with a headless-browser pass on lifecycle columns: only Done has a caret, collapse hides its .col-list and writes ["done"] to localStorage, the state survives a reload (caret shows the collapsed glyph), expand restores the cards, a backlog column has no caret, and no page errors. Docs: SPEC layout paragraph, docs/board.md Columns and cards, CHANGELOG Unreleased. Suite 160 green, ruff clean.
