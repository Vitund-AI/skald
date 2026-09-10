---
title: "Git integration: status, commit, log, changelog, board commit button"
status: "done"
rank: 440
tags: ["git", "ui"]
blocked_by: []
created_at: "2026-09-06T07:04:41Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

skald status shows uncommitted story files; skald commit stages only .skald/; the board shows a Commit N changes button; push is opt-in via skald config push true.

## Changelog

`skald status` shows uncommitted story files, `skald commit` stages only `.skald/`, the board has a Commit button for changed story files, and pushing from the board is opt-in with `skald config push true`.

## [claude] 2026-09-06 07:04 UTC
Implemented (D12, D21). changelog compares frontmatter at two refs and handles archived files.
