---
title: "Cross-project dependencies as project:id"
status: "done"
rank: 30
tags: ["core"]
blocked_by: []
created_at: "2026-09-06T07:04:41Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

A blocked_by entry may name another registered project. Unregistered projects resolve as unavailable (unmet, warning); missing stories in registered projects are problems.

## Changelog

A `blocked_by` entry can name a story in another registered project as `project:id`. It resolves through the machine-local index; a project not registered here counts as unmet with a warning rather than an error.

## [claude] 2026-09-06 07:04 UTC
Implemented in Store.dep_states. Board shows dependency chips that open the target and switch project. See D19.
