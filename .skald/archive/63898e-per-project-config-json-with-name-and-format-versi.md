---
title: "Per-project config.json with name and format version"
status: "done"
rank: 390
tags: ["core"]
blocked_by: []
released: "0.2.0"
created_at: "2026-09-06T07:04:41Z"
updated_at: "2026-09-10T00:56:31Z"
---
## Requirements

Committed .skald/config.json carries the project name used by cross-project references and a format number so newer tools can refuse or migrate cleanly.

## Changelog

Each project carries a committed `.skald/config.json` with its name, used by cross-project references, and a format version so newer tools can refuse or migrate cleanly.

## [claude] 2026-09-06 07:04 UTC
Implemented in config.py. Missing config.json is created lazily with a notice (D9). Format newer than supported raises ConfigError with an upgrade hint.
