---
title: "Opt-in update check: show an update-available icon on the board"
status: "idea"
rank: 100
tags: ["area:board", "epic:feature-flags"]
blocked_by: []
created_at: "2026-09-16T02:08:34Z"
updated_at: "2026-09-16T02:08:34Z"
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
- [ ] server-side version check via urllib against the PyPI JSON API, stdlib only
- [ ] X.Y.Z comparator with regex validation; malformed latest -> not outdated
- [ ] machine-local cache with a >= ~24h refresh window, refreshed off the request path (no board-load block)
- [ ] `update_check` flag in FEATURE_DEFAULTS defaulting False; no network call when off
- [ ] `GET /api/update` returns {enabled,current,latest,outdated,checked_at}; never 500 on network failure
- [ ] header icon appears only when outdated and the flag is on; tooltip + link + per-version dismiss
- [ ] offline / locked-down network is silent (no icon, no error)
- [ ] tests: comparator, endpoint enabled/disabled/outdated/offline (PyPI fetch stubbed, no real network in tests)
- [ ] docs: board.md (Settings + the icon), SPEC, DECISIONS entry (off-by-default), the flag catalog help
- [ ] python3 -m unittest green, ruff clean

## Changelog

The board can show an "update available" icon when a newer skald-kanban has
been released on PyPI. It is off by default and enabled per-machine or
per-project from the settings panel (`update_check`).
