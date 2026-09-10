---
title: "Claude Code skill and init writing the instructions pointer"
status: "done"
rank: 200
tags: ["agents"]
blocked_by: []
assignee: "claude"
released: "0.2.0"
created_at: "2026-09-06T19:01:43Z"
updated_at: "2026-09-10T00:56:31Z"
---
## Requirements

hooks claude --install also writes .claude/skills/skald/SKILL.md from the contract template; init appends the one-line pointer to root CLAUDE.md and AGENTS.md, creating AGENTS.md when neither exists.

## Changelog

`skald hooks claude --install` also writes a Claude Code skill from the contract template, and `skald init` appends the one-line pointer to `.skald/AGENTS.md` to the root `CLAUDE.md` and `AGENTS.md`, creating `AGENTS.md` when neither exists.

## [claude] 2026-09-06 19:12 UTC
Implemented: hooks claude --install writes .claude/skills/skald/SKILL.md with frontmatter from the contract template; init appends the pointer to root CLAUDE.md and AGENTS.md or creates AGENTS.md (D38).
