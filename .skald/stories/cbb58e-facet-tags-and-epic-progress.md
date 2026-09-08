---
title: "Facet tags and epic progress"
status: "review"
rank: 80
tags: ["core", "ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T17:42:24Z"
updated_at: "2026-09-08T17:24:21Z"
---
## Requirements

Tags of the form key:value are facets. epic:auth is an epic with no schema change, and it works across projects because tags are plain strings.

- [ ] Store.facets(): {key: {value: {total, done, open}}}
- [ ] skald facets [KEY] and skald epics with progress
- [ ] Board: one filter dropdown per facet key, group-by facet swimlanes, epic progress bars
- [ ] ls --all-projects --tag epic:x documented as the cross-repo epic view

## [claude] 2026-09-06 17:49 UTC
Implemented. store.facets groups key:value tags with done/open counts; skald facets [KEY], skald epics, both with --all-projects; board carries facets, shows a filter per facet key and a swimlane control with progress bars; drag works inside lanes. Verified in Chromium. See D28.
