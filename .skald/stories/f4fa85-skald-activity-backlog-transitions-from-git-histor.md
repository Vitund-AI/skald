---
title: "skald activity: backlog transitions from git history"
status: "review"
rank: 290
tags: ["git"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T19:01:43Z"
updated_at: "2026-09-06T19:09:25Z"
---
## Requirements

Every new story, status change, claim, and note between two refs, one line per event with commit, author, and date, so a human can review what agents did overnight.

## [claude] 2026-09-06 19:09 UTC
Implemented: skald activity walks commits touching .skald and reports created, status, assignee, tags, blockers, archived, notes, body edits, and deletions per commit, oldest first; default window 20 commits; --json.
