---
title: "Story references in notes resolve on the board and in show"
status: "idea"
rank: 40
tags: ["roadmap"]
blocked_by: []
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-12T20:39:49Z"
---
## Requirements

A story id in note text (`a3f9c2`, or `#a3f9c2`, or `project:a3f9c2`) becomes a link on the board that opens that story, and `skald show` and `resume` render it with the title beside it when it resolves. The file format is unchanged: agents already write ids into notes by hand.

## Why

Handoffs and decisions cite other stories constantly; making the citation navigable costs a regular expression in the board and a lookup in the CLI.
