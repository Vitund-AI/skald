---
title: "Daemon (background) mode for the web server"
status: "done"
rank: 470
tags: ["ui"]
blocked_by: []
released: "0.2.0"
created_at: "2026-09-06T05:24:05Z"
updated_at: "2026-09-10T00:56:31Z"
---
## Requirements

when running ```git skald serve``` should we support a --daemon (or start to match stop) flag to background the process? Perhaps also need a --stop option

## Changelog

The board server runs in the background: `skald server start`, `status`, and `stop`, and `skald open` starts it if needed before opening the browser. `skald serve` still runs it in the foreground.

## [claude] 2026-09-06 07:04 UTC
Implemented: skald server start|stop|status with a state file in the config home, skald open starts it if needed and opens the browser on the current project. Foreground serve still works (D15).
