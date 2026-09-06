# Skald

Kanban lite for coding agents.

Skald is a backlog tracker that lives inside your repository as Markdown
files. AI coding agents drive it from a small CLI. Humans drive it from a
local web board. There is no database, no service, and no dependency beyond
Python 3.9. The whole tool is one file.

```
.skald/
├── skald.py     # the tool: CLI, web board, agent contract
├── AGENTS.md    # what an agent needs to know, written by `init`
└── stories/     # one Markdown file per story
    └── a3f9c2-implement-wireguard-overlay.md
```

Stories are committed with the code they describe, so the board travels
with the branch and shows up in pull request diffs.

## Install

```sh
mkdir -p .skald
curl -sSL https://raw.githubusercontent.com/vitund-ai/skald/main/skald.py -o .skald/skald.py
python3 .skald/skald.py init
```

`init` creates `.skald/stories/`, writes `.skald/AGENTS.md`, and sets a local
git alias so `git skald ...` works in that clone. It is safe to run again.
Then add one line to your repository's `CLAUDE.md` or `AGENTS.md`:

> This repository tracks work with Skald. Read `.skald/AGENTS.md` before
> starting any task.

## Quick start

```sh
git skald new "Implement WireGuard overlay" --tags infra --body "Configure wg0 on every node."
git skald new "Write the network docs" --status ready --blocked-by a3f9c2
git skald ls
git skald serve --open
```

If you would rather not use the alias, every command also works as
`python3 .skald/skald.py <command>` from any directory in the repository.

An agent's session looks like this:

```sh
skald next --json          # the first ready, unblocked story
skald mv a3f9c2 in_progress
skald note a3f9c2 "Claimed. Plan: ..."
# ... write code ...
skald mv a3f9c2 review
git add .skald src && git commit
```

## Story files

```markdown
---
title: "Implement WireGuard overlay network"
status: "ready"
rank: 20
tags: ["infrastructure", "v1.0"]
blocked_by: ["7b21e0"]
created_at: "2026-09-05T10:00:00Z"
updated_at: "2026-09-06T08:12:41Z"
---
## Requirements

Configure the wg0 interface on every node...

## [agent] 2026-09-06 08:12 UTC
Claimed. Plan:
- [ ] write wg0.conf template
```

- The **frontmatter** is owned by Skald. Every value is a JSON literal, one
  field per line. Change it with the CLI or the board, never by hand.
- The **body** is free-form Markdown owned by people and agents. Edit it
  however you like. `skald note` appends a timestamped section.
- The **filename** carries the id: six hex characters plus a cosmetic slug.
- `status` is one of `backlog`, `ready`, `in_progress`, `review`, `done`.
- `rank` orders cards within a column. Lower sorts first.
- `blocked_by` is advisory. Moving a blocked story forward prints a warning
  and still succeeds.

Unknown frontmatter fields are preserved, so you can add your own.

## CLI

Any `<id>` may be a unique prefix. Every command that prints stories takes
`--json`. Exit codes: 0 success (warnings on stderr), 1 usage error or story
not found, 2 corrupt story file.

| Command | What it does |
| --- | --- |
| `init` | Create the layout, `AGENTS.md`, and the git alias. |
| `ls [--status S] [--tag T] [--unblocked] [--all]` | List stories. Hides `done` unless `--all`. |
| `next` | The first `ready`, unblocked story. Exit 1 if none. |
| `show <id>` | Print the file. `--json` adds `unmet`, `body`, and `body_sha256`. |
| `new "<title>" [--status S] [--tags a,b] [--blocked-by id,id] [--body TEXT \| -]` | Create a story and print its id. |
| `mv <id> <status>` | Change status. Warns if dependencies are unmet. |
| `set <id> title="..." rank=N` | Edit title or rank. |
| `tag <id> +tag -tag` | Add or remove tags. |
| `block <id> +id -id` | Add or remove dependencies. Cycles warn. |
| `note <id> "<text>" \| - [--as LABEL]` | Append a timestamped note. |
| `rm <id> [--force]` | Delete. Refuses if other stories depend on it. |
| `check` | Validate every file. Exit 2 on problems. Good as a pre-commit hook. |
| `serve [--port 8321] [--host 127.0.0.1] [--open]` | Start the web board. |

## Web board

`skald serve` starts a local server and serves a single-page Kanban board.
Drag cards between columns or reorder them within one. Click a card to edit
its title, status, tags, and blockers, edit the body, or append a note.
Blocked cards show a lock. Warnings appear as toasts. The board polls every
three seconds, so changes an agent makes from the CLI show up on their own.

The board uses Tailwind from a CDN, so it needs internet access for styling.
The server binds to `127.0.0.1` and has no authentication. Every write
endpoint changes files, so only expose it on other interfaces deliberately.

## HTTP API

All bodies are JSON. Errors are `{"error": "..."}` with a 4xx status.

| Method and path | Body | Result |
| --- | --- | --- |
| `GET /api/board` | | `{statuses, stories, warnings}` |
| `GET /api/stories/<id>` | | story plus `body` and `body_sha256` |
| `POST /api/stories` | `{title, status?, tags?, blocked_by?, body?}` | 201, `{story, warnings}` |
| `PATCH /api/stories/<id>` | any of `{title, status, rank, tags, blocked_by, order}` | `{story, warnings}` |
| `PUT /api/stories/<id>/body` | `{body, base_sha256}` | story, or 409 if the body changed on disk |
| `POST /api/stories/<id>/notes` | `{text, author?}` | 201, story with body |
| `DELETE /api/stories/<id>[?force=1]` | | 204, or 409 if other stories depend on it |

A story object carries the frontmatter fields plus `id`, `filename`,
`unmet` (blocker ids that are not done), and `blocked`.

`order` is the full ordered list of ids for the story's column. Sending
`status` and `order` together moves and reorders in one request.

## Development

```sh
python3 -m unittest          # the whole suite, standard library only
python3 skald.py serve       # run against this repository's own .skald/
```

The root `skald.py` is the source of truth. `.skald/skald.py` is the
vendored copy this repository uses for its own backlog, and a test fails if
the two differ. After changing `skald.py`, copy it over `.skald/skald.py`.

The full design is in [SPEC.md](SPEC.md).

## License

MIT. See [LICENSE](LICENSE).
