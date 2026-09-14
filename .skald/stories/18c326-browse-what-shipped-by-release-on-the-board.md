---
title: "Browse what shipped, by release, on the board"
status: "done"
rank: 100
tags: ["roadmap"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-13T23:08:32Z"
updated_at: "2026-09-14T05:42:10Z"
---
## Requirements

A Releases view on the board lists shipped work grouped by version, read from the archive.

- A header toggle (like Graph) switches to a Releases view: versions newest-first, each expandable to the stories that shipped in it.
- "Shipped" means archived stories whose `released` stamp is set and whose status is a done-role column; won't-do (closed-role) stories are excluded.
- A read endpoint `GET /api/projects/<p>/releases` returns those stories grouped by `released`, newest-first, each with id, title, and status; the version date if it can be had cheaply, else just the version.
- Clicking a story opens the existing dialog read-only (the server already serves archived stories).
- Shares a `store.releases()` helper with the rendered-doc story; whichever lands first adds it.
- Bounded: a story count on each version summary; older versions collapsed.

## Why

The board shows active work; what shipped lives only in git and the CHANGELOG. The `released` stamp and the read-only dialog already exist, so grouping the archive by version turns "what shipped in 0.6.0" into a click. It mirrors the CHANGELOG shipped bullets, so the two stay consistent.

## Notes

- `skald ls --release VERSION` today returns done and won't-do together; decide whether it keeps that or gains a flag. The `releases()` helper is done-only regardless.

## [agent] 2026-09-14 05:42 UTC · result
Board Releases view: a header toggle (rel-btn) mutually exclusive with Graph, shows GET /api/projects/<p>/releases grouped by version newest first, one section per version listing the shipped stories; a row opens the story. Rendered on toggle, not on every poll (render() early-returns when releasesView). The endpoint returns store.releases() as {version, stories:[{id,title,status,tags,assignee}]}. Archived stories now open read-only everywhere: openModal computes ro = state.readonly || s.archived and disables the fields, quick select, claim, note, and Edit (setEditing too), the e key is blocked, and the meta shows 'read-only'; so a shipped story opens for reading, not editing. Verified with a headless-browser pass (two versions newest-first, rows open the read-only dialog with Edit hidden and the quick select disabled, Graph and Releases are mutually exclusive, no page errors). Server test for the endpoint. SPEC section 8, docs/api.md, docs/board.md, CHANGELOG. Shares store.releases() with a729bb.
