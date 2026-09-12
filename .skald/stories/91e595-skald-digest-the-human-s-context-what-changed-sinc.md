---
title: "skald digest: the human's context, what changed since you last looked"
status: "idea"
rank: 10
tags: ["roadmap"]
blocked_by: []
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-12T20:39:49Z"
---
## Requirements

The agent gets one block on session start; the human gets the board and nothing else. `skald digest [--since 1d|REF]` assembles the morning check-in: stories moved, notes written, questions asked, grouped by story, newest first, from git history (`activity` has the events) and the notes (`resume` reads them). Bounded like `context`: a cap per section and a pointer to the full command.

## Why

Every review this week came from a human reading story files by hand to find out what an agent did overnight. No new data is needed; the two sources exist.
