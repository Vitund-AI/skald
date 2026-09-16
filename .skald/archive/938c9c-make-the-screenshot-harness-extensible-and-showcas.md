---
title: "Make the screenshot harness extensible and showcase the new features"
status: "done"
rank: 90
tags: ["area:docs"]
blocked_by: []
assignee: "claude"
released: "0.8.0"
created_at: "2026-09-16T05:37:18Z"
updated_at: "2026-09-16T07:11:46Z"
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
- [x] capture.py is driven by an extensible shot list; adding a shot is one entry
- [x] the existing board-dark/board-light/story shots are still produced (re-captured from the enriched demo: cards now also carry an area: facet, so the hero shows facet filtering too — an improvement, not a regression)
- [x] make-demo.sh gives swimlanes at least two lanes with progress bars, deterministically
- [x] a swimlanes screenshot is captured and referenced in docs/board.md
- [x] docs/images/README.md explains the shot list
- [x] offline assets stay gitignored; harness runs in-sandbox with them present
- [x] python3 -m unittest green, ruff clean

## [claude] 2026-09-16 06:01 UTC · handoff
Built. Extended the existing docs/images harness. capture.py refactored to a declarative SHOTS list (name/size/theme/setup(page)/full_page) — adding a showcase is one entry; setup() drives the board to a view (open_story, swimlanes). make-demo.sh enriched with an area: facet across all stories (area:net x5, area:platform x5, area:docs x1) so 'swimlanes by area' shows three lanes with per-lane progress bars, deterministically. New docs/images/swimlanes.png captured full-height and referenced in docs/board.md; board-dark/light/story re-captured (cards now also show an area: chip and the header an area: filter — richer, on-message). docs/images/README.md documents the shot list. Verified the whole pipeline in-sandbox: fetched tailwind.js/marked.js via the proxy (gitignored) and the fonts/ were present, so capture.py served them from disk and produced fully-styled shots at DPR 2; eyeballed board-dark and swimlanes. 184 tests, ruff clean (incl capture.py). Offline assets stay gitignored. Note: capture.py/make-demo.sh live under docs/ so CI ruff (src tests examples scripts) does not lint them; kept clean anyway.
