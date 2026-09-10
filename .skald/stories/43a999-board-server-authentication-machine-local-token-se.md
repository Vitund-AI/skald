---
title: "Board server authentication: machine-local token, session cookie, bearer header"
status: "done"
rank: 320
tags: ["core", "ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-09T22:21:58Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

A localhost bind keeps the network out, not other local users and not the browser: any web page can send requests to 127.0.0.1:8321, and the API reads JSON bodies regardless of content type, so a form post from a hostile page can write today.

- A random token is generated on first server start and stored in the machine-local directory as token (mode 0600, directory 0700). skald server token prints it; --rotate replaces it and invalidates existing sessions.
- Every /api route except /api/health and POST /api/session requires Authorization: Bearer TOKEN or the session cookie. Unauthorised requests get 401 with a message pointing at skald open.
- skald open and serve --open open http://host:port/#key=TOKEN. The page reads the fragment, posts it to /api/session, gets an HttpOnly SameSite=Strict cookie, and rewrites the URL so the key leaves the address bar.
- The server checks the Host header is loopback (or the bound host) on every /api route, closing DNS rebinding.
- An unauthenticated board shows one line: open it with skald open. The token is never displayed.
- CLI, MCP, hooks, and workflows are unaffected: they read files, not HTTP.

## Changelog

The board server now requires a per-machine token. skald open handles it for you; scripts pass Authorization: Bearer with the value from skald server token. This closes cross-site requests from web pages and other local users.

## Acceptance
- [x] Requests without the token get 401; with the header or cookie they succeed; /api/health stays open
- [x] POST /api/session with the token sets the cookie; the board strips the key from the URL
- [x] A non-loopback Host header is refused
- [x] skald server token prints and --rotate replaces the token
- [x] Docs: board, api, troubleshooting, SPEC, CHANGELOG, DECISIONS

## [claude] 2026-09-09 22:31 UTC · result
Implemented: token in the machine-local dir (0600), Bearer header or skald_session cookie checked with compare_digest, Host check (403), POST/DELETE /api/session, key in the URL fragment from skald open, skald server token [--rotate], server re-reads the token on change. Verified: 124 unit tests; curl (401 without token, 200 with bearer, 403 on bad Host); Playwright with fresh page loads (no key and wrong key show the locked overlay; right key loads 46 cards, strips the fragment, sets an HttpOnly SameSite=Strict cookie; reload and a new navigation without the key still load). Docs: board, api, troubleshooting, getting-started, multi-project, SPEC 7, CHANGELOG, D48.
