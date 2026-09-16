---
title: "Show claim provenance as author@branch on the board and in ls"
status: "in_progress"
rank: 10
tags: ["area:board", "area:cli"]
blocked_by: ["50b992"]
assignee: "claude"
created_at: "2026-09-15T17:26:47Z"
updated_at: "2026-09-16T03:30:04Z"
---
## Requirements

Follow-up to 50b992 (which makes `skald claim` warn on a cross-worktree/branch
collision keyed on origin rather than name). That story derives the origin
branch only at warn time. This one surfaces it durably so provenance is
visible at a glance.

## Idea

When a story is claimed elsewhere, show *where* — the origin branch or
worktree — next to the assignee, e.g. `claude@feature-x`, in:

- the board `claimed elsewhere` badge (it already carries the branch from
  `claims_elsewhere`; make the label read `assignee@branch`),
- `skald ls` / `skald context` where a claim-elsewhere is reported,
- optionally the claim note trail (record the branch the claim was made on).

## Constraints / decisions to make

- Do NOT change the stored `assignee` frontmatter field or the story format;
  `assignee` stays the bare name. Provenance is display-only, composed from
  the branch/checkout that `claims_elsewhere` already returns.
- Decide whether the local claim note (`skald claim` appends a note) should
  record the origin branch for durable audit, or whether display-only is
  enough (ties to 50b992 Q3).
- Keep it local-branches/worktrees only, consistent with `claims_elsewhere`.

## Acceptance
- [ ] the board claimed-elsewhere badge reads assignee@branch
- [ ] ls / context show the origin branch for an elsewhere-claim
- [ ] no change to the stored assignee field or the story format
- [ ] tests cover the rendered provenance
- [ ] docs updated (board.md)
- [ ] python3 -m unittest green, ruff clean

## [claude] 2026-09-16 03:30 UTC · decision
Investigation before building: most of this is already implemented on dev.

- Board card badge already renders 'also <assignee>@<branch>' with a tooltip of every elsewhere-claim (web/index.html card render, reading state.branches.claims). loadBranches() runs on project load and every 30s, so the badge shows without interaction. Acceptance item 1 already met.
- skald context already prints '<assignee> on <branch> (<status>)' + uncommitted checkout path (cli.py cmd_context); a test asserts 'worker on feature (in_progress)'. Most of item 2 met.
- docs/board.md already documents the 'also name@branch' marker.

The only untouched surface is skald ls, which shows just the local ASSIGNEE and nothing about elsewhere-claims. Tradeoff: claims_elsewhere snapshots every local branch + reads worktrees; context pays that occasionally, but ls is a frequent snappy table, so unconditional lookup there has a real cost.

Put three options to the maintainer: (A recommended) ls --elsewhere opt-in annotation + a regression test locking in board/context; (B) declare board+context sufficient, add a regression test, close; (C) ls always shows it. Awaiting the decision before building.
