---
title: "Opt-in update check: show an update-available icon on the board"
status: "done"
rank: 70
tags: ["area:board", "epic:feature-flags"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-16T02:08:34Z"
updated_at: "2026-09-16T06:58:04Z"
---
## Requirements

Show an unobtrusive "update available" icon on the board when a newer
`skald-kanban` has been published to PyPI. Opt-in (off by default) because it
makes an outbound request to a third party; the feature-flag layer (716fe0)
and settings modal (0341fc) gate and toggle it.

## Where the check runs — the server, not the browser

The board server is Python and already imports `urllib.request`, so it can
query PyPI with the standard library (no new dependency). Server-side avoids
CORS (PyPI does not promise it), centralises caching/rate-limiting, and keeps
the single HTML page dumb — consistent with how render/help/version already
work.

## Mechanism

- Fetch `https://pypi.org/pypi/skald-kanban/json` with a short timeout (2-3s),
  read `info.version`.
- Compare to `__init__.__version__` with a small X.Y.Z tuple comparator (no
  `packaging` dependency; same spirit as release.sh sort -V). VALIDATE the
  fetched string against a version regex first; anything malformed -> treat as
  "no update". Never execute anything, only compare strings.
- Cache in machine-local `SKALD_HOME/update.json` = `{checked_at, latest}`.
  The endpoint serves the cache and refreshes in a background thread when it is
  stale (>= ~24h), so board load never blocks and offline just means no icon.

## Gating (privacy)

- New feature flag `update_check` in `FEATURE_DEFAULTS`, **default False**
  (opt-in). Because it phones home to PyPI, it is off until the user turns it
  on in the Settings gear (globally or per-project). DECISIONS entry for the
  off-by-default choice.
- When the flag is off, the server does no network call and the endpoint
  reports disabled.

## API

- `GET /api/update` -> `{enabled, current, latest, outdated, checked_at}`.
  Flag off or offline -> `{enabled: false}` (or latest null); never 500 on a
  network error.

## Board UI

- A small header pill/icon shown ONLY when `outdated` is true. Tooltip:
  "vX.Y.Z available - pip install -U skald-kanban"; links to the GitHub
  releases / CHANGELOG. Dismissible per-version via localStorage so it does not
  nag. Hidden entirely when the flag is off or there is no update.
- Matches the Vitund token theme, dark-first, responsive.

## Tie-ins (optional, keep tight)

- `skald doctor` already compares server-vs-package version; it can report
  "a newer release is available" using the same helper. Include if cheap.
- No CLI `--version` change and no auto-update; this only informs.

## Security / robustness

- Timeout so a slow or hung PyPI never stalls the server thread or the board.
- Validate the version string; malformed or unexpected JSON -> no update.
- Cache to avoid hammering PyPI; TLS via the system trust store.
- Handle URLError/offline/HTTP errors silently (no icon, no error toast).
- The whole feature is inert in a locked-down network and when the flag is off.

## Acceptance
- [x] server-side version check via urllib against the PyPI JSON API, stdlib only
- [x] X.Y.Z comparator with regex validation; malformed latest -> not outdated
- [x] machine-local cache with a ~24h TTL; the board never blocks on it (the page fetches /api/update lazily, not on the render path) — the refresh happens inside the handler gated by the TTL rather than a separate background thread (see note)
- [x] `update_check` flag in FEATURE_DEFAULTS defaulting False; no network call when off
- [x] `GET /api/update` returns {enabled,current,latest,outdated,checked_at}; never 500 on network failure
- [x] header icon appears only when outdated and the flag is on; tooltip + link + per-version dismiss
- [x] offline / locked-down network is silent (no icon, no error)
- [x] tests: comparator, endpoint enabled/disabled/outdated/offline (PyPI fetch stubbed, no real network in tests)
- [x] docs: board.md (Settings + the icon), SPEC, DECISIONS entry (off-by-default), the flag catalog help
- [x] python3 -m unittest green, ruff clean

## Changelog

The board can show an "update available" icon when a newer skald-kanban has
been released on PyPI. It is off by default and enabled per-machine or
per-project from the settings panel (`update_check`).

## [claude] 2026-09-16 02:23 UTC · handoff
Built. New module src/skald/update.py: parse_version (final X.Y.Z only), is_newer (numeric tuple), fetch_latest (urllib GET pypi.org/pypi/skald-kanban/json, swallows every error), and check() serving a machine-local ~24h cache (SKALD_HOME/update.json). update_check flag added to FEATURE_DEFAULTS, default False. Server: GET /api/update?project=NAME returns {enabled:false} when the flag is off, else {enabled,current,latest,outdated,checked_at}; never 500. Board: a header pill shown only when enabled+outdated (checked once per project view, off the render path so board load never blocks), links to GitHub releases (target=_blank rel=noopener), tooltip 'skald X available - pip install -U skald-kanban', per-version dismiss in localStorage. doctor reports the cached result with NO network call. Deviation from the story: the stale refresh happens inside the /api/update handler gated by the TTL, not a separate background thread — 'no board-load block' holds because the frontend fetches it lazily. Verified end to end in a real browser (off=hidden; on=pill with correct label/href/title; dismiss persists across reload) and the endpoint directly (off/on/outdated). ruff S310 waived per-file for update.py (one fixed https URL). 184 tests (test_update, a server endpoint test, a doctor cached-state test; all stub the fetch, no real network). Docs: SPEC 2.3/7, api.md, board.md; DECISIONS D67.
