---
title: "Browse what shipped, by release, on the board"
status: "idea"
rank: 80
tags: ["roadmap"]
blocked_by: []
created_at: "2026-09-13T23:08:32Z"
updated_at: "2026-09-13T23:08:32Z"
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
