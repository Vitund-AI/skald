---
title: "Story references in notes resolve on the board and in show"
status: "done"
rank: 20
tags: ["roadmap"]
blocked_by: []
assignee: "claude"
released: "0.7.0"
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-14T15:24:52Z"
---
## Requirements

A story id in note text (`a3f9c2`, or `#a3f9c2`, or `project:a3f9c2`) becomes a link on the board that opens that story, and `skald show` and `resume` render it with the title beside it when it resolves. The file format is unchanged: agents already write ids into notes by hand.

## Why

Handoffs and decisions cite other stories constantly; making the citation navigable costs a regular expression in the board and a lookup in the CLI.

## [agent] 2026-09-13 22:46 UTC · result
CLI: annotate_refs(text, index) puts '(Title)' beside every id in text that resolves in the store index (includes archived). REF_IN_TEXT matches a bare 6-hex, #-prefixed, or project:id, with boundaries that skip a longer hex run (a sha) or a slug; a title already following (' (') is not doubled. Wired into cmd_show (non-JSON body only; --json stays raw) and cmd_resume (latest note/handoff and decision lines). Board: linkifyRefs walks the rendered text nodes (skipping a, code, pre, existing refs), wraps each resolving id in a span.ref with a title tooltip, and wires a click that opens it, switching project for project:id; a bare id links only when it is on the current board so a stray hex is left alone. CSS .ref styled as an accent mono link. Verified: unit test in test_cli (bare, #, project: forms annotate; stray hex plain; --json untouched; no doubling) and a headless-browser pass (3 ref spans, tooltip, stray hex not linked, click opens the target, no page errors). Docs: SPEC board dialog + resume/show rows, docs/board.md, docs/stories.md notes, CHANGELOG Unreleased. Suite 157 green, ruff clean.
