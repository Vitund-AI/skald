---
title: "Drag a card between facet swimlanes to reassign its tag; show a card in every lane it belongs to"
status: "review"
rank: 20
tags: ["area:board"]
blocked_by: []
assignee: "agent"
created_at: "2026-09-16T22:55:42Z"
updated_at: "2026-09-16T23:04:37Z"
---
## Requirements

In swimlane-by-facet mode, dragging a card to another lane reassigns the grouping tag; the grouping key tells us which tag to rewrite.

- Render a card in EVERY lane whose key:value it holds (today only the first, via facetOf, so lane counts and visible cards disagree for multi-valued facets). The 'no <key>' lane is stories with zero values for the key.
- A small multi-lane icon on the card when it holds >1 value for the current grouping key, tooltip 'In N <key> lanes'.
- On drop into a different lane: remove key:source, add key:target (drop into 'no <key>' removes key:source only); sent with status/order in the existing single PATCH. Other values of the same key untouched.
- Capture the source lane on dragstart (the dragged instance's lane).
- Parent lanes (__parent__) stay non-reassignable (that would be reparenting).
- Multi-select batch drag uses the drag's origin lane as the source value.

No new API (PATCH already takes tags+status+order together); facet active-limits already enforced server-side. Standard library only.
