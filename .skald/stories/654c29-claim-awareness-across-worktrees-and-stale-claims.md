---
title: "Claim awareness across worktrees and stale claims"
status: "review"
rank: 130
tags: ["agents", "core"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T19:01:42Z"
updated_at: "2026-09-08T17:24:21Z"
---
## Requirements

next skips and claim warns about stories claimed by someone else on another local branch, using branch snapshots. Claims on active stories untouched for stale_days count as free again, with a warning.

## [claude] 2026-09-06 19:06 UTC
Implemented: Store.claims_elsewhere from local branch snapshots; next skips other agents' claims with a warning and offers stale assignments back (D33, D34); claim warns on takeover and on claims elsewhere; branches endpoint returns claims and cards show an also-claimed badge.
