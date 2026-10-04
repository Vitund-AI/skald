# HTTP API

> **Internal to the board.** This API is what the board's page calls. It is
> documented in full for reference, but it is **not** part of the 1.x
> compatibility promise and may change in any release. Scripts and agents
> should use the CLI's `--json` output or the MCP server (`skald mcp`), which
> are covered.

The board server exposes everything the board does as JSON over HTTP. It
binds to `127.0.0.1` by default; every write endpoint changes files in the
repository. The routes are listed in `Handler._dispatch` in
`src/skald/server.py`, and `tests/test_api_docs.py` fails if a route there is
missing from this page or a route here no longer exists.

## Authentication

Every `/api/` route except `GET /api/health` and `/api/session` needs
the machine's token, either as `Authorization: Bearer <token>` or as the
`skald_session` cookie the board holds. `skald server token` prints the
token; `--rotate` replaces it. Requests without it get 401. The `Host`
header must name this machine (`localhost`, `127.0.0.1`, `::1`, or the bound
address) or the request gets 403; that closes DNS rebinding. The Host check
applies to every `/api/` route except `GET /api/health`, and is skipped when
the server is bound to all interfaces (`--host 0.0.0.0`), where the token is
the only gate.

```sh
TOKEN=$(skald server token)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8321/api/projects
```

`POST /api/session` with `{"token": "..."}` sets the cookie (`HttpOnly`,
`SameSite=Strict`, `Path=/`) and returns `{ok: true}`, or 401 for a wrong
token; `DELETE /api/session` clears it. Any other method is 405. The board
sends this itself when `skald open` hands it the key in the URL fragment.

## Conventions

- All request and response bodies are JSON, except the board's own page and
  assets and the event stream.
- `HEAD` is answered as `GET`.
- Errors are `{"error": "..."}` with a 4xx or 5xx status: 400 for a bad
  request, 401 without the token, 403 for a foreign `Host`, 404 for an
  unknown route, project, checkout, or story, 405 for a method a route does
  not take, 409 for a conflict (a body that changed on disk, a story others
  depend on), 422 for a corrupt story file, 500 for git or configuration
  failures, and 503 when another command held the project's mutation lock for
  longer than `SKALD_LOCK_TIMEOUT` (SPEC section 4.7).
- Project names come from the machine-local registry; the API never accepts a
  filesystem path.
- Every `/api/projects/<p>/...` route accepts `?checkout=ID` to act on another
  checkout of the project (a worktree or a second clone) instead of the
  primary. Ids come from `GET /api/projects/<p>/checkouts`, and an unknown id
  is 404.
- Skald warnings come back inside results as `warnings`, not as errors.

## The board's page and assets

| Method and path | Body | Result |
| --- | --- | --- |
| `GET /`, `GET /index.html` | | the board, `text/html` |
| `GET /theme.css` | | the user's `SKALD_HOME/theme.css`, loaded after the page's own tokens; empty when there is none |
| `GET /favicon.ico` | | 204, any method |

## Server, settings, and help

| Method and path | Body | Result |
| --- | --- | --- |
| `GET /api/health` | | `{ok, version, pid, installed, stale}`; open, no token, no Host check. `installed` is the on-disk package version (`null` if unreadable) and `stale` is true when it is a final release strictly newer than the running `version` — the board banner, `skald server status`, and `skald doctor` read it to prompt `skald server restart` after an upgrade |
| `POST /api/session`, `DELETE /api/session` | `{token}` | Sets or clears the session cookie (see above); open, but the token must match |
| `GET /api/projects` | | `{projects: [{name, path, exists, registered_at, checkouts}], settings}`; `checkouts` lists the non-primary ones |
| `GET /api/update[?project=NAME]` | | `{enabled}` alone when the `update_check` flag is off; otherwise `{enabled, current, latest, outdated, checked_at}` from a once-a-day cached PyPI lookup (a final `X.Y.Z` newer by numeric tuple is `outdated`; network failures are swallowed, so `latest` may be null) |
| `GET /api/settings[?project=NAME]` | | `{settings, features}`; `features` is `{catalog: [{name, label, help, default}], resolved, global, project}` — `global`/`project` map each flag to its explicitly stored value or `null` (inherit), `resolved` to the effective value |
| `PUT /api/settings`, `PATCH` | `{features?: {name: true|false|null}, author?, push?, stale_days?, ...}` | writes global settings (`PUT` and `PATCH` are the same: only the keys sent change); a feature `null` clears it, as does `null` for a flat preference; returns `{settings, features}` |
| `GET /api/help` | | `{version, commands: [{name, help, usage, arguments, subcommands}]}`, the CLI reference read from the argparse parser |
| `GET /api/ready` | | `{stories, warnings}`: ready, unblocked stories across all registered projects |

## A project

