---
title: "Board: reset the card modal scroll to the top when a story is opened"
status: "ready"
rank: 10
tags: ["area:board"]
blocked_by: []
created_at: "2026-09-21T20:19:31Z"
updated_at: "2026-09-21T20:19:31Z"
---
## Requirements

Bug (minor UI). Open a card's detail modal, scroll down to the bottom, close it. Open a different card: the modal is still scrolled to where the previous card was, instead of showing the top of the new story.

Cause: the modal's scroll container — the inner div of #modal (`<div class="... max-h-full overflow-y-auto">`, a direct child of #modal, no id) — keeps its scrollTop across opens. Nothing resets it.

Fix: on opening a card, set that container's scrollTop = 0. showModal() is the right place — it runs on a fresh open but NOT on the in-place openModal() refresh after a save (that path does `if (!modal.classList.contains('flex')) showModal()`), so putting the reset there resets on open and preserves position on save/refresh. Grab the element as `modal.firstElementChild` (or give it an id) and set scrollTop = 0 in showModal().

Also consider the in-modal navigation case: clicking a story-id link inside an open modal calls openModal(id) while it is already open, so showModal() does not run and the scroll would not reset. If we want that to jump to the top too, reset in openModal when the loaded id differs from the one currently shown.

area:board. Client-only (web/index.html). No test harness for the board, so verify in a headless browser.
