---
title: "Render the story body as Markdown in the modal"
status: "done"
rank: 60
tags: ["ui"]
blocked_by: []
created_at: "2026-09-06T02:16:15Z"
updated_at: "2026-09-08T17:24:16Z"
---
## Requirements

The modal shows the body in a textarea only. Add a read-only rendered view next to it. No build step, so either a small CDN Markdown library or a minimal renderer for headings, lists, code, and links.

## Changelog

The story dialog renders the body as Markdown with a Preview toggle beside the editor.

## [claude] 2026-09-06 07:04 UTC
Implemented: a Preview toggle in the modal renders the body with marked from cdnjs, sanitised client-side (D23). Falls back to plain text when the CDN is unreachable.
