---
title: "Stop flagging open questions after an unrelated decision"
status: "done"
rank: 40
tags: ["agents", "area:cli", "bug"]
blocked_by: []
assignee: "claude"
released: "1.3.0"
created_at: "2026-10-17T05:10:34Z"
updated_at: "2026-10-17T07:42:11Z"
---
## Requirements

From agent feedback (parallel worktree agents, 2026-10-17). A story with six open questions and one unrelated (scheduling) decision made `skald check` warn "Q1…Q6 open again". The questions were correctly open: since 0.4.1 a decision closes only the questions it names. The warning is a 0.4.1 migration aid that now fires on new stories too. The agent's only way to silence it was to withdraw the questions and re-ask them as one, losing their numbering.

## Acceptance
- [x] The warning fires only when the plain decision predates 0.4.1 (2026-09-10), the case it was written for.
- [x] A question followed by an unrelated decision written since then raises no warning and stays open.

## [claude] 2026-10-17 05:17 UTC · handoff
Done: reopened_questions counts only plain decisions stamped before QUESTION_RULE_SINCE (2026-09-10, 0.4.1). Test: a now-dated unrelated decision leaves both questions open, numbered, and check silent; a backdated pre-0.4.1 decision still earns 'Q1 open again'. D54 addendum, SPEC check row.
