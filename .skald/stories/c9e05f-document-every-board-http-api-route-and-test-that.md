---
title: "Document every board HTTP API route, and test that docs/api.md stays complete"
status: "ready"
rank: 20
tags: ["area:docs", "release:1.0.0"]
blocked_by: []
created_at: "2026-10-04T02:42:04Z"
updated_at: "2026-10-04T02:42:04Z"
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
- A note at the top of docs/api.md: the API is internal to the board, not
  covered by the 1.x compatibility promise, and may change in any release;
  scripts should use `--json` or MCP. (0a2011 Q1, decided 2026-10-04: keep
  it internal, document it for our own reference, revisit after 1.0.)

## Acceptance
- [ ] every route in server.py has a row in docs/api.md with method, path, params/body, and response
- [ ] auth and the Host check are described once, near the top
- [ ] a test fails when a server route is missing from docs/api.md
- [ ] the internal-API note is at the top of docs/api.md
- [ ] python3 -m unittest green, ruff clean
