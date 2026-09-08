---
title: "Link commits to stories with a Skald-Story trailer"
status: "review"
rank: 140
tags: ["git"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T19:01:42Z"
updated_at: "2026-09-08T17:24:21Z"
---
## Requirements

skald commit writes Skald-Story trailers for the stories it touches; the contract tells agents to add the trailer to code commits; skald commits <id> and the History tab list commits referencing a story.

## [claude] 2026-09-06 19:09 UTC
Implemented: skald commit appends Skald-Story trailers for touched stories (--no-trailers to skip); skald commits <id> greps for the trailer or [id]; History tab lists referencing commits above file history; contract tells agents to add the trailer (D35).
