---
title: "Bulk operations on the board"
status: "review"
rank: 30
tags: ["ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-08T17:33:27Z"
---
## Requirements

Multi-select cards and move, tag, or archive them together.

## [human] 2026-09-08 04:24 UTC
A long mouse press could enable selection mode, a circle icon apears on the stories in the column of the selected story. The selected story has a check mark in a circle. Now when other stories are single clicked they become selected rather than opening the detail.

When the user has finished making the selection, they can drag to move the batch to a new column, or clicking in a different column deselects everything and normal operation is resumed.

## [claude] 2026-09-08 04:32 UTC · result
Implemented as you described: press and hold a card (450ms, pointer events so touch works too) starts a selection in that column; circles appear on the column's cards and the selected ones get a check. Clicks in the column toggle; a click elsewhere or Esc ends it; x on a focused card is the keyboard route. Dragging a selected card moves the batch and inserts it at the drop point. A bar at the bottom moves, tags, or archives the selection; archive shows only for done or closed columns and uses the new ids parameter on skald archive and POST .../archive. Verified in headless Chromium: long press, add and remove by click, batch drag, bulk tag, bulk move, archive, clear by column click and Esc, and that a normal click still opens the story afterwards. One bug caught there: the hold re-renders the board under the pointer, so the release lands on a new element and no click fires; pointer listeners now live on the document. D44.

## [human] 2026-09-08 17:26 UTC
tested moving sets of stories to different columns - ok

What I did note is that on click to select a card, the column scrolls back to the top of the list. This is not desirable behavior as it makes a multi select a click, scroll, click, scroll... task instead of a quick click through the items.

## [claude] 2026-09-08 17:33 UTC · result
Fixed the scroll jump: every render rebuilt the column elements, which reset their scroll offsets. render() now captures each column's scrollTop (and the board's own scroll) before rebuilding and restores them afterwards. Verified in headless Chromium on a 30-card column scrolled to 900px: long press, three selection clicks, and a live refresh from a CLI note all left the offset at 900 with the selection intact. Leaving the story in review for you to confirm.
