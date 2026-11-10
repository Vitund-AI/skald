---
title: "A drag reranks one story, not the whole column"
status: "done"
rank: 10
tags: ["agents", "area:board", "area:store"]
blocked_by: []
assignee: "claude"
released: "1.3.1"
created_at: "2026-11-08T09:11:37Z"
updated_at: "2026-11-09T18:48:58Z"
---
## Requirements

Feedback from heavy use: one drag on a busy board produced a 208-file diff. `Store.reorder` renumbers the whole column to 10, 20, 30… in the given order, so every story below the drop point (and any whose rank was not already on that grid) is rewritten. The board makes it worse: with a filter on, it appends every hidden card to the end of the order, and in swimlanes it sends only the target lane, so the column's other cards are moved to the bottom.

An agent suggested fractional or LexoRank keys. `rank` is an integer in the story format, which 1.x promises to keep, and an older 1.x install would reject a story with a non-integer rank. Sparse integers give the same one-file property within the format.

## Acceptance
- [x] `reorder` keeps the longest run of stories already in the asked relative order where they are and gives only the others new ranks, between their neighbours; one drag writes one file while there is a gap.
- [x] When neighbours leave no gap, only a small window around the spot is respaced, never the whole column.
- [x] Ranks stay integers (negative allowed above the top card); existing files need no migration.
- [x] The board sends an order in which cards it did not move keep their place: filtered-out cards and cards in other swimlanes stay put.
- [x] Tests show a 200-story column taking one write per drag; SPEC, docs, DECISIONS, CHANGELOG updated.

## [claude] 2026-11-08 09:18 UTC · handoff
Done.
- store:
  - `plan_ranks(ranks)` keeps a longest strictly increasing run (`_increasing_run`, a patience sort) and places the others between their kept neighbours, steps of 10 above the top (0 or negative allowed) and below the bottom.
  - On a gap under 1 it drops the nearest kept neighbours from the run and retries, so respacing stays local.
  - `reorder` writes only stories whose rank changed.
- Board: `columnOrder()` sends the whole column with untouched cards in place. A filtered-out card stays attached to the next placed card, and other lanes' cards stay put. This replaces `order.concat(hidden)` for single and batch drags.
- Docs: SPEC sort-order bullet, api.md `order` note, D86, CHANGELOG.

Verified:
- new tests: a 200-story column takes one write per drag (mid, top, bottom); `plan_ranks` cases (one move, above the top, local respace with the tail unchanged, equal ranks spread);
- the old tests that asserted the 10/20/30 renumbering now assert order and untouched neighbours;
- headless Chromium on a 30-story board: a plain drag, a filtered drag (search area:web) and a swimlane drag (by area) each changed exactly 1 story file, and the cards landed where dropped;
- the full suite, ruff and docs --check.
