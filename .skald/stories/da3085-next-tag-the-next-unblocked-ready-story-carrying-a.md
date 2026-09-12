---
title: "next --tag: the next unblocked ready story carrying a tag"
status: "done"
rank: 20
tags: ["cli"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-12T03:22:00Z"
updated_at: "2026-09-12T05:25:14Z"
---
## Requirements

ls filters by tag; next cannot, so an executive loop cannot ask for the next ready story for a given kind of agent in one call.

- [x] skald next --tag TAG (facets such as effort:deep work) picks among ready stories carrying the tag, with the same rank, dependency, lane, and assignee rules
- [x] MCP skald_next takes tag
- [x] tests; cli.md, SPEC row, CHANGELOG

## [claude] 2026-09-12 03:27 UTC · result
next_story(tag=) filters ready stories to those carrying the tag (case-insensitive) before the dependency, claim, lane, and assignee rules; CLI next --tag and MCP skald_next tag; stderr says 'tagged X' when none. Tests in store, CLI, MCP. cli.md, SPEC row, CHANGELOG.
