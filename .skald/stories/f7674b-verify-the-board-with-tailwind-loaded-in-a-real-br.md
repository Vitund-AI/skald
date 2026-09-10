---
title: "Verify the board with Tailwind loaded in a real browser"
status: "review"
rank: 220
tags: ["ui"]
blocked_by: []
created_at: "2026-09-06T02:16:15Z"
updated_at: "2026-09-08T17:24:21Z"
---
## Requirements

The board was exercised headlessly, but the sandbox could not reach the Tailwind CDN, so layout and styling were never seen by a person. Open `skald serve --open` on a machine with internet access, walk through drag, reorder, modal editing, notes, create, delete, and the filter, and fix anything that looks wrong.

## Changelog

The board was verified in a real browser with its stylesheet loaded, and the layout problems found were fixed.

## [agent] 2026-09-06 05:03 UTC
Testing the board locally

## [human] 2026-09-06 05:15 UTC
Page loads!

## [human] 2026-09-06 06:02 UTC
All looking good.

## [human] 2026-09-06 06:02 UTC
test

## [claude] 2026-09-06 07:04 UTC
The board changed a lot in 0.2: project switcher, custom columns, commit button, history tab, Markdown preview. It was exercised headlessly again but Tailwind and marked could not load in the sandbox, so please take another look with skald open.

## [claude] 2026-09-07 01:37 UTC · result
Rendered in the bundled Chromium with Tailwind 3.4.17 and marked served from local copies of the CDN files. Board, modal, graph, filters, and the new theme and help panel all lay out correctly; the four layout bugs found are fixed under c5f90f.
