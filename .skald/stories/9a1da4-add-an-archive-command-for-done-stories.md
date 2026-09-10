---
title: "Add an archive command for done stories"
status: "done"
rank: 460
tags: ["cli"]
blocked_by: []
created_at: "2026-09-06T02:16:15Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

`skald archive` moves every `done` story into `.skald/archive/` so the board and `ls --all` stay small on long-lived repositories. Archived stories should still satisfy `blocked_by` links as done. Decide whether `show` can read archived stories by id.

## Changelog

`skald archive` moves done and closed stories into `.skald/archive/` so the board and listings stay small; archived stories still satisfy `blocked_by` links and `skald unarchive` brings one back.

## [claude] 2026-09-06 07:04 UTC
Implemented: skald archive [--dry-run], skald unarchive <id>, ls --archived. Archived stories still resolve by id, satisfy dependencies, and appear in changelog; they cannot be edited until unarchived (DECISIONS.md D20).
