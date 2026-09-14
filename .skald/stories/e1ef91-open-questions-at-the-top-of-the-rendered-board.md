---
title: "Open questions at the top of the rendered board"
status: "done"
rank: 70
tags: ["roadmap"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-14T03:01:20Z"
---
## Requirements

`skald render` writes an "Open questions" section above the columns: story id and title, the question's number and first line, who asked and when. Empty when nothing is waiting.

## Why

Someone reading the repository on GitHub, where the committed `.skald/README.md` is the board, should see what is waiting on a human without running anything. Twenty lines in render.py; the data is `questions_of`.

## [agent] 2026-09-14 03:01 UTC · result
render_markdown now emits an 'Open questions' section right after the intro, above the columns, when any non-archived story has an open question: a table of story link + title, Q<number>: first line, and who asked with the date, read from each story's open_questions(). Omitted entirely when nothing is waiting. So the committed .skald/README.md shows what is waiting on a human to anyone reading the repo on GitHub. HTML render unchanged (the committed board is the markdown). test_render covers the three states (absent with no questions, present and above the columns when one is open, gone again after answer). SPEC 10b, CHANGELOG Unreleased. Suite green, ruff clean.
