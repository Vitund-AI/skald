---
title: "skald context says when the board server is older than the installed package"
status: "done"
rank: 10
tags: ["agents", "area:cli", "area:server"]
blocked_by: []
assignee: "claude"
created_at: "2026-10-16T00:56:30Z"
updated_at: "2026-10-16T01:06:28Z"
---
## Requirements

Feature request from an agent: after an upgrade, the background board server keeps running the old version until someone runs `skald server restart`. `skald doctor` already warns about it, but agents don't run doctor; they run `skald context` at the start of every session.

## Acceptance
- [x] `skald context` prints one line, `board server runs X but Y is installed: skald server restart`, when a running server is older than the installed package, and nothing otherwise.
- [x] The check is free: it reads `server.json` and the installed version, checks the pid is alive, and makes no network call or HTTP probe.
- [x] `--json` (and MCP `skald_context`) carry it as `server`: `{version, installed, stale}` while a server runs, else null.
- [x] `doctor` keeps it as a WARN with the fix (an old server still works; FAIL means a broken setup and exit 1).
- [x] SPEC, CHANGELOG updated; contract baseline records the new field.

## [claude] 2026-10-16 00:58 UTC · handoff
Done.
- `server.version_lag(home)` reads `server.json` and checks the pid is alive, then compares the recorded version with this process's `__version__`.
  - It deliberately doesn't use `installed_version()`: an editable install leaves that metadata behind, which hid the lag in a real run here.
  - The long-running server still needs the metadata for its own health check.
- `build_context` adds `server`; the text output adds one line under the header when it's stale. MCP `skald_context` gets it through `build_context`.
- `doctor` is unchanged: it stays a WARN with the fix, because an old server still works and FAIL means exit 1.
- Docs: SPEC context row, working-with-agents.md, CHANGELOG. The contract baseline records `server`.

Verified:
- a new test covers stale, current, dead pid and no server;
- a real run with `server.json` set to 1.1.0 printed the line, and `skald server restart` cleared it;
- `context` took 0.21 s;
- the full suite, ruff and docs --check pass.
