---
title: "Add an optional assignee field for multi-agent setups"
status: "done"
rank: 150
tags: ["cli", "ui"]
blocked_by: []
created_at: "2026-09-06T02:16:15Z"
updated_at: "2026-09-08T17:24:16Z"
---
## Requirements

When several agents work one repository they need to avoid claiming the same story. Add an optional `assignee` string, let `next` skip stories assigned to someone else, and show it on cards.

## Changelog

Stories have an optional `assignee`. `skald next` skips stories assigned to someone else and cards show who holds them, so several agents can share one repository.

## [claude] 2026-09-06 07:04 UTC
Implemented: assignee field (omitted when empty), skald claim <id> --as NAME, skald next --as NAME skips stories assigned to others, ls --assignee, Claim button on the board.
