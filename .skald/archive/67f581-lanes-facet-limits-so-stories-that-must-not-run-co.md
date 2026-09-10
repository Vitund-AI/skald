---
title: "Lanes: facet limits so stories that must not run concurrently are not picked together"
status: "done"
rank: 80
tags: ["agents", "core"]
blocked_by: []
assignee: "claude"
released: "0.3.0"
created_at: "2026-09-10T05:09:37Z"
updated_at: "2026-09-10T18:07:16Z"
---
## Requirements

Dependencies express order; some work has no order but cannot run concurrently (four stories each rewriting one Alembic baseline file collided semantically in parallel worktrees). config.json gains facet_limits, e.g. {"lane": 1}: for that facet key, at most N stories per value may be in an active column at once, counting claims on other branches and in other checkouts. From the design-record feature request (item 6).

- next_story skips a candidate whose lane is busy, with a warning naming the holder.
- claim, and move into an active column, warn when the limit would be exceeded. Advisory.
- skald columns prints facet limits; status counts busy lanes; the board swimlane header shows N/N in red like an over-limit column.
- Docs: SPEC 3, 4.4, 6; stories.md Lanes paragraph; working-with-agents Several agents at once; AGENTS template (tag stories that must not run together with the same lane: value); CHANGELOG; DECISIONS (a facet limit, not a new relation).

## Acceptance
- [x] Config validation: keys are facet names, values positive integers
- [x] next skips and warns with a local active story, a claim on another branch, and a claim in another checkout; a limit of 2 admits two
- [x] claim and move warn; columns and status report; board header
- [x] Docs synced

## [claude] 2026-09-10 05:29 UTC · result
config.json facet_limits {key: N}, validated (facet key pattern, positive int). Store.busy_lanes counts active-here plus claimed-elsewhere per limited facet value; lane_conflicts names holders. next skips with a warning; claim and move into an active column warn (update gained an optional elsewhere; move passes it). columns lists limits; status prints busy lanes and JSON lanes; the board payload carries facet_limits and the swimlane header shows N/N active in red when full. Docs: SPEC 3, 4.4, 6; stories.md Lanes; working-with-agents; AGENTS step 2 and copies; CHANGELOG; D56. 133 tests pass.
