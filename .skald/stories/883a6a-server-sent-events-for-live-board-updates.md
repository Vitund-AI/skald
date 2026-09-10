---
title: "Server-sent events for live board updates"
status: "done"
rank: 80
tags: ["ui"]
blocked_by: []
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

Replace the 1.5s version-hash polling with an SSE endpoint that pushes when story files change. Watch for thread-per-tab cost on ThreadingHTTPServer (D14).

## Changelog

The board updates live over a server-sent event stream when story files change, with polling as the fallback. A toast announces changes made outside the board.

## [claude] 2026-09-06 07:08 UTC
Implemented: GET /api/projects/<p>/events streams hello and change events from the version hash; the board subscribes with EventSource and keeps a 15s poll as a safety net (D25). Verified in Chromium: a CLI change appeared in 182 ms.
