---
title: "Claude Code SessionStart hook runs skald context, not skald ls"
status: "done"
rank: 20
tags: ["agents"]
blocked_by: []
assignee: "claude"
released: "0.3.0"
created_at: "2026-09-10T04:27:40Z"
updated_at: "2026-09-10T18:07:16Z"
---
## Requirements

The hook written by skald hooks claude runs 'skald status && skald ls', which prints every open story into the agent's context on every session start, resume, clear, and compaction. On a backlog of a few hundred stories that is hundreds of rows, repeatedly. skald context is the bounded orientation block the docs already recommend for SessionStart; the template contradicted the docs. Reported by an agent adopting Skald in another repository.

- The hook runs skald context. Identity comes from --as, then SKALD_AUTHOR, then agent; hooks claude gains --as NAME to bake a name into the command.
- Docs: SPEC 6 row, README, getting-started, working-with-agents (mention SKALD_AUTHOR for the assigned-to-me section), cli.md regenerated, CHANGELOG, DECISIONS.

## Changelog

The Claude Code SessionStart hook written by `skald hooks claude` now runs `skald context`, a bounded orientation block, instead of listing the whole open backlog on every session start. `skald hooks claude --as NAME` bakes the agent's name into the hook; otherwise set `SKALD_AUTHOR`. Re-run the install to update an existing hook.

## Acceptance
- [x] Hook command is skald context, with --as NAME when given
- [x] Test asserts the command
- [x] SPEC, README, getting-started, working-with-agents, cli.md, CHANGELOG, DECISIONS

## [claude] 2026-09-10 04:29 UTC · result
Hook runs skald context, with --as NAME baked in when hooks claude --as is given; this repository's own .claude/settings.json updated to skald context --as claude. Test asserts both forms. SPEC 6 row, README, getting-started, working-with-agents (why context not ls; SKALD_AUTHOR), cli.md regenerated, CHANGELOG Unreleased, D50.
