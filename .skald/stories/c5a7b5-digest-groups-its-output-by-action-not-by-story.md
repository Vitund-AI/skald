---
title: "digest groups its output by action, not by story"
status: "done"
rank: 60
tags: ["cli"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-14T01:52:16Z"
updated_at: "2026-09-14T01:53:14Z"
---
## Requirements

Feedback: a digest of several same-kind changes repeated the action per story (three "created" lines). Group the text output by action instead.

- [x] Sections in a fixed order (Moved, Notes, Open questions, Created, Archived, Deleted); each lists the stories with that change, newest activity first; empty sections are skipped.
- [x] --limit caps each section, with a per-section pointer to skald activity.
- [x] --json is unchanged: still one object per story.

## [agent] 2026-09-14 01:53 UTC · result
The text digest now groups by action: Moved, Notes, Open questions, Created, Archived, Deleted, in that order, each listing the stories with that change newest-first, empty sections skipped. Removes the repeated per-story action lines (three 'created' lines becomes one Created section). --limit caps each section with a per-section 'skald activity --since' pointer. _digest_data and --json are unchanged (one object per story). test_digest updated to the section format and the ordering; SPEC, CHANGELOG (amended the unreleased entry), docs/git-and-ci.md reworded. Suite 160 green, ruff clean.
