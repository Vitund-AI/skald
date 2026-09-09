# HTTP API

The board server exposes everything the board does as JSON over HTTP. It
binds to `127.0.0.1` by default and has no authentication; every write
endpoint changes files in the repository.

All request and response bodies are JSON. Errors are `{"error": "..."}` with
a 4xx or 5xx status: 400 for a bad request, 404 for an unknown project or
story, 409 for a conflict (a body that changed on disk, a story others depend
on), 422 for a corrupt story file, 500 for git or configuration failures.
Project names come from the machine-local registry; the API never accepts a
filesystem path. Skald warnings come back inside results as `warnings`, not
as errors.

| Method and path | Body | Result |
| --- | --- | --- |
| `GET /api/health` | | `{ok, version, pid}` |
| `GET /api/projects` | | `{projects, settings}` |
| `GET /api/help` | | `{version, commands: [{name, help, usage, arguments, subcommands}]}`, the CLI reference read from the argparse parser |
| `GET /api/ready` | | ready, unblocked stories across all projects |
| `GET /api/projects/<p>/board[?ref=REF]` | | `{columns, stories, facets, git, identity, settings, version, warnings}`; `git` carries `branch`, `head`, and `changes`; with `ref`, a read-only snapshot of that branch |
| `GET /api/projects/<p>/branches` | | `{current, branches: [{name, sha, remote, stories, only_there, only_here, differ}], elsewhere, claims}` |
| `GET /api/projects/<p>/version` | | a hash that changes whenever any story file changes |
| `GET /api/projects/<p>/events` | | server-sent events: `hello` on connect, `change` whenever the hash changes |
| `POST /api/projects/<p>/stories` | `{title, status?, tags?, blocked_by?, body?, assignee?, template?}` | 201, `{story, warnings}` |
| `GET /api/projects/<p>/stories/<id>[?ref=REF]` | | story with `body`, `body_sha256`, and `deps`; with `ref`, as it is on that branch |
| `PATCH /api/projects/<p>/stories/<id>` | any of `{title, status, rank, tags, blocked_by, assignee, order}` | `{story, warnings}` |
| `PUT /api/projects/<p>/stories/<id>/body` | `{body, base_sha256}` | story, or 409 if the body changed on disk |
| `POST /api/projects/<p>/stories/<id>/notes` | `{text, author?, kind?}` | 201, story with body |
| `POST /api/projects/<p>/stories/<id>/claim` | `{author?}` | `{story, warnings}` |
| `GET /api/projects/<p>/stories/<id>/history` | | `{history: [{sha, date, author, subject}], commits: [...]}` |
| `DELETE /api/projects/<p>/stories/<id>[?force=1]` | | 204, or 409 if other stories depend on it |
| `GET /api/projects/<p>/git` | | `{branch, changes, push_enabled, identity}` |
| `POST /api/projects/<p>/git/commit` | `{message?, push?}` | `{sha, message, pushed, output}` |
| `POST /api/projects/<p>/archive` | `{ids?}` | `{archived: [ids]}`; without `ids`, every done or closed story; with them, only those, 400 if any is not in a terminal column |
| `GET /api/projects/<p>/templates` | | `{templates}` |

`order` is the full ordered list of ids for the story's column. Sending
`status` and `order` together moves and reorders in one request; the board
uses this for drag and for batch moves.

A story object carries the frontmatter fields plus `id`, `filename`,
`archived`, `checklist` (`{done, total}`), `acceptance` when a
`## Acceptance` section exists, `deps` (one entry per blocker with its
`state` and whether it is `satisfied`), `blocked`, `stale`, and `role` (the
column's role).
