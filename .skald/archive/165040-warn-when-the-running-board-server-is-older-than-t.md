---
title: "Warn when the running board server is older than the installed package; add skald server restart"
status: "done"
rank: 10
tags: ["area:server"]
blocked_by: []
assignee: "agent"
released: "0.8.1"
created_at: "2026-09-16T16:15:55Z"
updated_at: "2026-09-17T04:48:22Z"
---
## Requirements

When `skald server` runs as a background daemon and the user upgrades the pip package, the running process keeps the old code in memory. Detect this and surface it, non-blocking:

- /api/health gains `installed` (importlib.metadata.version('skald-kanban'), None if undeterminable) and `stale` (update.is_newer(installed, running __version__)).
- Board shows a dismissible banner when stale, offering the restart command.
- `skald server status` reports the mismatch and points at restart.
- New `skald server restart` subcommand: stop then start.
- doctor's server check aligns to is_newer semantics and mentions `skald server restart`.

Gate every warning with is_newer so an editable install (installed older than source) never false-positives. Standard library only.
