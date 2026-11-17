---
title: "Board: Undo on the toast a move raises (warnings, and the bulk-move confirmation)"
status: "done"
rank: 40
tags: ["area:board"]
blocked_by: []
assignee: "claude"
released: "1.3.3"
created_at: "2026-11-15T21:30:05Z"
updated_at: "2026-11-17T05:25:13Z"
---
## Requirements

Moving a story can trip a check: unchecked acceptance criteria, open
questions moving to ready, unmet dependencies, a busy lane, a column over
its limit. The board shows each as a warning toast, but the move has
already happened. The only way back was to drag the card back by hand,
which lands it at the bottom of its old column, not where it was.

- The warning toast a move raises carries an **Undo** button. With several
  warnings, the last one carries it, and Undo dismisses them all. Toasts
  with Undo stay 12 seconds, not 6.
- It applies to a dragged card, a multi-card drag or a "Move to…" bulk
  move, and the status select in the story dialog. A bulk move with no
  warnings gets Undo on its "Moved N stories" toast.
- Undo puts back each story's column, tags (a swimlane drop retags) and
  exact rank, then the old column order. The column it left was not
  renumbered by the move, so restoring the rank writes only the moved
  stories.
- Undo raises its own warnings, if any, without an Undo of its own.

## Acceptance
- [x] A drag that warns offers Undo; Undo returns the story to its old column and position.
- [x] The story dialog's status select and a bulk move offer the same.
- [x] After an undo, only the moved stories' files differ, and only in updated_at.
- [x] docs/board.md and CHANGELOG updated.

## [claude] 2026-11-15 21:30 UTC · handoff
Done in src/skald/web/index.html: toast(msg, kind, action) takes an optional action button and returns its element; showWarnings(ws, undo) dedupes and puts Undo on the last warning; moveSnapshot(ids) records status, rank, tags and the left column's order from state.stories (already in column and rank order); undoMove(snap) PATCHes status, rank and tags back, then one order per column. Wired into onDrop (single), bulkMove (multi-drag and Move to…, with Undo on the confirmation when nothing warned) and the dialog's status select. Checked with Playwright on a scratch board: drag to review with unchecked acceptance, then Undo, restores backlog rank 50 between 40 and 60; same via the dialog select to ready (open question) and a bulk move of two to done. After all three, git diff shows only updated_at on the two moved stories.
