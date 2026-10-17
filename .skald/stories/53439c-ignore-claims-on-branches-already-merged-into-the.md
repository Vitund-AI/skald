---
title: "Ignore claims on branches already merged into the current branch"
status: "review"
rank: 20
tags: ["agents", "area:git", "bug"]
blocked_by: []
assignee: "claude"
created_at: "2026-10-17T05:10:34Z"
updated_at: "2026-10-17T05:17:29Z"
---
## Requirements

From agent feedback (parallel worktree agents, 2026-10-17). After merging the agents' work, `skald move` and `claim` kept warning that stories were "already active as claude on branch worktree-agent-…", naming branches whose commits were already merged.

## Acceptance
- [x] A branch whose tip is an ancestor of the current HEAD contributes no claims.
- [x] A worktree on such a branch contributes no claims unless its `.skald/` has uncommitted changes (an unmerged claim made since).
- [x] Unmerged branches and dirty worktrees are reported as before.

## [claude] 2026-10-17 05:17 UTC · handoff
Done: gitutil.is_merged (merge-base --is-ancestor). _claims_elsewhere skips a merged branch, and a worktree whose HEAD is merged unless git status shows changes under its .skald/ (store._dirty, True on doubt). Tests: claim on agent/two warns, then after merging it, nothing; a worktree claim committed and merged disappears, a new uncommitted claim there reappears. SPEC 4.6 paragraph updated.
