---
title: "Render the story body as Markdown in the modal"
status: "review"
rank: 30
tags: ["ui"]
blocked_by: []
created_at: "2026-09-06T02:16:15Z"
updated_at: "2026-09-06T07:04:40Z"
---
## Requirements

The modal shows the body in a textarea only. Add a read-only rendered view next to it. No build step, so either a small CDN Markdown library or a minimal renderer for headings, lists, code, and links.

## [claude] 2026-09-06 07:04 UTC
Implemented: a Preview toggle in the modal renders the body with marked from cdnjs, sanitised client-side (D23). Falls back to plain text when the CDN is unreachable.
