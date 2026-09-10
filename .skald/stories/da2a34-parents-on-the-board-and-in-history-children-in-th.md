---
title: "Parents on the board and in history: children in the modal, epics merge, commits union"
status: "done"
rank: 120
tags: ["git", "ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T05:09:38Z"
updated_at: "2026-09-10T18:04:04Z"
---
## Requirements

Second stage of parents, after children exist in practice. Board: parent card shows children progress; modal lists children with status and a new-child button; swimlanes can split by parent. skald epics lists structural parents merged with the epic: facet. commits <id> on a parent unions the children's commits (--no-children turns it off), so the hand-maintained piece table becomes derived.

## Acceptance
- [x] Board children progress, modal list, new child
- [x] epics merge; commits union with trailers on a temp repo

## [claude] 2026-09-10 06:19 UTC · result
Board: parent card shows children done/total with a bar; the dialog has a Parent field, a chip for the parent, chips for the children (struck through when done) and a + child button that opens a new story with the parent set; the History tab unions the children's commits, tagged; swimlanes by parent. API: create takes parent and inherit, patch takes parent, a story returns children and parent_story, history unions children unless ?children=0. CLI: skald epics lists structural parents titled with children counts beside the epic: facet; skald commits <parent> unions the children's commits via gitutil.commits_for_family, tagged, --no-children turns it off. Verified in a browser: badge, chips, + child creating a real child, history heading, lanes. Docs: stories.md, board.md, api.md, SPEC 4.4/6/8, CHANGELOG, D59. 141 tests pass.
