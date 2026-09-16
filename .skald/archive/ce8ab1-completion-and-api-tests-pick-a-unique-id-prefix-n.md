---
title: "Completion and API tests pick a unique id prefix, not a fixed slice"
status: "done"
rank: 10
tags: ["tests"]
blocked_by: []
assignee: "claude"
released: "0.8.0"
created_at: "2026-09-14T15:49:21Z"
updated_at: "2026-09-16T07:11:46Z"
---
## Requirements

- [x] test_completion sliced `id[:2]` and test_server `id[:4]`, which collide when random ids share those leading hex; the v0.7.0 publish run failed this way. Use the `prefix()` helper (shortest prefix, min 3 chars, unique among the others) so both are deterministic.

## Why

A flaky test can fail a release: the publish workflow runs the suite from the tag. The helper already existed for the same class of bug elsewhere.
