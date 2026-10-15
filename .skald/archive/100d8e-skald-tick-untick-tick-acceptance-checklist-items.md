---
title: "skald tick / untick: tick acceptance checklist items without editing the file"
status: "done"
rank: 20
tags: ["agents", "area:cli", "area:mcp"]
blocked_by: []
assignee: "claude"
released: "1.2.0"
created_at: "2026-10-15T20:04:37Z"
updated_at: "2026-10-15T23:32:05Z"
---
## Requirements

Agent feedback: there is no command to tick an `## Acceptance` checklist item, so agents edit the story file by hand. The contract tells them to tick items as they verify each, and moving to review warns about unticked ones.

## Acceptance
- [x] `skald tick <id> N [N ...]` and `skald untick <id> N [N ...]` tick and untick items under `## Acceptance`; `--section HEADING` picks another heading (any level, case-insensitive; exact match first, else prefix).
- [x] With no N, either command lists the section's items numbered with their state.
- [x] Items are numbered in reading order within the section, nested items included, code fences skipped; the Acceptance progress count uses the same parser, so numbers match the board and the review warning.
- [x] Errors give the fix: a wrong number names how many items there are; a missing section names the headings that have items; an ambiguous heading names the matches.
- [x] The write takes the mutation lock and bumps `updated_at`; only the box character changes.
- [x] `resume` lists the numbered Acceptance items; MCP gains `skald_tick` and `skald_untick`.
- [x] Contract template, SPEC, docs, CHANGELOG updated; contract baseline records the new commands.

## [claude] 2026-10-15 20:12 UTC · handoff
Done; all 7 acceptance items ticked with the new command itself.
- `store.task_items(body, section)` is the one parser: heading at any level, exact match else prefix, the section running to the next heading of the same or higher level, fences skipped, prelude only. `acceptance_progress` now uses it.
- `Store.tick(ref, numbers, done, section)` checks every number before writing, then rewrites only the box character, keeping CRLF.
- CLI: `tick`/`untick` (no N lists them, `--json`). `resume` gains numbered `acceptance_items`, shared with MCP via `_resume_extras`.
- MCP: `skald_tick`/`skald_untick`.
- Contract template plus its two copies, SPEC, stories.md, working-with-agents.md, D83, CHANGELOG. The contract baseline now records tick, untick and resume acceptance_items.

Verified with tests/test_tick.py (9 tests), the full suite, ruff, docs --check, and doctor reporting the contract copies match.
