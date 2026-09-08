---
title: "Daemon (background) mode for the web server"
status: "done"
rank: 30
tags: ["ui"]
blocked_by: []
created_at: "2026-09-06T05:24:05Z"
updated_at: "2026-09-08T04:22:20Z"
---
## Requirements

when running ```git skald serve``` should we support a --daemon (or start to match stop) flag to background the process? Perhaps also need a --stop option

## [claude] 2026-09-06 07:04 UTC
Implemented: skald server start|stop|status with a state file in the config home, skald open starts it if needed and opens the browser on the current project. Foreground serve still works (D15).
