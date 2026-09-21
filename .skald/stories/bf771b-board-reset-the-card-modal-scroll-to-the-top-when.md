---
title: "Board: reset the card modal scroll to the top when a story is opened"
status: "review"
rank: 60
tags: ["area:board"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-21T20:19:31Z"
updated_at: "2026-09-21T20:36:56Z"
---
## Requirements

Bug (minor UI). Open a card's detail modal, scroll down to the bottom, close it. Open a different card: the modal is still scrolled to where the previous card was, instead of showing the top of the new story.

Cause: the modal's scroll container — the inner div of #modal (`<div class="... max-h-full overflow-y-auto">`, a direct child of #modal, no id) — keeps its scrollTop across opens. Nothing resets it.

Fix: on opening a card, set that container's scrollTop = 0. showModal() is the right place — it runs on a fresh open but NOT on the in-place openModal() refresh after a save (that path does `if (!modal.classList.contains('flex')) showModal()`), so putting the reset there resets on open and preserves position on save/refresh. Grab the element as `modal.firstElementChild` (or give it an id) and set scrollTop = 0 in showModal().

Also consider the in-modal navigation case: clicking a story-id link inside an open modal calls openModal(id) while it is already open, so showModal() does not run and the scroll would not reset. If we want that to jump to the top too, reset in openModal when the loaded id differs from the one currently shown.

area:board. Client-only (web/index.html). No test harness for the board, so verify in a headless browser.

## [claude] 2026-09-21 20:36 UTC · handoff
Fixed in src/skald/web/index.html: openModal() now captures the previously-open story id and resets the scroll container (modal.firstElementChild) to scrollTop 0 when the opened id differs from it — for both the new-story branch and the existing-story branch. Keying on id-change means the in-place refresh after a save or note-append (openModal(state.modal), same id) preserves the reader's position, while opening or switching to a different story starts at the top. Covers the reported close-then-open case and the in-modal story-link navigation case. Verified with a headless Chromium (Playwright) test driving the real board: (1) scroll a tall story to the bottom, close, open a different tall story -> scrollTop 0; (2) same story note-append refresh preserves scrollTop; both stories confirmed to overflow so a stale position would not auto-clamp. python3 -m unittest (198), ruff, skald docs --check all green.
