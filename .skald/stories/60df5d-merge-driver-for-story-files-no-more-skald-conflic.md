---
title: "Merge driver for story files: no more .skald conflicts between parallel agents"
status: "review"
rank: 50
tags: ["agents", "area:git"]
blocked_by: []
assignee: "claude"
created_at: "2026-10-17T05:10:34Z"
updated_at: "2026-10-17T05:40:55Z"
---
## Requirements

From agent feedback (parallel worktree agents, 2026-10-17). With parallel worktree agents, almost every cherry-pick or merge conflicts in `.skald/stories/`. Agents resolve those by hand or by script, and one such resolution left story 761f8f with its front matter twice.

## Requirements
A `skald merge-file %O %A %B %P` driver, registered for `.skald/stories/*.md` through `.gitattributes` and the clone's git config (`skald hooks git --install`), that merges a story three ways:
- front matter field by field against the common ancestor: a field changed on one side takes that side; `updated_at` takes the later; `tags` and `blocked_by` merge as sets (both sides' additions and removals); a field changed differently on both sides follows a recorded rule (status: the side further along the workflow; others: a conflict reported clearly);
- notes as an append-only union ordered by timestamp, never a text conflict;
- the authored prelude three-way, with conflict markers only inside the body when both sides rewrote the same lines, so the front matter always stays valid.

## Acceptance
- [x] Two branches that each add a note and change different fields merge with no conflict.
- [x] Tag additions and removals from both sides are kept.
- [x] Status changed on both sides resolves by the recorded rule.
- [x] A real body conflict leaves markers in the body only, a valid front matter, and a non-zero exit so git reports it.
- [x] `skald hooks git --install` registers the driver; docs and a decision record explain the rules.

## [claude] 2026-10-17 05:40 UTC · handoff
Done. Your rule for status is in: the later column wins. "Most recent edit wins" covers the other scalar fields, including rank read as priority.
- `merge.py`:
  - `merge_story` handles the front matter with `merge_fields`: three-way against the base, sets for tags/blocked_by, the later updated_at, the base created_at, status by column order, otherwise the newer side.
  - Notes are a union minus removals, ordered by timestamp.
  - The prelude goes through `gitutil.merge_file`; markers stay in the body.
  - An unparseable side falls back to a whole-file line merge.
  - `run_driver` writes over %A and exits 1 on markers. A path outside `stories/` (the rendered board) keeps ours.
- CLI: `skald merge-file BASE OURS THEIRS [PATH]`, dispatched before the Workspace (no registry or lock).
- `hooks git --install` adds the stories glob and the render path to `.gitattributes` and sets `merge.skald.name/driver`.
- `doctor` has a `merge` check: OK, WARN when the attribute is set with no driver, INFO when not set up.
- A pre-merge-commit hook was tried and dropped: git doesn't reread the index after it (D84).
- Docs: git-and-ci.md Conflicts (rule table), SPEC 4.8, working-with-agents.md, D84, CHANGELOG. The contract baseline records merge-file.

Verified with tests/test_merge.py (9 tests):
- the rules: different fields, the same field both ways (symmetric), a note kept once, a removed note staying removed, fields added and removed, a body conflict confined to the body, the unparseable fallback;
- real git: two agent branches (claim+note+tag vs note+tag+set rank) merge with no conflict, and check passes;
- the rendered board doesn't conflict and is reported stale until render;
- cherry-pick merges;
- doctor OK, then WARN after unsetting the driver.
The full suite, ruff and docs --check pass.
