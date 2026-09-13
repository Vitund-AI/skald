---
title: "Document how to model won't-do: the closed role and the archive"
status: "idea"
rank: 100
tags: ["roadmap"]
blocked_by: []
created_at: "2026-09-13T23:56:02Z"
updated_at: "2026-09-13T23:56:02Z"
---
## Requirements

Write down, in one place, how to handle a "won't do" column.

- docs/stories.md (and getting-started where it helps) explains that a won't-do column should carry role `closed`, not backlog: closed is a terminal state meaning decided-not-to-do, distinct from done.
- Spell out the lifecycle: move to the closed column with a `decision` note saying why; it leaves the board at the next `skald release` (recorded under "Not doing" and archived with the version stamp) or via `skald archive <id>` on demand.
- Archiving keeps the file and git history (`skald show`, `skald ls --archived` still find it); never delete a won't-do.
- Name the closed-role behaviours already in place: a closed blocker satisfies a dependency with a warning, and `release` lists closed stories under "Not doing".

## Why

Users add a won't-do column and ask where those stories should live. The model already answers it (closed role, then archive via release), but it is not written in one place. Docs only; no behaviour change.

## Notes

- Optional: `skald check` could hint when a column labelled like won't-do / cancelled carries a non-closed role. Decide separately; not required for the docs.
