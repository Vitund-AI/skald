---
title: "Questions as a note kind: open until a later decision, surfaced in context, resume, ls, and the board with a waiting-on-a-human filter"
status: "ready"
rank: 20
tags: ["agents", "core", "ui"]
blocked_by: []
created_at: "2026-09-10T05:09:37Z"
updated_at: "2026-09-10T05:09:38Z"
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
- [ ] Open and closed by note ordering
- [ ] context, resume, ls output and --questions
- [ ] Board badge, filter, Answer button writes a decision note under the board identity
- [ ] MCP answer tool; docs synced
