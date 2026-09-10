---
title: "serve --port 0 falls back to the configured port"
status: "done"
rank: 10
tags: ["core"]
blocked_by: []
assignee: "claude"
released: "0.3.0"
created_at: "2026-09-10T04:27:40Z"
updated_at: "2026-09-10T18:07:16Z"
---
## Requirements

_host_port in server.py uses 'or' to fall back to the configured value, so a port of 0 (ask the OS for a free port) is treated as unset and the server binds the configured port, 8321 by default. The daemon test starts a server on port 0 and so fails on any machine where a board is already running on 8321; CI never has one, so it stayed green. Reported by an agent adopting Skald in another repository.

## Changelog

`skald serve --port 0` and `skald server start` with port 0 now ask the operating system for a free port instead of silently using the configured one. The test suite passes on a machine with a board already running.

## Acceptance
- [x] _host_port distinguishes not given from 0 for both host and port
- [x] A unit test pins port 0 and the configured default without depending on 8321 being free
- [x] CHANGELOG entry

## [claude] 2026-09-10 04:29 UTC · result
_host_port only falls back when the flag is None, so port 0 reaches the OS. Unit test pins port 0, the configured default, explicit flags, and a bare namespace. Reproduced the report: with a board on 8321, the daemon test fails on the old code (server exited immediately) and passes on the fix.
