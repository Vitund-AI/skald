---
title: "skald open outside a repository opens the board on the browser's last project"
status: "review"
rank: 10
tags: ["area:board", "area:cli"]
blocked_by: []
assignee: "claude"
created_at: "2026-10-08T04:59:27Z"
updated_at: "2026-10-08T05:01:14Z"
---
## Requirements

`skald open` outside any repository fails with "no .skald directory found", even when projects are registered on the machine. The board already remembers the last project picked in its switcher (per browser, in localStorage) and falls back to the first registered project, so the CLI need not insist on a project.

## Acceptance
- Outside a repository, with at least one registered project, `skald open` starts the server if needed and opens the board without `?project=`; the page shows this browser's last project, else the first. A note on stderr says so.
- Inside a repository, or with `-p NAME`, unchanged; an unknown `-p NAME` still errors.
- With no projects registered, the error stays (`skald init` is the only useful advice).
- The last project is not stored server-side: each browser remembers its own.

## [claude] 2026-10-08 05:01 UTC · handoff
Done.
- `cli.run`: `open` catches NotFoundError when no `-p` was given and at least one registered project exists, and passes store=None.
- `cmd_open`: takes Optional[Store], omits `?project=` when there is no store, and notes on stderr that the board will choose.
- Docs updated: SPEC command table, board.md, multi-project.md, `open` help and cli.md. CHANGELOG. D80 covers why the last project is not stored server-side.

Verified with 2 new tests: outside a repo; with -p, and an unknown -p; no projects registered. The full suite (226), ruff and docs --check pass. A real run from a scratch directory outside any repository opened `http://127.0.0.1:8321/` with no project and exited 0.
