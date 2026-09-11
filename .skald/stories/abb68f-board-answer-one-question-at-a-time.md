---
title: "Board: answer one question at a time"
status: "review"
rank: 30
tags: ["board"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T23:22:11Z"
updated_at: "2026-09-10T23:26:17Z"
---
## Requirements

The modal's Answer button posts a plain decision note, which closes every open question. The CLI already targets one with 'answer --question N'.

- [x] each open question in the modal has its own Answer button; selecting one highlights it and relabels the send button 'Answer question N'; with none selected the button reads 'Answer all' and behaves as today
- [x] POST /stories/ID/notes takes an optional 'question' index (1-based over the open questions) and writes the same targeted decision the CLI writes, from one place in the store
- [x] docs: board.md, api.md, CHANGELOG; tests on the server and the store

## [claude] 2026-09-10 23:26 UTC · result
Store.answer(ref, text, author, question) is the one place the targeted first line is written; CLI answer, MCP skald_answer, and POST /notes with 'question' call it. The dialog numbers the open questions, each with an Answer button that selects it (Selected), relabels the send button 'Answer question N' and the note placeholder, and posts the decision with question=N; with none selected the button reads 'Answer all' when there is more than one. Verified in Chromium against a fixture project: two questions, select 2, reply, one remains and the story carries 'Answers [claude] stamp · And the host?'. Tests on the server (targeted answer, bad index, wrong kind, non-integer). Docs: board.md, api.md, SPEC, CHANGELOG. 151 tests pass.
