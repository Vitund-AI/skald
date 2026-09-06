---
title: "Add an archive command for done stories"
status: "backlog"
rank: 20
tags: ["cli"]
blocked_by: []
created_at: "2026-09-06T02:16:15Z"
updated_at: "2026-09-06T02:16:15Z"
---
## Requirements

`skald archive` moves every `done` story into `.skald/archive/` so the board and `ls --all` stay small on long-lived repositories. Archived stories should still satisfy `blocked_by` links as done. Decide whether `show` can read archived stories by id.
