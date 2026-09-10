---
title: "Board: checklist progress, stale marker, branch, history tab, keyboard shortcuts"
status: "done"
rank: 90
tags: ["ui"]
blocked_by: []
created_at: "2026-09-06T07:04:41Z"
updated_at: "2026-09-08T17:24:16Z"
---
## Requirements

Cards show task-list progress and a stale marker for active stories untouched for stale_days. Header shows the git branch. Modal has a History tab from git log. n, /, Esc shortcuts.

## Changelog

Cards show checklist progress and mark active stories untouched for `stale_days`; the header shows the git branch; the story dialog has a History tab from git log; `n`, `/`, and `Esc` are keyboard shortcuts.

## [claude] 2026-09-06 07:04 UTC
Implemented. Polling uses a version hash endpoint so the board only refetches on change (D14).
