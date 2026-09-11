---
title: "Questions close only when a decision names them; stable Q-numbers; --all and --withdraw"
status: "review"
rank: 40
tags: ["questions"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-11T05:09:11Z"
updated_at: "2026-09-11T05:17:19Z"
---
## Requirements

The coarse rule from D54 (any decision closes every earlier question) bit twice on the first real design story. Closing becomes explicit.

- [x] a decision note closes nothing; a question closes only when a decision's first line names it (Answers or Withdraws, author + stamp + first line; Q-label is display only)
- [x] questions are numbered by order of appearance (Q1, Q2, ...), stable for the story's life; resume, ls, context, and the board show the label; --question takes 3 or Q3
- [x] answer: --question N closes one; with exactly one open and no --question it defaults to it; several open refuses; none open refuses and points at note --kind decision; --all sweeps and prints what it closed; --withdraw records a drop rather than an answer
- [x] resume lists closed questions with the decision that closed them
- [x] check notices stories whose questions reopened under the new rule
- [x] MCP skald_answer and POST /notes: question (number or label), all, withdraw; board: per-question buttons carry Q-labels, Answer all sends all
- [x] docs: stories.md, working-with-agents.md, board.md, api.md, cli.md, SPEC, AGENTS template and copies, CHANGELOG, D54 addendum

## [claude] 2026-09-11 05:17 UTC · result
store: questions_of numbers questions by appearance and records closed_by (how: answered/withdrawn) from a decision's leading Answers/Withdraws lines; open_questions derives from it; a plain decision closes nothing; reopened_questions feeds a check warning per story. Store.answer: --question (3 or Q3), default to the one open question, refuse on several or none, --all, --withdraw. CLI answer prints 'answered Q2 on ID (decision; 1 still open)'; context shows Q-numbers; resume labels open questions and lists the last five closed with what closed them. MCP skald_answer and POST /notes take question (number or label), all, withdraw. Board labels Q1.. and Answer all sends all. Verified in Chromium: plain decision left 3 open, Answer beside Q2 closed only Q2, Answer all closed Q1 and Q3 with one naming line each. Docs: stories.md, working-with-agents.md, board.md, api.md, cli.md, SPEC 4 and 6, AGENTS template and copies (rule and command table), CHANGELOG, D54 second addendum. 150 tests pass.
