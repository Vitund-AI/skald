---
title: "Settings modal and API for defaults and per-project options"
status: "done"
rank: 40
tags: ["area:board", "epic:feature-flags"]
blocked_by: ["716fe0"]
assignee: "claude"
released: "0.8.0"
created_at: "2026-09-14T23:46:45Z"
updated_at: "2026-09-16T07:11:46Z"
---
## Requirements

A settings modal in the board UI to manage the machine-local feature flags
from story 716fe0: the global defaults, and the overrides for the current
project. Plus the HTTP endpoints behind it.

Design property: **flags are data; the modal is generic.** The API ships the
`FEATURE_DEFAULTS` catalog and the resolved values; the modal renders one
control per catalog entry, so a future flag appears automatically with no UI
change.

## Scope

- Server (`server.py`):
  - Extend the board payloads that already return `settings: ws.user.all()`
    to also carry the resolved `features` for the current project and the
    `feature_catalog` (name, label, help, default).
  - `PUT /api/settings` writes global settings (incl. `features` defaults).
  - `PUT /api/projects/<name>/settings` writes that project's `features`
    overrides (set true/false, or clear a key to inherit).
  - Validate against the catalog; reject unknown flags; token-guarded like
    the other write routes.
- Board (`web/index.html`):
  - A gear icon in the header opens a modal with two panels driven by the
    same catalog:
    - **Defaults** (global): a toggle per feature flag, plus the existing
      prefs (push, author, stale_days) if trivial to include.
    - **This project**: the same flags, each tri-state — *inherit (default: X)*
      / force on / force off — writing to the per-project block.
  - Reflects saved state, no reload needed; matches the Vitund token theme,
    dark-first; keyboard-dismissable; works at phone width.

## Out of scope

- The specific flags themselves and their consumers (each is its own story).

## Acceptance
- [x] GET board payload includes resolved features + catalog
- [x] PUT /api/settings and PUT /api/projects/<name>/settings write and validate
- [x] gear-icon modal renders defaults + per-project panels from the catalog
- [x] per-project control is tri-state (inherit / on / off) and persists
- [x] theme-consistent, dismissable, responsive
- [x] server tests for both endpoints (happy path, unknown flag, auth)
- [x] docs/board.md documents the settings modal
- [x] python3 -m unittest green, ruff clean

## [claude] 2026-09-15 01:14 UTC · handoff
Built the settings modal and its API. Server: GET/PUT /api/settings (global) and GET/PUT /api/projects/<name>/settings (per-project); both return a features payload of {catalog, resolved, global, project} so the modal needs no second request. A feature value of null clears a scope; the global endpoint also takes the flat prefs (author/push/stale_days), the per-project one only features; a bad batch is validated before any write lands. The board payload gains the same features block (resolved for the project) for story f9e295. Board: a header gear opens a modal with a Defaults panel (on/off per flag + author/push/stale_days) and a This-project panel (inherit/on/off select per flag, hidden in All-projects), both generated from the catalog. Verified with a live-browser Playwright run (global toggle, per-project tri-state, stale-days all persisted; Esc and X close). Docs: api.md endpoint rows, board.md Settings section, SPEC 7 and 8. 175 tests (added TestSettings), ruff clean.
