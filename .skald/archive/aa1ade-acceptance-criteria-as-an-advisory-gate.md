---
title: "Acceptance criteria as an advisory gate"
status: "done"
rank: 140
tags: ["core"]
blocked_by: []
assignee: "claude"
released: "0.2.0"
created_at: "2026-09-06T19:01:43Z"
updated_at: "2026-09-10T00:56:31Z"
---
## Requirements

A ## Acceptance checklist in the body; moving forward past the first active column or into done warns when items are unchecked; the board shows acceptance progress.

## Changelog

A `## Acceptance` checklist in the body is an advisory gate: moving a story past the first active column or into done warns while items are unchecked, and the board shows acceptance progress on the card.

## [claude] 2026-09-06 19:06 UTC
Implemented: acceptance_progress reads a ## Acceptance checklist; update warns on moves into terminal columns or forward past the first active column (D32); story dicts carry acceptance; context and resume show it.
