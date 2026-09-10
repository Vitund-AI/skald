---
title: "Story templates"
status: "done"
rank: 50
tags: ["cli"]
blocked_by: []
released: "0.2.0"
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-10T00:56:31Z"
---
## Requirements

.skald/templates/<name>.md used by skald new --template name; skald templates lists them.

## Changelog

Story templates live in `.skald/templates/<name>.md`; `skald new --template NAME` starts from one and `skald templates` lists them.

## [claude] 2026-09-06 07:04 UTC
Implemented. Template body first, then any --body text.
