---
title: "Target-release tag and a release warning"
status: "idea"
rank: 20
tags: ["roadmap"]
blocked_by: []
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-12T20:39:49Z"
---
## Requirements

A `release:0.6` facet on stories marks what a release should carry. `skald release 0.6.0 --dry-run` (and the real run) warns about stories tagged for that release that are not in done, and the board filters on the facet like any other. No new field.

## Why

Planning a release is a filter on the board and a check at the end. The facet machinery (epic:, lane:) already does the filtering; only the warning in release.plan is new. Document beside the other conventions.
