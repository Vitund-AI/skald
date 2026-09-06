---
title: "Claude Code skill and init writing the instructions pointer"
status: "ready"
rank: 90
tags: ["agents"]
blocked_by: []
created_at: "2026-09-06T19:01:43Z"
updated_at: "2026-09-06T19:01:43Z"
---
## Requirements

hooks claude --install also writes .claude/skills/skald/SKILL.md from the contract template; init appends the one-line pointer to root CLAUDE.md and AGENTS.md, creating AGENTS.md when neither exists.
