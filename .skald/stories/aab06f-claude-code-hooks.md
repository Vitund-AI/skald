---
title: "Claude Code hooks"
status: "done"
rank: 40
tags: ["agents"]
blocked_by: []
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

skald hooks claude prints or installs SessionStart (skald status && skald ls) and Stop (skald check) hooks; --strict makes the stop hook fail on uncommitted story files.

## Changelog

`skald hooks claude --install` adds Claude Code hooks: SessionStart runs `skald status` and `skald ls` so every session begins oriented, and Stop runs `skald check`; `--strict` makes the stop hook fail on uncommitted story files.

## [claude] 2026-09-06 07:04 UTC
Implemented (D22). Merges into an existing .claude/settings.json without clobbering other hooks.
