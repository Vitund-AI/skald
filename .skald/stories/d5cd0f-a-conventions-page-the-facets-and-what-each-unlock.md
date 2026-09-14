---
title: "A conventions page: the facets and what each unlocks"
status: "done"
rank: 80
tags: ["docs", "roadmap"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-14T03:02:41Z"
---
## Requirements

One page under docs/ listing the tag conventions that grew this week and what each one turns on: `epic:` (grouping and swimlanes), `lane:` (mutual exclusion with facet_limits), `effort:` (routing with next --tag), `area:` (from import), `release:` (once the target-release story lands). For each: the tag, the command or board feature that reads it, and when to use it. Linked from stories.md and the README docs table.

## Why

Every one of these was invented on demand and lives in a different document. Without a line of code, a page turns them from tribal knowledge into features a new adopter can find.

## [agent] 2026-09-14 03:02 UTC · result
Added docs/conventions.md: a table of the facet tags (epic:, lane:, effort:, area:, release:) with what reads each (skald epics / ls --tag; facet_limits + status + next for lanes; next --tag and the model-routing example for effort; import for area; skald release for release:) and when to use it, plus a note on model: as a convention (D61), a 'make a facet a lane' snippet, and an 'invent your own' section. Linked from the README docs table, docs/README.md, and the stories.md facets section; cross-links to the model-routing example, DECISIONS D61, and stories.md#lanes all resolve. Docs only. CHANGELOG Unreleased.
