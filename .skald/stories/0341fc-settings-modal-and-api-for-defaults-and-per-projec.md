---
title: "Settings modal and API for defaults and per-project options"
status: "idea"
rank: 90
tags: ["area:board", "epic:feature-flags"]
blocked_by: ["716fe0"]
created_at: "2026-09-14T23:46:45Z"
updated_at: "2026-09-14T23:46:45Z"
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
- [ ] GET board payload includes resolved features + catalog
- [ ] PUT /api/settings and PUT /api/projects/<name>/settings write and validate
- [ ] gear-icon modal renders defaults + per-project panels from the catalog
- [ ] per-project control is tri-state (inherit / on / off) and persists
- [ ] theme-consistent, dismissable, responsive
- [ ] server tests for both endpoints (happy path, unknown flag, auth)
- [ ] docs/board.md documents the settings modal
- [ ] python3 -m unittest green, ruff clean
