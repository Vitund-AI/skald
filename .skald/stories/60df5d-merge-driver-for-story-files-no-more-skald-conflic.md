---
title: "Merge driver for story files: no more .skald conflicts between parallel agents"
status: "ready"
rank: 10
tags: ["agents", "area:git"]
blocked_by: []
created_at: "2026-10-17T05:10:34Z"
updated_at: "2026-10-17T05:10:34Z"
---
## Requirements

From agent feedback (parallel worktree agents, 2026-10-17). With parallel worktree agents, almost every cherry-pick or merge conflicts in `.skald/stories/`. Agents resolve those by hand or by script, and one such resolution left story 761f8f with its front matter twice.

## Requirements
A `skald merge-file %O %A %B %P` driver, registered for `.skald/stories/*.md` through `.gitattributes` and the clone's git config (`skald hooks git --install`), that merges a story three ways:
- front matter field by field against the common ancestor: a field changed on one side takes that side; `updated_at` takes the later; `tags` and `blocked_by` merge as sets (both sides' additions and removals); a field changed differently on both sides follows a recorded rule (status: the side further along the workflow; others: a conflict reported clearly);
- notes as an append-only union ordered by timestamp, never a text conflict;
- the authored prelude three-way, with conflict markers only inside the body when both sides rewrote the same lines, so the front matter always stays valid.

## Acceptance
- [ ] Two branches that each add a note and change different fields merge with no conflict.
- [ ] Tag additions and removals from both sides are kept.
- [ ] Status changed on both sides resolves by the recorded rule.
- [ ] A real body conflict leaves markers in the body only, a valid front matter, and a non-zero exit so git reports it.
- [ ] `skald hooks git --install` registers the driver; docs and a decision record explain the rules.
