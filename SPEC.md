# Skald: Project Specification

**Skald** is a file-system-native Kanban backlog for repositories worked on by
AI coding agents. Stories are Markdown files in `.skald/stories/`. A single
Python file, `skald.py`, gives agents a CLI and gives humans a local web board.
Nothing else is required.

**Audience:** the coding agent implementing Skald, and humans reviewing the
design. Everything here is normative unless marked *future*.

---

## 1. Goals and principles

1. **One file to install.** `skald.py` is the entire tool. The web UI and the
   agent instructions are embedded in it as string constants. Installing Skald
   into a repository is a copy plus one command.
2. **Standard library only.** No third-party Python packages, ever. Minimum
   Python 3.9.
3. **Git is the database.** All state lives in `.skald/stories/*.md`. Story
   changes are committed alongside the code they describe. Skald keeps no
   caches, indexes, or lock files.
4. **Skald owns the frontmatter, people and agents own the body.** Board state
   is only ever written by `skald.py`. The Markdown body is free-form and may
   be edited with any tool.
5. **Advisory, not enforcing.** Dependencies produce warnings, never hard
   errors. The agent's judgement is trusted.
6. **Small surface.** Every command and endpoint below must earn its place.
   Prefer removing a feature over making one configurable.

---

## 2. Installation and repository layout

### 2.1 Installing into a target repository

```sh
mkdir -p .skald
curl -sSL https://raw.githubusercontent.com/vitund-ai/skald/main/skald.py -o .skald/skald.py
python3 .skald/skald.py init
```

`init` creates:

```
.skald/
├── skald.py       # the tool (already present after the curl)
├── AGENTS.md      # agent contract, written from the embedded template
└── stories/       # story files, one per story
    └── .gitkeep
```

`init` is idempotent. It never overwrites an existing `AGENTS.md` or story.
After running, it prints one suggested line for the repository's root
`CLAUDE.md` or `AGENTS.md`:

> This repository tracks work with Skald. Read `.skald/AGENTS.md` before
> starting any task.

### 2.2 Path resolution

`skald.py` locates its data directory relative to its own file, never the
current working directory:

```
SKALD_DIR   = Path(__file__).resolve().parent
STORIES_DIR = SKALD_DIR / "stories"
```

So `python3 .skald/skald.py ls` works from any directory in the repository.

### 2.3 This repository

This repository is the Skald product, and it also dogfoods Skald for its own
backlog:

```
skald.py               # single source of truth for the tool, UI, and AGENTS.md template
tests/test_skald.py    # stdlib unittest suite
README.md              # human-facing docs: install, usage, API
SPEC.md                # this document
.skald/                # Skald's own backlog, created with `init`
```

`.skald/skald.py` in this repository is a copy of the root `skald.py`. A test
asserts the two are byte-identical so they cannot drift.

---

## 3. Data model

### 3.1 Story files

One story per file in `.skald/stories/`. Filename:

```
<id>-<slug>.md          e.g.  a3f9c2-implement-wireguard-overlay.md
```

- `id` is six lowercase hex characters from `secrets.token_hex(3)`. On
  creation Skald regenerates until the id is unique in the directory.
- `slug` is derived from the title at creation time: lowercase ASCII letters,
  digits, and hyphens, at most 50 characters. It is cosmetic. It is never
  updated when the title changes, and it is never used for lookup.
- **The filename is the authoritative id.** The frontmatter does not repeat it.
  Renaming a file changes the story's id and breaks any `blocked_by` links to
  it. `skald check` reports such dangling links.

### 3.2 File format

```markdown
---
title: "Implement WireGuard overlay network"
status: "ready"
rank: 20
tags: ["infrastructure", "v1.0"]
blocked_by: ["7b21e0", "c4d811"]
created_at: "2026-09-05T10:00:00Z"
updated_at: "2026-09-06T08:12:41Z"
---
## Requirements

Configure the wg0 interface on every node...

## [human] 2026-09-05 10:14 UTC
Please keep the MTU at 1420.

## [agent] 2026-09-06 08:12 UTC
Claimed. Plan:
- [ ] write wg0.conf template
- [ ] systemd unit
```

