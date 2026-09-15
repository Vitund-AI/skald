---
title: "Show claim provenance as author@branch on the board and in ls"
status: "idea"
rank: 90
tags: ["area:board", "area:cli"]
blocked_by: ["50b992"]
created_at: "2026-09-15T17:26:47Z"
updated_at: "2026-09-15T17:26:47Z"
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
