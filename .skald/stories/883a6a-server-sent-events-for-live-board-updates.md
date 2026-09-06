---
title: "Server-sent events for live board updates"
status: "backlog"
rank: 10
tags: ["ui"]
blocked_by: []
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-06T07:04:42Z"
---
## Requirements

Replace the 1.5s version-hash polling with an SSE endpoint that pushes when story files change. Watch for thread-per-tab cost on ThreadingHTTPServer (D14).
