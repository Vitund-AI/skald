---
title: "Make columns collapsible via a config flag; ship the lifecycle icebox collapsible"
status: "done"
rank: 40
tags: ["roadmap"]
blocked_by: []
assignee: "agent"
released: "0.9.0"
created_at: "2026-09-17T16:14:34Z"
updated_at: "2026-09-29T18:20:30Z"
---
## Requirements

Follow-up to f0e40d, before the icebox feature releases. The board hardcoded collapse to done/closed roles (isTerminalRole), so the backlog-role icebox could not fold away.

- Column gains an optional collapsible boolean (validated), included in to_dict/board payload when set.
- Board: collapsible = col.collapsible != null ? col.collapsible : isTerminalRole(col.role). Preserves the done/closed default; lets any column opt in or out.
- lifecycle preset marks the icebox collapsible: true so parked work folds away like done work.

Docs: SPEC (columns config + board), board.md, stories.md. Standard library only.
