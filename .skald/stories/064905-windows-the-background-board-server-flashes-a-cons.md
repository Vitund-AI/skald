---
title: "Windows: the background board server flashes a console window for every git command"
status: "done"
rank: 10
tags: ["area:server", "bug", "platform:windows"]
blocked_by: []
assignee: "claude"
created_at: "2026-10-15T19:29:53Z"
updated_at: "2026-10-15T19:39:12Z"
---
## Requirements

First user bug report. On Windows, `skald open` starts the board server in the background, and it runs git every few seconds to keep the board live (`rev-parse`, `worktree list`, `status`, `for-each-ref`). Each git run flashes up a console window and closes it.

Cause: `start_server` launches the server with `DETACHED_PROCESS`, so it has no console. Every console program it starts, git included, then gets a new console window of its own.

## Acceptance
- The background server runs with a hidden console (`CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`) instead of none, so git shares that invisible console and nothing flashes. It still outlives the terminal that started it and ignores its Ctrl+C.
- gitutil passes `CREATE_NO_WINDOW` to git whenever Skald itself has no console, for example an MCP server started by a GUI host. A process with a visible console keeps sharing it, so git can still prompt for credentials in a terminal.
- Tests cover both flag choices; the Windows CI job still starts and stops the real background server.

## [claude] 2026-10-15 19:31 UTC · handoff
Done.
- `server._background_kwargs()`: on Windows, `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP` replaces `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`.
- `gitutil.no_window()`: returns `CREATE_NO_WINDOW` on Windows when `GetConsoleWindow()` is null. It's applied to all three git `subprocess.run` calls, the only subprocess calls in the package apart from the server spawn.
- Docs: D82, a SPEC command-table note, CHANGELOG.

Verified with tests for both flag choices and for every git call carrying the flags. The full suite and ruff pass. Windows CI starts and stops the real background server with the new flags. The missing window itself can't be observed in CI, so it needs a check on a Windows desktop.
