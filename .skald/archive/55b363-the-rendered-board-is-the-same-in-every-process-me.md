---
title: "The rendered board is the same in every process: Mermaid class lines in a fixed order"
status: "done"
rank: 10
tags: ["area:render"]
blocked_by: []
assignee: "claude"
released: "1.3.2"
created_at: "2026-11-14T00:36:55Z"
updated_at: "2026-11-14T00:36:55Z"
---
## Requirements

The 1.3.2 release pull request (dev -> main) could not merge: `.skald/README.md`
conflicted in the dependency graph's `class` lines.

Cause: `graph.to_mermaid` wrote one `class` line per role by iterating a
Python `set`. String hashing differs per process, so the order changed from
run to run with nothing changed. The skald workflow re-renders the board on
main after each release merge, saw a "different" board, and committed it
`[skip ci]` (73ea3b1 for 1.3.0, c2c236b for 1.3.1). Those commits were never
merged back into dev. This time dev's own render touched the same lines,
and GitHub's merge, which does not run the skald merge driver, stopped on
them.

- Emit the `class` lines in the fixed role order (backlog, ready, active,
  done, closed, unknown), then any other role sorted.
- A test renders the graph under several `PYTHONHASHSEED`s and requires one
  output.
- Merge main into dev so the release pull request merges.

## Acceptance
- [x] `to_mermaid` output is identical across hash seeds; the test fails without the fix.
- [x] The whole rendered board (`skald render --stdout`, md and html) is identical across seeds on this repository.
- [x] main's render commits are merged into dev and the board re-rendered.
- [x] CHANGELOG updated.

## [claude] 2026-11-14 00:36 UTC · handoff
Done. graph.to_mermaid iterates the styles dict's role order, then other roles sorted, instead of the used-roles set. tests/test_graph.py renders under 8 hash seeds and requires one output (8 distinct outputs without the fix). skald render --stdout md and html identical across 10 and 6 seeds on this repository. main merged into dev (a3ac870), board re-rendered. Shipped in 1.3.2 if merged before the release pull request.
