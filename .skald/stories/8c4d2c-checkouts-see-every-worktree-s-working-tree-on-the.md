---
title: "Checkouts: see every worktree's working tree on the board, claims visible before commit"
status: "done"
rank: 340
tags: ["agents", "core", "ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-09T23:42:51Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

A project keeps one name. A second checkout of the same repository (a git worktree, or a separate clone) today replaces the registered path every time a command runs there, and the board's branch views read committed objects only, so an agent mid-task in a worktree is invisible until it commits. Parallel agents in worktrees are the main reason for a second checkout.

- The registry keeps one primary path per name plus a list of other checkouts. Running skald in another checkout while the primary still exists records it as a checkout and says so; the path only moves when the old one is gone. skald projects use makes the current checkout the primary.
- Git worktrees of the primary are discovered from git worktree list without registration. Checkouts whose directory has gone are dropped.
- Board: the Branch dropdown gains a Checkouts group; choosing one shows that checkout's working tree, editable, with a banner naming path and branch and a marker for uncommitted story files. Writes and the commit button act on that checkout. Every project route accepts ?checkout=ID; ids are opaque, never paths. GET /api/projects/<p>/checkouts lists them.
- skald projects lists checkouts under each project with branch and dirty count.
- skald context, next, and claim count claims in other checkouts' working trees as claims elsewhere, so two agents in worktrees cannot both take a story before either commits. A checkout's working tree replaces the committed view of its branch, so nothing is counted twice.
- README comparison row for work in progress across worktrees.

## Changelog

A project with several working trees on one machine keeps one primary and knows the others: git worktrees are discovered automatically and a second clone is recorded when a command runs there, without replacing the primary. The board's branch dropdown lists every working tree and shows the chosen one, uncommitted changes included and editable; `skald projects` lists checkouts and `skald projects use` picks the primary; `next`, `claim`, and `context` see claims made in other checkouts before they are committed.

## Acceptance
- [x] A second checkout does not replace the primary; a moved repository still does; projects use switches
- [x] Worktrees appear without registration; missing checkouts disappear
- [x] Board: checkout group in the dropdown, editable view with banner, writes land in that checkout
- [x] API: /checkouts endpoint, ?checkout=ID on project routes, unknown id is 404
- [x] CLI: projects lists checkouts; context/next/claim see uncommitted claims in other checkouts
- [x] Docs: multi-project, board, working-with-agents, api, troubleshooting, README row, SPEC, CHANGELOG, DECISIONS

## [claude] 2026-09-09 23:51 UTC · result
Registry keeps a primary plus recorded checkouts and discovers git worktrees; a second checkout no longer replaces the primary (notice printed; moved repo still takes over; skald projects use switches). Board: Working trees group in the branch dropdown, editable view with amber banner, ?checkout=ID on every project route incl. the event stream, id kept in the URL across reloads. GET /checkouts endpoint. skald projects lists checkouts with branch and dirty count. next/claim/context read other working trees; a working tree stands in for its branch so claims are not double counted. Verified: 127 unit tests; Playwright against a clone plus worktree with an uncommitted claim (dropdown groups, badge on the primary, banner and editable cards in the worktree, selection survives reload). Docs: multi-project, board, working-with-agents, api, troubleshooting, README row, SPEC 2.3/2.4/4.6/6/8, CHANGELOG, D49.