**Frontmatter rules (the "Skald subset" of YAML):**

- The file begins with a line that is exactly `---`. The frontmatter ends at
  the next line that is exactly `---`. Everything after that line is the body,
  byte for byte.
- Each frontmatter line is `key: value` with a single space after the colon.
  `value` is a **JSON literal**: a string, integer, or array of strings. JSON
  is valid YAML flow syntax, so any YAML tool can still read these files.
- Skald parses values with `json.loads` and writes them with `json.dumps`.
  Block-style lists, unquoted strings, comments, and multi-line values are not
  supported. A file that does not conform is **corrupt**: `ls` and the board
  skip it and print a warning naming the file; `show`, `mv`, and similar
  commands exit with status 2 and a message naming the offending line.
- On every write, Skald re-serialises the whole frontmatter block from its
  parsed form in the canonical field order below, then appends the original
  body bytes unchanged.

**Fields:**

| Field        | Type          | Notes                                                        |
| ------------ | ------------- | ------------------------------------------------------------ |
| `title`      | string        | Required. Non-empty.                                          |
| `status`     | string        | One of `backlog`, `ready`, `in_progress`, `review`, `done`.  |
| `rank`       | integer       | Sort order within a column. Lower sorts first.               |
| `tags`       | array[string] | Free-form. Stored sorted, de-duplicated, lowercase.          |
| `blocked_by` | array[string] | Story ids this story depends on. Stored sorted, de-duplicated.|
| `created_at` | string        | ISO 8601 UTC, second precision, `Z` suffix.                  |
| `updated_at` | string        | Same format. Set on every Skald write to the file.           |

Unknown fields are preserved on read and written back after the known fields,
so a human can add e.g. `estimate: 3` without Skald discarding it.

### 3.3 Body

The body is free-form Markdown. Skald creates it as:

```markdown
## Requirements

<body text given at creation, or empty>
```

Skald's only body operation is **append a note**, which adds a blank line, a
heading, and the text:

```markdown

## [<author>] <YYYY-MM-DD HH:MM> UTC
<text>
```

`author` is a short label such as `agent` or `human`. Any other edit to the
body is done by people or agents with ordinary tools. Editing the frontmatter
by hand is the one thing the contract forbids.

### 3.4 Derived state

- A story's **unmet dependencies** are the ids in `blocked_by` whose story is
  not `done`. An id with no matching file counts as unmet.
- A story is **blocked** if it has any unmet dependencies.
- **Sort order** everywhere (CLI and board) is: status in column order, then
  `rank` ascending, then `created_at` ascending, then id.

### 3.5 Ranks

- New stories get `rank = max(rank in target column) + 10`, or `10` for an
  empty column.
- A reorder replaces the ranks of every story in a column with
  `10, 20, 30, ...` in the given order. Ranks are only meaningful within a
  column, so collisions across columns are fine.

### 3.6 Concurrency and git

- Every file write goes to a temp file in the same directory followed by
  `os.replace`, so readers never see a partial file.
- Body edits made through the web UI are optimistic: the client sends the
  SHA-256 of the body it loaded, and the server refuses with 409 if the file
  has changed. CLI and agent writes are read-modify-write on a single small
  file and do not lock; the window is milliseconds and acceptable for a
  single-machine tool.
- Random ids mean two branches creating stories never produce add/add
  conflicts. Two branches editing the same story conflict like any other file.
  `skald check` reports files containing conflict markers.

---

## 4. CLI

Invocation is `python3 .skald/skald.py <command> [args]`. The examples below
abbreviate that to `skald`.

Anywhere a command takes `<id>`, any **unique prefix** of an id is accepted
(`skald show a3f`). An ambiguous or unknown prefix is an error.

**Exit codes:** `0` success (warnings may be on stderr), `1` usage error or
story not found, `2` corrupt story file. Warnings go to stderr prefixed
`WARNING:`; errors go to stderr prefixed `ERROR:`.

Every command that prints stories accepts `--json` and then emits a JSON
document on stdout with no other output. Agents should prefer `--json`.

