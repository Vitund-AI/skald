---
title: "Warn when claiming a story already active in another local worktree, same author included"
status: "done"
rank: 60
tags: ["area:cli"]
blocked_by: []
assignee: "claude"
released: "0.8.0"
created_at: "2026-09-15T17:22:01Z"
updated_at: "2026-09-16T07:11:46Z"
---
## Requirements

A `skald claim` (and, to a lesser extent, `skald move` into an active
column) should warn when the story is already active in another local
working tree or branch — even when the assignee is the same name — so two
parallel agents sharing an identity do not silently work the same story.

## Background — what already works

Skald already tracks cross-checkout / cross-branch claims via
`store.claims_elsewhere()` (`_claims_elsewhere`): it reads active,
assigned stories from other registered worktrees (on disk, so an
uncommitted claim is seen) and other **local** branches (committed state).
This already powers:

- `skald next` skipping a story claimed elsewhere,
- the board `claimed elsewhere` badge,
- and a warning in `store.claim`:
  `<id> is also claimed by <assignee> on branch <branch> (<status>)`.

## The gap

`store.claim` only emits that warning when `c["assignee"] != author`
(store.py ~line 894). Coding agents almost always run under one shared
identity (`claude`, `agent`), so the common multi-agent case is silent:

Reproduced with two git worktrees of one repo:
- worktree A: `skald claim X --as claude` -> claimed
- worktree B: `skald claim X --as claude` -> **claimed, no warning**
- worktree B: `skald claim X --as agent-two` -> warns as expected

Every entry in `claims_elsewhere[id]` is by definition in another tree or
branch (the current tree is never included), so a same-name entry is still
a real collision between two actors, not "you already have this here".

## Proposed change

In `store.claim`, warn for a same-author elsewhere-claim too, with wording
that distinguishes it from a different-author one so a genuinely resuming
agent is not alarmed, e.g.:

- different author (unchanged): `<id> is also claimed by <other> on branch <b> (<status>)`
- same author, other tree: `<id> is already active as <author> in another working tree (<path-or-branch>); two agents may be working it at once`

Keep it a **warning, not a block** — Skalds contract is that warnings are
advisory and the human/agent decides (consistent with `next` and the
existing claim warning). Local worktrees and local branches only (remote
branches are out of scope, as they are for claims_elsewhere by default).

## Open questions

- Q1: Should `skald move <id> <active-col>` carry the same warning? cmd_move
  already passes `elsewhere` to `store.update`; confirm whether update
  surfaces it and, if not, whether move should warn too.
- Q2: Board parity — the board already shows a claimed-elsewhere badge;
  confirm the claim action in the dialog surfaces the warning the API returns.

## Acceptance
- [x] `skald claim` (and a move into an active column) warns when the story is active in another local worktree/branch even for the same author, naming the origin branch (one name-agnostic message; branch is the key — see decision note)
- [x] different-author case still warns (name shown inline); no warning when there is genuinely no elsewhere-claim
- [x] warning only (claim still succeeds); local-only
- [x] decision recorded on Q1 (move) and Q2 (board), acted on or deferred with a note
- [x] unit tests: same-author-elsewhere warns, different-author warns, no-collision is silent
- [x] docs updated if behaviour is user-visible (board.md / git-and-ci.md)
- [x] python3 -m unittest green, ruff clean

## Changelog

`skald claim` now warns when a story is already active in another local
working tree or branch, including when the same name is used in both, so
parallel agents do not silently pick up the same story.

## [claude] 2026-09-15 17:24 UTC · decision
Design refinement (from the maintainer): the collision key is (author, from_branch/tree), not author alone. We cannot require distinct agent names, but a git worktree cannot share a branch with another, so the origin branch (or checkout path) always distinguishes two concurrent claimants — even when both are 'claude'.

Implication: the fix is to key the warning on origin, not on name. Warn whenever the story is active in another local worktree/branch, and label it with that origin (e.g. claude@feature-x) so a different-name and a same-name-other-branch collision read differently. author != author gating goes away.

Good news: from_branch is already available on both sides without any storage change — skald claim knows the current branch via gitutil.branch(), and claims_elsewhere() already returns each other-tree claim's {branch, checkout}. The current tree is never in that set, so any entry is a real other-origin claim. So the core fix needs no story-file/frontmatter change.

Open fork for the maintainer (Q3): do we also want to STORE/DISPLAY provenance durably — surface the claim as author@branch on the board badge, in ls, and in the claim note — or is deriving it at warn time enough? Deriving fully closes the reported gap with no format change; storing adds at-a-glance provenance but touches how assignee is shown. Recommend: derive-only core now, treat author@branch display as an optional follow-up.

## [claude] 2026-09-15 17:34 UTC · decision
Built the derive-only core. Implementation and decisions:

- Placed the warning in store.update(), the chokepoint both claim and a move-into-active reach, gated on: elsewhere provided AND the story's resulting status has an active role. Removed the old author-gated loop from store.claim(). So the warning fires on claim, on 'skald move <id> <active-col>', and on a re-claim of an already-active story.
- Q1 (move) RESOLVED: yes, a move into an active column warns too (same code path).
- Q2 (board parity) RESOLVED: the server claim endpoint now computes elsewhere and passes it to store.claim, so the board's Claim button toasts the same warning (frontend already surfaces res.warnings).
- Message: chose ONE name-agnostic template rather than two — 'X is already active as <assignee> on branch <branch>; check it is not being worked in another tree'. The branch is the reliable key; the assignee name is shown inline, so a different-name collision still reads differently without a separate template. This is a deliberate deviation from the acceptance bullet that asked for 'distinct wording'; the single message is simpler and honest about names being unreliable.
- Verified end to end (scratch worktrees): same-author claim warns (was silent), move warns, different-author warns, no-collision silent. Tests: test_store unit, a CLI worktree assertion, and a server-endpoint assertion. 179 tests, ruff clean. Docs: SPEC 4.4, board.md.
