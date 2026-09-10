---
title: "Changelog text on every story before the 0.2.0 release"
status: "done"
rank: 370
tags: ["docs"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T00:45:17Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

skald release reads each story's ## Changelog section and falls back to the title. 45 stories in done and review had no section, so the 0.2.0 changelog would have been a list of titles. Each now carries a one- or two-sentence user-facing entry.

## Changelog

Every story that ships in 0.2.0 carries a user-facing changelog entry, so the generated release section reads as release notes rather than a list of titles.

## Acceptance
- [x] Every story in done or review has a ## Changelog section
- [x] skald release --dry-run reads as release notes
