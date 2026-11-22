---
title: "Archived blockers count as missing: released stories make their dependents look blocked"
status: "done"
rank: 20
tags: ["area:core"]
blocked_by: []
assignee: "claude"
released: "1.3.4"
created_at: "2026-11-21T19:36:20Z"
updated_at: "2026-11-22T20:19:30Z"
---
## Requirements

Reported from a project's graph view: blockers shown red as "missing",
though clicking one opened the story fine. They are stories archived by a
release.

Reproduced in a scratch project: B is blocked by A, A is done and
archived. After that:

- `skald ls` shows B as BLOCKED by A;
- `skald next` and `skald context` say nothing is ready and unblocked, and
  B is "waiting on" A;
- the graph (CLI and board) shows A as missing, with an unmet edge.

Only `skald show B` is right (A: archived, satisfied).

Cause: `dep_states` resolves each `blocked_by` entry in the index the
caller passes. Most callers (the CLI listings, context, status, next, the
MCP tools, the board API, render and graph) build that index from active
stories only, so an archived blocker is not found and reads as missing. So
every release can re-block work that depended on what it shipped, and
agents stop being offered that work.

- `Store.dep_states`: when the caller's index lacks a local id, look it up
  in the project (the archive included) before calling it missing. Do the
  same for `Snapshot`, against all of its stories.
- Dependency entries carry the blocker's title, so the board's graph can
  label an archived blocker.
- `graph.build_graph` resolves archived blockers the same way and shows
  them as "archived", satisfied.
- The board's graph shows an archived blocker as a done-coloured node
  marked "archived", with its title. Clicking it opens it read-only, as
  today.

## Acceptance
- [x] With A archived, `ls`, `next`, `context`, `status` and the MCP list treat B as unblocked.
- [x] The graph (CLI json, mermaid, and the board) shows A as archived and satisfied, with its title.
- [x] A truly missing id is still missing and unmet.
- [x] Tests; contract fixture updated for the added `title` on dependency entries; CHANGELOG.

## [claude] 2026-11-21 19:39 UTC · handoff
Done.
- Store.dep_states: a miss in the caller's index falls back to get_or_none (stories and archive), so every caller that indexes only active stories (cli ls/next/context/status/export, mcp, server board, render) now resolves archived blockers as archived and satisfied.
- Snapshot gained get_or_none and does the same.
- DepState carries the blocker's title, and to_dict emits it (contract baseline refreshed; the addition only).
- graph.build_graph falls back the same way: status "archived", role from the stored status, title kept.
- Board buildGraph labels an archived blocker "archived" with its title, done or closed coloured.
- Test in tests/test_store.py: archived blocker satisfied via a load_all index, next --json and ls, build_graph node and edge; a truly missing id stays unmet. It fails without the fix.
- Checked in a scratch project (ls, next, context, status, graph json and mermaid, render) and in the board's graph view.
- This repo's own b24938 was shown blocked by the archived b56d9e; the re-render fixes its red "(missing)" node.
