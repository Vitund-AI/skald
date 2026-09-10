---
title: "Author identity for notes and claims"
status: "done"
rank: 420
tags: ["core"]
blocked_by: []
released: "0.2.0"
created_at: "2026-09-06T07:04:41Z"
updated_at: "2026-09-10T00:56:31Z"
---
## Requirements

CLI defaults to agent, overridable with --as and SKALD_AUTHOR. Board uses SKALD_AUTHOR, then skald config author, then git user.name.

## Changelog

Notes and claims carry an identity: the CLI defaults to `agent`, overridable with `--as` or `SKALD_AUTHOR`; the board uses `SKALD_AUTHOR`, then `skald config author`, then your git `user.name`.

## [claude] 2026-09-06 07:04 UTC
Implemented (D11). Identity shown in the board header.
