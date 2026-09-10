---
title: "Review notes: resume map one heading per line, answer --question N"
status: "done"
rank: 50
tags: ["agents", "cli"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T18:21:55Z"
updated_at: "2026-09-10T20:18:26Z"
---
## Requirements

From the 0.3.0 adoption review notes. The section map in resume is one long line when a record has many headings: above four sections it becomes one heading per line. The coarse closing rule (D54) will bite on design records where a decision about one thing closes a question about another: skald answer --question N closes only the Nth open question, by writing the decision with a first line naming the question it answers, and open_questions honours that.

## Changelog

`skald resume` lists a long section map one heading per line, and `skald answer --question N` closes only the Nth open question instead of all of them.

## Acceptance
- [x] Map wraps above four sections
- [x] answer --question N; a targeted decision leaves the other questions open; test; docs; D54 amended

## [claude] 2026-09-10 18:26 UTC · result
resume map wraps one heading per line above four sections; resume numbers open questions; answer --question N (CLI and MCP) writes 'Answers [author] stamp · first line' as the decision's first line and open_questions closes only that question (author, stamp, and first line, since two questions can share a minute). D54 addendum. Tests on the CLI and MCP.