| Method and path | Body | Result |
| --- | --- | --- |
| `GET /api/projects/<p>/board` | | `{project, path, checkout: {id, path, primary}, columns, default_status, stories, facets, facet_limits, warnings, git, repo_slug, identity, settings, features, version}`; `git` is `{available, branch, head, changes}`; `facets` leaves out keys in `facets.exclude`; `features` is resolved for this project (see `GET /api/settings`); `repo_slug` is `owner/name` for a GitHub remote, else null |
| `GET /api/projects/<p>/board?ref=REF` | | a read-only snapshot of branch `REF`: `{project, path, columns, stories, facets, warnings, git, repo_slug, identity, settings, features, version, readonly: true, ref, sha}` |
| `GET /api/projects/<p>/settings`, `PUT`, `PATCH` | `{features: {name: true|false|null}}` | the project's feature overrides; `PUT`/`PATCH` set or (with `null`) clear them and return `{features}`; accepts only `features` |
| `GET /api/projects/<p>/checkouts` | | `{current, checkouts: [{id, path, branch, changes, primary, worktree, exists}]}`; `current` is the checkout the request acted on |
| `GET /api/projects/<p>/branches` | | `{available, current, branches: [{name, sha, remote, current, stories, only_there, only_here, differ}], elsewhere, claims}`; `elsewhere` lists ids that exist only on other branches; `claims` maps a story id to the active claims on other branches and in other checkouts (`{branch, assignee, status, checkout?}`), uncommitted ones included. Outside git: `{available: false, current: null, branches: [], elsewhere: []}` |
| `GET /api/projects/<p>/version` | | `{version}`, a hash that changes whenever any story file or `config.json` changes |
| `GET /api/projects/<p>/events` | | server-sent events (`text/event-stream`): `hello` on connect and `change` whenever the version hash changes, each with data `{version}`, plus a `: keepalive` comment about every 30 polls |
| `GET /api/projects/<p>/releases` | | `{releases: [{version, stories: [{id, title, status, tags, assignee}]}]}`, what shipped grouped by version, newest first (done-role archived stories; won't-do excluded) |
| `GET /api/projects/<p>/templates` | | `{templates}`, the names under `.skald/templates/` |
| `POST /api/projects/<p>/archive` | `{ids?}` | `{archived: [ids]}`; without `ids`, every done or closed story; with them, only those, 400 if any is not in a terminal column |
| `GET /api/projects/<p>/git` | | `{available, branch, head, changes, push_enabled, identity}` |
| `POST /api/projects/<p>/git/commit` | `{message?, push?}` | `{sha, message, pushed, output}`; commits `.skald/` and the rendered snapshot; pushes only when `push` is sent and the `push` setting is on; 500 outside a git repository |

## Stories

| Method and path | Body | Result |
| --- | --- | --- |
| `POST /api/projects/<p>/stories` | `{title, status?, tags?, blocked_by?, body?, assignee?, template?, parent?, inherit?}` | 201, `{story, warnings}`; with `parent`, the parent's facet tags are copied unless `inherit` is false |
| `GET /api/projects/<p>/stories/<id>[?ref=REF]` | | the story with `body`, `body_sha256`, `children` (`[{id, title, status, done}]`), and `parent_story` (`{id, title, status}`) when it has a parent; with `ref`, as it is on that branch, with `body` and `body_sha256` but no family |
| `PATCH /api/projects/<p>/stories/<id>` | any of `{title, status, rank, tags, blocked_by, assignee, parent, order}` | `{story, warnings}`; `parent: "-"` clears it; any other field is 400. `tags` and `blocked_by` replace the whole list |
| `PUT /api/projects/<p>/stories/<id>/body` | `{body, base_sha256}` | the story with body, or 409 if the body changed on disk since `base_sha256` |
| `POST /api/projects/<p>/stories/<id>/notes` | `{text, author?, kind?, question?, all?, withdraw?}` | 201, the story with body. `question` (a stable number, `3` or `"Q3"`) or `all: true`, with `kind` `decision` or omitted, writes the decision that closes those questions, as `skald answer`; `withdraw: true` records a drop. A decision without either closes nothing. `author` defaults to the board's identity |
| `POST /api/projects/<p>/stories/<id>/claim` | `{author?}` | `{story, warnings}`; `author` defaults to the board's identity; warns when the story is claimed in another checkout or on another branch |
| `GET /api/projects/<p>/stories/<id>/history[?children=0]` | | `{history: [{sha, date, author, subject}], commits: [{..., story}], children}`; `commits` include those referencing the story's children, each tagged with `story`, unless `children=0` |
| `DELETE /api/projects/<p>/stories/<id>[?force=1]` | | 204, or 409 if other stories depend on it; `force=1` deletes anyway and removes the references |

`order` is the full ordered list of ids for the story's column. Sending
`status` and `order` together moves and reorders in one request; the board
uses this for drag and for batch moves.

A story object carries the frontmatter fields plus `id`, `filename`,
`archived`, `checklist` (`{done, total}`), `acceptance` when a
`## Acceptance` section exists, `deps` (one entry per blocker with its
`state` and whether it is `satisfied`), `blocked`, `stale`, and `role` (the
column's role).

Board edits send whole values (a `tags` list, say), so an edit made from a
board that has not refreshed can overwrite a newer change; the live event
stream keeps that window small. Concurrent writes from the CLI, MCP, and the
board otherwise take turns on the project's mutation lock (SPEC section 4.7).
