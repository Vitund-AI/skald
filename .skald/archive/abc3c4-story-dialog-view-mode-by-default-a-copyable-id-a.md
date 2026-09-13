---
title: "Story dialog: view mode by default, a copyable id, a deep link"
status: "done"
rank: 80
tags: ["board"]
blocked_by: []
assignee: "claude"
released: "0.6.0"
created_at: "2026-09-13T18:25:53Z"
updated_at: "2026-09-13T21:49:59Z"
---
## Requirements

- [x] header: the id, larger, top left; click copies it, shift-click copies project:id; created and updated beside it; the title as a heading on the second line; the project name and filename go
- [x] an existing story opens in view mode: status, assignee, tags, blockers, and family as chips, the body rendered as Markdown, the questions and the note box below; Edit (button and the e key) switches to the form; Save returns to view; Esc in edit mode cancels; a new story opens in edit mode; read-only views never edit
- [x] the URL carries #story=ID while a story is open, and opening the board with that hash opens the story
- [x] docs/board.md, the shortcuts panel, story.png retaken, CHANGELOG

## [agent] 2026-09-13 18:38 UTC · result
Header: #m-id (mono, larger) with created and updated beside it and the title as a heading; the project name and filename are gone. View mode by default: quick status select, assignee, tag chips, claim, dependency chips, family, body rendered by marked with note headings set apart (.md h2.note, kind in the accent), questions, add-a-note. Edit button and e switch to the form; Save and Cancel return to view; Esc leaves edit mode first, then closes; a new story opens in the form; read-only refs hide Edit and disable the quick select. Click on the id copies it, shift-click copies project:id (clipboard API with an execCommand fallback). The hash carries #story=ID while open and is cleared on close; establishSession keeps it when it drops #key=, and loadProjects now resolves after the first board fetch so the deep link opens with the columns known (the quick select previously read 'in_progress (unknown)'). Playwright pass in the sandbox: deep link, copy, e/Esc, save, quick move, close, no page errors. SPEC section 8, docs/board.md dialog section and shortcuts table, the help panel, story.png retaken in the dark theme, CHANGELOG.
