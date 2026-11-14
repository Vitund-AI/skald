---
title: "Story dialog: a wide mode, tables that scroll in their own box, and a header that stays put"
status: "review"
rank: 10
tags: ["area:board"]
blocked_by: []
assignee: "claude"
created_at: "2026-11-14T02:49:02Z"
updated_at: "2026-11-14T02:53:09Z"
---
## Requirements

The story dialog is a fixed 768px (`max-w-3xl`). Two problems with it:

- **Wide content.** A Markdown table (common in stories now) wider than the
  dialog widens the whole body, not just the table. `#pane-story` is a CSS
  grid, and a grid item's min-width defaults to its content. So everything
  below the table (notes, questions, the note box) is laid out at the
  table's width, and you scroll sideways to read it. On a widescreen
  monitor the fixed width is cramped anyway.
- **Scrolling.** On a long story the header (id, dates, title, tabs, Edit,
  close) scrolls away, so closing or switching tab means scrolling back up.

Changes:

- **Wide mode:** a header button toggles the dialog between the reading
  width and nearly the whole window, capped at 100rem (1600px). The browser
  remembers the choice (localStorage, guarded). Shown where there is room
  for it (lg and up). Shortcut `w`. Default stays narrow: prose reads
  better at that measure.
- **Contained overflow:** the story and edit panes' grid column is
  `minmax(0, 1fr)`, so nothing in them can widen the dialog. Tables scroll
  in their own box (`display: block; overflow-x: auto`), like code blocks.
  Long unbroken words (URLs, paths) wrap.
- **Table styling:** borders, cell padding, a tinted header row; column
  alignment from the Markdown (`:--:`) kept.
- **Pinned header:** the header sticks to the top while the body scrolls,
  with a shadow once scrolled. While scrolled, the title is clamped to two
  lines (full title in its tooltip) so a long title cannot eat a phone
  screen.

## Acceptance
- [x] A wide table scrolls inside its own box; notes and the note box below it wrap at the dialog's width.
- [x] The wide toggle (button and `w`) widens the dialog on a large screen and is remembered across reloads; the narrow width stays the default.
- [x] The header stays visible while scrolling a long story, at widescreen, laptop and phone widths, in the Story and History tabs and in edit mode.
- [x] Tables have borders and padding; Markdown column alignment is respected.
- [x] docs/board.md, the help's shortcut list and CHANGELOG updated.

## [claude] 2026-11-14 02:53 UTC · handoff
Done in src/skald/web/index.html.
- Wide mode: #m-wide button (lg and up) and `w` toggle #modal-card.wide (max-width 100rem); remembered in localStorage skald.modalWide, guarded.
- Overflow: #pane-story/#pane-edit grid-template-columns minmax(0, 1fr) (the root cause: a grid item's min-width was its content); .md table display:block + overflow-x:auto; .md overflow-wrap: break-word.
- Tables: borders, padding, tinted header, th left-aligned only without an align attribute; on phones (<=640px) cells have min-width 6rem so a scrolling table isn't one word per line.
- Header: #modal-head sticky with bg; the title moved to its own full-width row (it was squeezed beside the tabs, very tall on a phone); .scrolled (set from the card's scroll event) adds a shadow and clamps the title to 2 lines, full title in its tooltip.
Checked with Playwright at 1920x1080 (wide), 1280x800 and iPhone 13, dark and light: notes and note box at the dialog width with a wide table above; table scrolls only on the phone; header pinned in Story, History and edit mode; wide survives a reload; typing w in the note box does not toggle.
