---
title: "Custom columns with roles and WIP limits"
status: "done"
rank: 20
tags: ["core", "ui"]
blocked_by: []
released: "0.2.0"
created_at: "2026-09-06T07:04:41Z"
updated_at: "2026-09-10T00:56:31Z"
---
## Requirements

Projects define columns in config.json with roles backlog/ready/active/done/closed and optional limits. Unknown statuses show in an Unknown column and are reported by check.

## Changelog

Columns are defined per project in `config.json` with roles (backlog, ready, active, done, closed) and optional WIP limits. A story with an unknown status shows in an Unknown column and is reported by `skald check`.

## [claude] 2026-09-06 07:04 UTC
Implemented (D16, D17, D18). Closed blockers satisfy with a warning. Over-limit columns warn on mv and show red on the board.