| Command | Behaviour |
| --- | --- |
| `init` | Create the layout in section 2.1. Idempotent. |
| `ls [--status S] [--tag T] [--unblocked] [--all] [--json]` | List stories in sort order. Hides `done` unless `--all` or `--status done`. `--unblocked` keeps only stories with no unmet dependencies. Human output is a table: `ID  STATUS  RANK  BLOCKED  TAGS  TITLE`. |
| `next [--json]` | Print the single story an agent should pick up: the first `ready`, unblocked story in sort order. Prints nothing and exits 1 if there is none. |
| `show <id> [--json]` | Print the raw file. With `--json`: `{id, filename, ...frontmatter, unmet, body}`. |
| `new "<title>" [--status S] [--tags a,b] [--blocked-by id,id] [--body TEXT \| --body -] [--json]` | Create a story. Default status `backlog`. `--body -` reads the body from stdin. Prints the new id. |
| `mv <id> <status>` | Change status. Emits the dependency warning in section 4.1 when moving to `ready`, `in_progress`, `review`, or `done` with unmet dependencies. Assigns a rank at the bottom of the new column. |
| `set <id> title="..." \| rank=N` | Update title or rank. Multiple `key=value` pairs allowed. |
| `tag <id> +tag -tag ...` | Add and remove tags. |
| `block <id> +id -id ...` | Add and remove dependencies. Adding a self-reference or an unknown id is an error. Adding an id that creates a cycle succeeds with a warning. |
| `note <id> "<text>" \| -` | Append a note (section 3.3). `-` reads from stdin. `--as LABEL` sets the author, default `agent`. |
| `rm <id> [--force]` | Delete the file. Refuses without `--force` if other stories are blocked by it. |
| `check [--json]` | Validate every story file. Reports corrupt frontmatter, invalid statuses, dangling or self `blocked_by` ids, dependency cycles, and git conflict markers. Exit 0 if clean, 2 otherwise. Suitable for a pre-commit hook. |
| `serve [--port 8321] [--host 127.0.0.1] [--open]` | Start the web board. `--open` launches the default browser. |

### 4.1 Dependency warning

Text, on stderr, whenever a transition or the board would move a blocked
story forward:

```
WARNING: a3f9c2 has unmet dependencies: 7b21e0 (ready), c4d811 (in_progress)
```

The transition still happens.

---

## 5. HTTP API

Served by `ThreadingHTTPServer` from the standard library. Binds to
`127.0.0.1` by default; there is no authentication, and every write endpoint
modifies files, so binding to other interfaces is the user's explicit choice.

All request and response bodies are JSON. Errors are `{"error": "<message>"}`
with a 4xx status. Every endpoint that touches a story accepts a unique id
prefix, exactly like the CLI.

A **story object** in responses is:

```json
{
  "id": "a3f9c2",
  "filename": "a3f9c2-implement-wireguard-overlay.md",
  "title": "...", "status": "ready", "rank": 20,
  "tags": ["infrastructure"], "blocked_by": ["7b21e0"],
  "created_at": "...", "updated_at": "...",
  "unmet": ["7b21e0"],
  "blocked": true
}
```

| Method and path | Request | Response |
| --- | --- | --- |
| `GET /` | | The embedded `index.html`. |
| `GET /api/board` | | `{"statuses": [...], "stories": [story...]}` in sort order, including `done`. |
| `GET /api/stories/<id>` | | Story object plus `"body"` and `"body_sha256"`. |
| `POST /api/stories` | `{title, status?, tags?, blocked_by?, body?}` | `201` with the story object. |
| `PATCH /api/stories/<id>` | Any of `{title, status, rank, tags, blocked_by, order}` | `{"story": ..., "warnings": [...]}`. `order` is the complete ordered list of ids for the story's (new) column and triggers a reorder (section 3.5). Moving between columns and reordering is therefore one request. |
| `PUT /api/stories/<id>/body` | `{body, base_sha256}` | `200` with the story object, or `409` if `base_sha256` does not match the current body. |
| `POST /api/stories/<id>/notes` | `{text, author?}` | `201` with the story object. Default author `human`. |
| `DELETE /api/stories/<id>` | | `204`. `409` if other stories depend on it unless `?force=1`. |

