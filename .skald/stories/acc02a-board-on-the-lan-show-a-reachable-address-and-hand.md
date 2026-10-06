---
title: "Board on the LAN: show a reachable address and hand over the key when bound to 0.0.0.0"
status: "done"
rank: 10
tags: ["area:board", "area:server", "bug"]
blocked_by: []
assignee: "claude"
created_at: "2026-10-06T06:10:11Z"
updated_at: "2026-10-06T06:19:07Z"
---
## Requirements

With `host` set to `0.0.0.0` (a board for other devices on the network), `skald open` prints `http://0.0.0.0:8321/?project=...`. Another device can't open that address, and the printed link carries no key. The token is enforced, but the only way to hand it to another device is to compose `http://<ip>:8321/#key=$(skald server token)` by hand, and nothing documents that. On a headless machine such as a Raspberry Pi, the browser `skald open` tries to launch never appears, so the keyed link is never seen at all.

## Acceptance
- When the server is bound to all interfaces, `skald open`, `serve`, `server start|restart|status` show the machine's network address(es), not `0.0.0.0`.
- With a wildcard bind, `skald open` prints the full link including `#key=` for each network address, since its purpose is another device; with a loopback bind the printed URL stays key-free as today, unless no browser could be opened, when it prints the keyed local link.
- This machine's own browser, the health probe, and `doctor` connect to `127.0.0.1` when the bind is a wildcard (connecting to `0.0.0.0` fails on Windows).
- Docs (board.md, troubleshooting, SPEC) say how to open the board from another device; DECISIONS entry.

## [claude] 2026-10-06 06:13 UTC · handoff
Done.
- `server.py` gains `WILDCARD`, `local_host()`, `lan_addresses()` (the default-route UDP trick plus the hostname's addresses, loopback dropped) and `shown_hosts()`.
- `health()` connects to `127.0.0.1` on a wildcard bind. `serve`, `server start|restart|status` print the network addresses.
- `skald open` opens the local browser on `127.0.0.1`. On a wildcard bind it prints a keyed link per network address. On a loopback bind it prints the keyed link only when `webbrowser.open` fails.
- Docs updated: board.md "From another device", troubleshooting, SPEC Access paragraph, `open` help and cli.md. DECISIONS D79. CHANGELOG.

Verified with 4 new tests in `TestOpenLinks`, the full suite (224) and ruff. Also ran a real `server start --host 0.0.0.0` here: status and open showed `192.0.2.2` (the sandbox's address). Over that address, curl got 401 without the key; POSTing the key to /api/session got 200 and the cookie then reached /api/projects.
