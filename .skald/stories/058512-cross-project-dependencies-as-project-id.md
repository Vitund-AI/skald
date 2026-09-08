---
title: "Cross-project dependencies as project:id"
status: "done"
rank: 40
tags: ["core"]
blocked_by: []
created_at: "2026-09-06T07:04:41Z"
updated_at: "2026-09-08T17:24:16Z"
---
## Requirements

A blocked_by entry may name another registered project. Unregistered projects resolve as unavailable (unmet, warning); missing stories in registered projects are problems.

## [claude] 2026-09-06 07:04 UTC
Implemented in Store.dep_states. Board shows dependency chips that open the target and switch project. See D19.
