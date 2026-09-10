---
title: "Board polish: dark mode, layout fixes, keyboard access, empty states"
status: "done"
rank: 230
tags: ["ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-07T01:29:56Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

Found while verifying the board in a real browser with Tailwind loaded (f7674b).

- Graph button label disappears when the graph is active (white text on the retained white background).
- Modal overflows horizontally: the four-field row needs min-w-0 on its inputs; the header metadata wraps badly.
- Columns are a fixed 18rem, so five columns clip at 1440px. Let them flex between a minimum and maximum width.
- No dark mode. Theme through a small set of CSS variables (system preference plus a manual toggle) rather than dark: variants on every class.
- Cards are not keyboard reachable. Make cards and ready rows focusable, Enter opens.
- Empty board shows five empty columns and nothing else. Add a hint pointing at New story and skald new.
- Stack columns vertically on narrow screens.
- Toast when the backlog changes on disk outside the board (hook, workflow, CLI).

## Changelog

The board has a dark theme that follows the operating system or a header toggle, columns that flex to the window, a story dialog that no longer overflows, keyboard access to cards, and empty-state messages.

## Acceptance
- [x] Graph toggle stays readable when active
- [x] Modal has no horizontal scrollbar at 1440px and fields stay inside it
- [x] Five default columns fit at 1440px without horizontal scroll
- [x] Dark theme follows the OS and can be forced from the header; choice persists
- [x] Tab reaches cards; Enter opens the story
- [x] Empty project shows a hint
- [x] Narrow viewport stacks columns
- [x] External change to a story file shows a toast

## [claude] 2026-09-07 01:37 UTC · result
Verified in headless Chromium with the real Tailwind and marked assets: board and modal have no horizontal overflow at 1440px, Tab reaches cards and Enter opens them, the theme choice persists in localStorage, the phone viewport stacks columns, an empty project shows the hint, and a CLI note produced the on-disk change toast. Theme is CSS custom properties plus data-theme (D41).
