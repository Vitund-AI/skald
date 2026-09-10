---
title: "rm --force clears the references it would orphan"
status: "done"
rank: 10
tags: ["cli", "core"]
blocked_by: []
assignee: "claude"
released: "0.4.0"
created_at: "2026-09-10T18:21:55Z"
updated_at: "2026-09-10T20:18:46Z"
---
## Requirements

rm --force on a parent left its children carrying parent: <id>, which skald check then reported as a problem; the same happens to dependents' blocked_by. From the 0.3.0 adoption review (finding 1). --force now clears parent on every child and removes the id from every dependent's blocked_by, printing each change, so the backlog is never left in a state the tool itself calls corrupt.

## Changelog

`skald rm --force` now clears the parent field on the deleted story's children and removes it from other stories' blocked_by, printing each change, instead of leaving references that `skald check` reports as problems.

## Acceptance
- [x] Children lose their parent; dependents lose the reference; each printed
- [x] Test; SPEC 6 rm row; stories.md; rm help string

## [claude] 2026-09-10 18:26 UTC · result
delete(force, notes) removes the id from dependents' blocked_by and clears children's parent, describing each; rm prints the lines. The old test that asserted the dangling reference now asserts a clean check. SPEC 6 rm row, stories.md, rm help.
