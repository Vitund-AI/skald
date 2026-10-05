---
title: "Document every board HTTP API route, and test that docs/api.md stays complete"
status: "review"
rank: 10
tags: ["area:docs", "release:1.0.0"]
blocked_by: []
assignee: "claude"
created_at: "2026-10-04T02:42:04Z"
updated_at: "2026-10-04T17:06:05Z"
---
## Requirements

The board's HTTP API should be documented whether or not 1.x promises to
keep it stable (that call is 0a2011's Q1). docs/api.md has 27 route rows
today; the server (`_dispatch` in src/skald/server.py) is the source of
truth and has grown since some rows were written.

- Audit docs/api.md against every route in server.py: method, path, query
  parameters, request body, status codes, response shape, auth (token,
  session cookie, Host check), and the SSE event stream.
- Add the missing routes and fix any that drifted.
- A test that enumerates the server's routes and fails if one is missing
  from docs/api.md, so the doc cannot fall behind again (the same idea as
  `skald docs --check` for the CLI).
- docs/api.md split into two planes (0a2011 Q1, revised 2026-10-05): a
  **data plane** stable for 1.x (auth, errors, health, projects, ready,
  version, events, the story routes) and a **board backend** that is
  internal and may change in any release. The test classifies every route
  into exactly one plane and pins the data-plane set.

## Acceptance
- [x] every route in server.py has a row in docs/api.md with method, path, params/body, and response
- [x] auth and the Host check are described once, near the top
- [x] a test fails when a server route is missing from docs/api.md
- [x] docs/api.md states the two planes at the top; the test pins the data plane
- [x] python3 -m unittest green, ruff clean

## [claude] 2026-10-04 17:06 UTC · handoff
Done. docs/api.md rewritten against Handler._dispatch: an 'internal to the board' banner (0a2011 Q1), conventions (HEAD as GET; errors 400/401/403/404/405/409/422/500/503), the board's own page and assets (/, /index.html, /theme.css, /favicon.ico), and corrected shapes that had drifted: /ready {stories, warnings}; /board adds project, path, default_status, facet_limits, repo_slug and the ?ref snapshot's own field set; /branches adds available and per-branch current; /git adds available, head; /version {version}; events data and keepalive; PATCH aliases on both settings routes; Host check skipped on 0.0.0.0. tests/test_api_docs.py reads the routes from _dispatch with ast and fails both ways (server route missing from the doc; doc route the server lacks); mutation-checked by deleting the templates row and adding a bogus POST, both caught. SPEC 7, README and docs/README rows, CHANGELOG. unittest 210 OK, ruff clean.
