---
title: "context caps Waiting on a human at five stories"
status: "done"
rank: 30
tags: ["agents"]
blocked_by: []
assignee: "claude"
released: "0.4.0"
created_at: "2026-09-10T18:21:55Z"
updated_at: "2026-09-10T20:18:46Z"
---
## Requirements

The section listed every story with an open question. On a backlog with 63 such stories the SessionStart hook would inject about 130 lines on every start, the failure D50 fixed for ls, one level up. From the 0.3.0 adoption review (finding 3). The section now shows at most five stories, newest question first, and ends with '... and N more: skald ls --questions'; JSON carries waiting (capped) and waiting_more.

## Changelog

`skald context` lists at most five stories under Waiting on a human and says how many more there are; `skald ls --questions` has the full list.

## Acceptance
- [x] Text and JSON capped at five with the remainder counted
- [x] Test; SPEC 6 context row; docs

## [claude] 2026-09-10 18:26 UTC · result
WAITING_CAP = 5: newest question first, waiting_more in JSON, '... and N more: skald ls --questions' in text. Test with seven waiting stories.
