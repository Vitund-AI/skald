---
title: "Open questions at the top of the rendered board"
status: "idea"
rank: 50
tags: ["roadmap"]
blocked_by: []
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-12T20:39:49Z"
---
## Requirements

`skald render` writes an "Open questions" section above the columns: story id and title, the question's number and first line, who asked and when. Empty when nothing is waiting.

## Why

Someone reading the repository on GitHub, where the committed `.skald/README.md` is the board, should see what is waiting on a human without running anything. Twenty lines in render.py; the data is `questions_of`.
