---
title: "skald diff between refs and a PR comment from the workflow"
status: "review"
rank: 280
tags: ["docs", "git"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T19:01:43Z"
updated_at: "2026-09-06T19:09:25Z"
---
## Requirements

New, moved, claimed, and archived stories between two refs, as text, JSON, or Markdown. The GitHub workflow upserts the Markdown as a comment on pull requests.

## [claude] 2026-09-06 19:09 UTC
Implemented: diff_states in the store; skald diff --since REF [--until REF] as text, JSON, or Markdown with a <!-- skald-diff --> marker; the generated workflow gains a diff job that upserts the comment on pull requests (D36).
