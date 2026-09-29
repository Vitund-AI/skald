---
title: "Close the linked GitHub issue when its story ships"
status: "idea"
rank: 80
tags: ["epic:integrations", "examples", "roadmap"]
blocked_by: ["b56d9e"]
created_at: "2026-09-29T01:17:37Z"
updated_at: "2026-09-29T01:17:37Z"
---
## Requirements

The one write-back from Skald to GitHub that avoids the problems of two-way
sync: when a story tagged `gh:<number>` (from the b56d9e sync) is released,
close that issue with a comment linking the release, e.g. "Shipped in
v0.9.0 (story a3f9c2)". One direction, so there is nothing to conflict.

Open questions before planning:
- Where it runs: a step in the example script (`--close-shipped`), a hook on
  `skald release`, or a CI job on the release tag. The CI job keeps the write
  token out of agent sessions.
- Idempotency: skip issues already closed; never comment twice.
- Needs a token with issues:write, so it stays opt-in and outside the core.

## Why

What people want from "sync back" is mostly that the issue closes when the
work ships. This gets that without the conflict resolution, status mapping,
and comment echo that full two-way sync would need.
