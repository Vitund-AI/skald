---
title: "skald check: print problems to stderr so a blocking Stop hook shows why"
status: "done"
rank: 20
tags: ["agents", "area:cli", "bug"]
blocked_by: []
assignee: "claude"
released: "1.3.0"
created_at: "2026-10-17T05:10:34Z"
updated_at: "2026-10-17T07:42:11Z"
---
## Requirements

From agent feedback (parallel worktree agents, 2026-10-17). `skald check` exits 2 on a problem, which blocks a Claude Code Stop hook, but it prints `PROBLEM:` lines to stdout. The hook shows only stderr, so the agent saw "No stderr output" six times without the reason.

## Acceptance
- [x] `PROBLEM:` lines go to stderr, like `WARNING:` lines already do; `ok` stays on stdout; `--json` is unchanged.

## [claude] 2026-10-17 05:17 UTC · handoff
Done: PROBLEM lines, including the --hook uncommitted-files one, go to stderr; ok stays on stdout; --json unchanged. Every consumer (release script, generated CI, hooks) reads the exit code only. Tests now assert stderr and an empty stdout. SPEC check row says why.
