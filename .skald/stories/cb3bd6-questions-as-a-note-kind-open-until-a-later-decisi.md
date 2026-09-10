---
title: "Questions as a note kind: open until a later decision, surfaced in context, resume, ls, and the board with a waiting-on-a-human filter"
status: "review"
rank: 50
tags: ["agents", "core", "ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T05:09:37Z"
updated_at: "2026-09-10T05:22:05Z"
---
## Requirements

A third of the design records carry a question only the owner can answer, invisible until an agent rereads the body. Skald has no way to say these stories are waiting on a human, which is the single most useful thing a board can tell the human. From the design-record feature request (item 1), plus the board filter.

- note --kind question is open until a later decision note on the same story (deliberately coarse; a decision naming its question is a later refinement).
- skald answer <id> text [--as NAME] is sugar for note --kind decision.
- Story.open_questions(); story_dict gains questions {open: N} compact, the list in full.
- context gains Waiting on a human after Ready but blocked: every story with open questions, not filtered to the actor.
- resume prints open questions after Decisions and before the latest handoff.
- ls: a narrow Q column (not overloading BLOCKED); --questions filters.
- Board: count badge on the card, a Waiting on a human filter (and swimlane option), and an Answer button in the modal writing a decision note as the board identity.
- MCP: skald_answer; context and resume carry the lists.
- Docs: AGENTS template step 5 (use --kind question for what only the human can decide, keep working on what does not depend on it), stories.md, working-with-agents.md, board.md, SPEC 4.3, cli.md, CHANGELOG, DECISIONS (why a note, not a section).

## Acceptance
- [x] Open and closed by note ordering
- [x] context, resume, ls output and --questions
- [x] Board badge, filter, Answer button writes a decision note under the board identity
- [x] MCP answer tool; docs synced

## [claude] 2026-09-10 05:22 UTC · result
open_questions: a question note is open until a later decision note. story_dict carries questions {open} (+items when not compact). skald answer = note --kind decision with a closed count. context: Waiting on a human section (all stories, JSON key waiting); resume: Open questions after Decisions; ls: Q column with ?N and --questions. Board: amber ? N badge, a Waiting on a human toggle with the count, the modal lists open questions and an Answer button posts a decision note as the board identity; the notes endpoint now honours kind as api.md already said. MCP: skald_answer, waiting and open_questions. Verified in a browser end to end. Docs: AGENTS step 5 and copies, stories.md, working-with-agents, board.md, SPEC 4.3 and 6, cli.md, CHANGELOG, D54. 130 tests pass.
