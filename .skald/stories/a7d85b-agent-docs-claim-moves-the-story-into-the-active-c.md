---
title: "Agent docs: claim moves the story into the active column; new --body - reads stdin"
status: "review"
rank: 40
tags: ["agents", "docs"]
blocked_by: []
assignee: "claude"
created_at: "2026-10-17T05:10:35Z"
updated_at: "2026-10-17T05:17:30Z"
---
## Requirements

From agent feedback (parallel worktree agents, 2026-10-17). Two surprises that are the design, not bugs: `skald claim` moves a story into the first active column (that is how the board and `skald next` see it as taken), so its rank becomes its place in the new column; and `skald new --body -` already reads the body from stdin, which avoids shell quoting for long bodies. The contract should say both.

## Acceptance
- [x] The agent contract and docs say what claim changes and show `--body -` with a pipe.

## [claude] 2026-10-17 05:17 UTC · handoff
Done: contract step 3 says claim moves the story into the first active column (how others see it as taken) so rank becomes its place there; step 6 shows cat body.md | skald new "title" --body -. Template and both copies updated; doctor confirms they match.
