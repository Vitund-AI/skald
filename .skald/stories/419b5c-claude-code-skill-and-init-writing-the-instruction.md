---
title: "Claude Code skill and init writing the instructions pointer"
status: "review"
rank: 300
tags: ["agents"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T19:01:43Z"
updated_at: "2026-09-06T19:12:48Z"
---
## Requirements

hooks claude --install also writes .claude/skills/skald/SKILL.md from the contract template; init appends the one-line pointer to root CLAUDE.md and AGENTS.md, creating AGENTS.md when neither exists.

## [claude] 2026-09-06 19:12 UTC
Implemented: hooks claude --install writes .claude/skills/skald/SKILL.md with frontmatter from the contract template; init appends the pointer to root CLAUDE.md and AGENTS.md or creates AGENTS.md (D38).
