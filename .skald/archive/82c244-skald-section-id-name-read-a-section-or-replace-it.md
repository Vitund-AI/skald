---
title: "skald section <id> NAME: read a section, or replace it from a pipe"
status: "done"
rank: 70
tags: ["agents", "area:cli", "area:mcp"]
blocked_by: []
assignee: "claude"
released: "1.3.0"
created_at: "2026-10-17T05:10:34Z"
updated_at: "2026-10-17T07:42:11Z"
---
## Background

From agent feedback (parallel worktree agents, 2026-10-17). Agents read stories with sed and grep and rewrite sections by hand-editing files, which also causes many of the merge conflicts above.

## Requirements

- `skald section <id> NAME` prints the section's content; `skald section <id> NAME -` (or inline TEXT) replaces the content and the heading stays. Writing takes an explicit `-` rather than detecting a pipe: agent shells often have an empty, non-terminal stdin, which would blank the section, or an open one, which would hang (D85).
- NAME matches a heading's text without its `#`s, case-insensitively, exact else prefix; two matches refuse (the `tick` parser), and two identically named sections say to rename one.
- A missing section is an error; `--create` appends it. Piped text starting with the same heading is refused.
- Notes are never addressable: sections are the authored body only.
- The write holds the lock, bumps `updated_at`, and refuses a result `skald check` would reject. `--dry-run` shows the change.

## Acceptance
- [x] read, replace, `--create`, and `--dry-run` work as above; errors name the fix
- [x] MCP gains an equivalent tool; contract template, SPEC, docs updated

## [claude] 2026-10-17 05:56 UTC · handoff
Done. Requirements updated, with this command, for the one deliberate change: writing needs an explicit `-` (D85).
- store:
  - `find_section`, `section_text` and `headings_of` share `_match_heading` with `tick`;
  - `Store.replace_section` (locked, bumps updated_at) refuses empty text, the section's own heading, a heading at its level or above, note headings and conflict markers, then re-parses the result before writing;
  - `--create` appends `##` before the notes; CRLF line endings are kept.
- CLI: `section` (read, write, `--create`, `--dry-run` diff, `--json`).
- MCP: `skald_section`.
- Docs: contract template and copies, SPEC command row, stories.md, working-with-agents.md, D85, CHANGELOG. The contract baseline records section.

Verified:
- tests/test_section.py (6 tests): read by any level, case or prefix; replace keeping the next section and the notes; create and dry-run; every refusal leaving the file unchanged; ambiguity; CRLF; MCP;
- the full suite, ruff, docs --check and doctor;
- a scratch-repo run.
