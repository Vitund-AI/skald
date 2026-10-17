---
title: "skald section <id> NAME: read a section, or replace it from a pipe"
status: "ready"
rank: 40
tags: ["agents", "area:cli", "area:mcp"]
blocked_by: []
created_at: "2026-10-17T05:10:34Z"
updated_at: "2026-10-17T05:10:34Z"
---
## Requirements

From agent feedback (parallel worktree agents, 2026-10-17). Agents read stories with sed and grep and rewrite sections by hand-editing files, which also causes many of the merge conflicts above.

## Requirements
- `skald section <id> NAME` prints the section's content; with stdin piped, the piped text replaces the content and the heading stays.
- NAME matches a heading's text without its `#`s, case-insensitively, exact else prefix; two matches refuse (the `tick` parser).
- A missing section is an error; `--create` appends it. Piped text starting with the same heading is refused.
- Notes are never addressable: sections are the authored body only.
- The write holds the lock, bumps `updated_at`, and refuses a result `skald check` would reject. `--dry-run` shows the change.

## Acceptance
- [ ] read, replace, `--create`, and `--dry-run` work as above; errors name the fix
- [ ] MCP gains an equivalent tool; contract template, SPEC, docs updated
