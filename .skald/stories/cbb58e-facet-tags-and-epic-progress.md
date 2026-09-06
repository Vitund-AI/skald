---
title: "Facet tags and epic progress"
status: "in_progress"
rank: 20
tags: ["core", "ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T17:42:24Z"
updated_at: "2026-09-06T17:46:52Z"
---
## Requirements

Tags of the form key:value are facets. epic:auth is an epic with no schema change, and it works across projects because tags are plain strings.

- [ ] Store.facets(): {key: {value: {total, done, open}}}
- [ ] skald facets [KEY] and skald epics with progress
- [ ] Board: one filter dropdown per facet key, group-by facet swimlanes, epic progress bars
- [ ] ls --all-projects --tag epic:x documented as the cross-repo epic view
