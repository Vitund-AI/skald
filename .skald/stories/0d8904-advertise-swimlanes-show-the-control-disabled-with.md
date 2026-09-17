---
title: "Advertise swimlanes: show the control disabled with a hint when no facets exist"
status: "idea"
rank: 10
tags: ["area:board", "release:0.9.0"]
blocked_by: []
created_at: "2026-09-16T05:25:26Z"
updated_at: "2026-09-17T04:46:24Z"
---
## Requirements

Make the swimlanes feature discover itself. Today the "Swimlanes by…"
control (`#group-by` in the header) is hidden entirely until a story carries
a `key:value` facet tag or has a parent (web/index.html renderFacetControls,
~line 659: `gb.classList.add("hidden")`), so a user with an untagged backlog
never learns it exists. An engaged maintainer missed it for days.

## Change

When there are no facets and no parents, keep the control **visible but
grayed/disabled**, showing a single placeholder like "Swimlanes by…" and a
hover tooltip that briefly teaches it, e.g. "Add key:value tags (epic:auth,
area:web) to a few stories to group the board into swimlanes." When facets or
parents appear, it enables with the real options, exactly as now.

Only on a real project board — keep it hidden in the All-projects view (refresh
returns early there and renderFacetControls is not called; add an explicit
toggle in applyProject so switching to All-projects hides it).

### Tooltip-on-disabled gotcha

Some browsers do not show a `title` tooltip on a truly `disabled` <select>.
Two safe options: (a) wrap the select in a span that carries the title and
disable the select, or (b) keep the select enabled but visually grayed
(opacity + cursor-help) with only the placeholder option. Pick one that shows
the hint reliably across browsers; verify by hover.

## Docs image (separate deliverable)

Capture a screenshot of the board in swimlanes mode for the docs (board.md /
README), showing lanes with their per-lane progress bars. NOTE: this cannot be
produced in the agent sandbox — the board loads Tailwind from a CDN that is
blocked here, so a headless screenshot renders unstyled. Capture it in a real
browser (maintainers machine) or treat the image as a manual follow-up;
the code change above does not depend on it.

## Acceptance
- [ ] with no facets/parents on a project board, the swimlanes control is visible, disabled/grayed, and shows a teaching tooltip
- [ ] with facets or parents, it enables with the real swimlane options (unchanged behaviour)
- [ ] hidden in the All-projects view
- [ ] the tooltip is reliably visible on hover in the disabled state (gotcha handled)
- [ ] docs/board.md mentions that swimlanes advertise themselves; add the swimlanes screenshot (or leave a TODO if captured out of band)
- [ ] python3 -m unittest green, ruff clean

## Changelog

The board now shows the "Swimlanes by…" control even before any story is
tagged, grayed out with a hint to add `key:value` tags, so the swimlanes
feature is discoverable instead of hidden until the first facet exists.

## [claude] 2026-09-16 05:54 UTC · decision
Parked (moved back to idea) by decision. The maintainer's UX concern: dynamically appearing/disappearing header controls shift the layout and break spatial muscle memory. Reframe agreed: the shift already happens today (swimlanes pops in/out with facets); 'always visible + disabled' would actually FIX the shift, not cause it. But a one-off stable-slot change to only swimlanes is the least defensible version. If we ever adopt 'stable header slots' as a principle, do it consistently (swimlanes + a facet-filter entry both get fixed slots), or use a stable 'View ▾' menu that never moves. For now, discoverability is delivered by the docs screenshot (938c9c) with zero UI risk; this story waits until/unless we commit to the stable-slots principle.
