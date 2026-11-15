---
title: "Done and closed columns show the most recent first"
status: "done"
rank: 30
tags: ["area:board"]
blocked_by: []
assignee: "claude"
created_at: "2026-11-15T21:41:30Z"
updated_at: "2026-11-15T21:42:28Z"
---
## Requirements

A story moving into a column gets that column's bottom rank, so in Done and
Closed, rank is the order stories finished. The board shows them by rank,
oldest first, so the story you just finished sinks to the bottom of a long
column. People look there for "what did I just move" and "what finished
overnight".

- The board and the rendered board (`.skald/README.md` and HTML) show done
  and closed columns newest first, by reading rank in reverse.
- In a done or closed column, a dropped card lands at the top, as the
  newest. Dragging a card within the column changes nothing; rank there
  records finish order, not priority.
- The files and `skald release` are unchanged. Ranks stay integers, and the
  CHANGELOG still lists stories in the order they finished. Nothing
  migrates.

## Acceptance
- [x] The board's done and closed columns list the most recently finished first, in swimlanes too.
- [x] Dropping a card into Done puts it at the top; a drag within Done is a no-op; Undo still restores.
- [x] The rendered README and HTML board list done and closed newest first.
- [x] docs/board.md and CHANGELOG updated.

## [claude] 2026-11-15 21:42 UTC · handoff
Done. render.Board.in_column reverses done and closed columns (md and html). Board: renderColumns lists terminal columns reversed and marks their lists data-terminal; onDragOver puts the placeholder on top there; onDrop into a terminal column sends no order (entering takes the bottom rank, shown on top), skips cards already in the column, and goes through bulkMove for several. tests/test_render.py: done newest first in md and html, backlog still by rank (fails without the change). Playwright: Done shows D2,D1; dropping B lands on top with its acceptance warning and Undo; dragging D1 within Done is a no-op (ranks unchanged); Undo returns B to the backlog.
