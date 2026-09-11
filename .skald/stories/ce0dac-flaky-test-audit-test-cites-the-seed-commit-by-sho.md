---
title: "Flaky test: audit test cites the seed commit by short sha, which may have no letters"
status: "done"
rank: 40
tags: ["tests"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T21:33:38Z"
updated_at: "2026-09-11T04:55:55Z"
---
## Requirements

The audit extractor ignores digit-only tokens on purpose (numbers are not commits). test_audit_checks_and_notes cites the seed commit by its 7-character short sha; about one run in 27 the short sha has no letter and the test fails on the commit count. Cite the full sha instead. The ResourceWarning about a running subprocess seen in the same runs is the server start handing off its child, and is unrelated.

## [claude] 2026-09-10 21:39 UTC · result
The extractor drops digit-only tokens on purpose; test_audit cites the full sha now. Reproduced before the fix in 2 of 6 full runs and by crafting a commit whose short sha was 6543063. The ResourceWarning the reviewer saw is the server start handing off its child and is unrelated.
