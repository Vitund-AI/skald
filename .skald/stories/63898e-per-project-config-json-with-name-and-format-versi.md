---
title: "Per-project config.json with name and format version"
status: "done"
rank: 50
tags: ["core"]
blocked_by: []
created_at: "2026-09-06T07:04:41Z"
updated_at: "2026-09-08T17:24:16Z"
---
## Requirements

Committed .skald/config.json carries the project name used by cross-project references and a format number so newer tools can refuse or migrate cleanly.

## [claude] 2026-09-06 07:04 UTC
Implemented in config.py. Missing config.json is created lazily with a notice (D9). Format newer than supported raises ConfigError with an upgrade hint.
