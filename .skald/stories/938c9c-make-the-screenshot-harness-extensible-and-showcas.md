---
title: "Make the screenshot harness extensible and showcase the new features"
status: "idea"
rank: 90
tags: ["area:docs"]
blocked_by: []
created_at: "2026-09-16T05:37:18Z"
updated_at: "2026-09-16T05:37:39Z"
---
## Requirements

Turn the existing screenshot tooling into the extensible demo+capture harness
the maintainer described: add a feature to the demo and a line to a shot list,
re-run, done.

## What already exists (extend, do not rebuild)

- `docs/images/make-demo.sh` builds a deterministic "WireGuard overlay" demo
  on the lifecycle columns (epic:overlay facet, children, a claim + checklist,
  questions, blocked, done, dated notes).
- `docs/images/capture.py` captures board (dark+light) and the story dialog in
  headless Chromium at DPR 2.
- `docs/images/README.md` documents an offline-asset workaround: local
  `tailwind.js`, `marked.js`, and `fonts/` (all gitignored) that capture.py
  serves from disk, so it runs behind a proxy/sandbox. Verified: the assets
  fetch through the proxy and the fonts are already present, so styled shots
  are capturable in-sandbox.

## Changes

1. Refactor `capture.py` to a declarative SHOTS list — each shot is
   `{name, size, theme, setup(page)}` where setup drives the page to the view
   (open the swimlanes select, the graph, the releases view, the settings
   modal, a story dialog, ...). Adding a showcase = one list entry. Keep the
   existing board-dark/board-light/story outputs identical.
2. Enrich `make-demo.sh` so swimlanes are illustrative: add a facet with
   several values (e.g. `area:net`, `area:ops`, `area:docs`) across the
   stories so "swimlanes by area" shows multiple lanes with per-lane progress
   bars. Keep it deterministic (fixed --created-at/--at timestamps). Do not
   regress the existing board/story shots.
3. Add a swimlanes shot and wire the image into `docs/board.md` (this also
   satisfies the image half of 0d8904). Optionally add shots for the
   sessions other features (settings modal, Open in Claude Code, update
   pill) as we decide to showcase them.
4. Update `docs/images/README.md` to describe the shot list and how to add one.

## Acceptance
- [ ] capture.py is driven by an extensible shot list; adding a shot is one entry
- [ ] the existing board-dark/board-light/story images are still produced unchanged
- [ ] make-demo.sh gives swimlanes at least two lanes with progress bars, deterministically
- [ ] a swimlanes screenshot is captured and referenced in docs/board.md
- [ ] docs/images/README.md explains the shot list
- [ ] offline assets stay gitignored; harness runs in-sandbox with them present
- [ ] python3 -m unittest green, ruff clean