The server and the CLI share the same functions. There is exactly one
implementation of "update a story", "reorder a column", and "append a note".

---

## 6. Web board

A single page embedded in `skald.py`. Vanilla JavaScript and Tailwind via
CDN. No build step and no framework. Internet access is required for the CSS;
that is accepted.

**Layout:** five columns in status order, each showing a count. Cards show
title, id, tag pills, and a lock badge when blocked. Hovering the lock lists
the unmet dependencies.

**Interactions:**

- Drag a card within or between columns. Drop sends one `PATCH` with `status`
  and `order`. Warnings in the response appear as a toast that fades after a
  few seconds and never blocks the UI.
- A search box filters cards by title, id, and tag as you type.
- Click a card to open a modal with: editable title, status select, tags and
  blockers as comma-separated inputs, the body in a textarea with a save
  button, and a note box that appends via the notes endpoint. A 409 on body
  save shows the conflict and offers reload.
- A "New story" button opens the same modal empty.
- The board polls `/api/board` every three seconds while the tab is visible,
  so agent activity from the CLI appears without a refresh. Polling pauses
  while a modal is open.

**Not in scope for v1:** Markdown rendering of the body, multi-board support,
authentication, mobile layout.

---

## 7. The agent contract

This is the content of `.skald/AGENTS.md`, written by `init`. It is embedded
in `skald.py` as a template and must be kept in sync with the CLI.

1. **Where things are.** The tool is `python3 .skald/skald.py`. Stories are
   files in `.skald/stories/`. Run `skald ls` at the start of a session.
2. **Pick work.** Run `skald next --json`. If it prints nothing, run `skald ls
   --json` and either pick an unblocked `ready` story or ask the human.
3. **Claim it.** Run `skald mv <id> in_progress`, then `skald show <id>` and
   read the whole file, including notes from humans.
4. **Warnings are advisory.** If `mv` warns about unmet dependencies, decide
   whether to stub the missing piece or work the blocker first. Write your
   decision as a note.
5. **Record progress.** Use `skald note <id> "..."` for progress, decisions,
   and checklists. You may edit the body with any tool. You must never edit
   the lines between the two `---` fences by hand, and you must never create
   story files by hand. Use `skald new`.
6. **Discovered work.** When you find work outside the current story, create a
   story for it with `skald new` and link it with `--blocked-by` or `skald
   block` where a real dependency exists. Do not silently expand the scope of
   the story you are on.
7. **Finish.** Move the story to `review` with a closing note summarising what
   changed and how it was verified. A human moves it to `done`. If the human
   has told you to close stories yourself, move to `done` instead.
8. **Commit together.** Story file changes go in the same commit as the code
   they describe. Never leave `.skald/` changes uncommitted at the end of a
   task.

---

## 8. Testing

`tests/test_skald.py` uses `unittest` and imports `skald.py` directly. It runs
with `python3 -m unittest`. Minimum coverage:

- Frontmatter parse and serialise round-trip, including unknown fields and a
  body containing `---` lines.
- Corrupt frontmatter is detected and reported with the line.
- Id generation is unique and prefix lookup is unambiguous.
- Unmet and blocked derivation, including missing ids.
- Rank assignment on create, move, and reorder.
- Every CLI command through its entry function, with stdout and stderr
  captured, checking exit codes and warning text.
- Every API endpoint through the server against a temp directory, including
  the 409 body conflict and the combined status plus order patch.
- Root `skald.py` and `.skald/skald.py` are byte-identical.

---

## 9. Deliverables

1. `skald.py`: CLI, server, embedded UI, embedded agent contract.
2. `tests/test_skald.py`.
3. `README.md`: install, quick start for humans and agents, CLI reference,
   API reference, file format.
4. `.skald/`: this repository's own backlog, initialised with `init`, with the
   remaining implementation work captured as stories.

---

## 10. Future ideas, explicitly out of scope

- `archive` command moving `done` stories to `.skald/archive/`.
- Markdown rendering in the modal.
- A `pipx`-installable package with a global `skald` command.
- Per-story assignee field for multi-agent setups.
- A `--watch` flag on `ls` for terminal users.
