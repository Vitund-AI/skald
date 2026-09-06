# Skald: Project Specification

**Skald** is a file-system-native Kanban backlog for repositories worked on by
AI coding agents. Stories are Markdown files in `.skald/stories/`. The
`skald-kanban` package gives agents a CLI and gives humans a local web board
that shows every project on the machine.

**Audience:** the coding agent implementing Skald, and humans reviewing the
design. Everything here is normative unless marked *future*. Where this
document and the code disagree, the code is wrong. For *why* a choice was
made, see `DECISIONS.md`.

This is the 0.3 specification. It supersedes the 0.1 single-file design; the
migration path is in section 2.4.

---

## 1. Goals and principles

1. **Install once per machine.** `pip install skald-kanban` provides `skald`
   and `git-skald`. Repositories carry data only, never the tool.
2. **Standard library only.** No third-party Python packages. Minimum Python
   3.9. The board loads Tailwind and marked from CDNs; that is the one
   external dependency and it degrades to unstyled, un-previewed but working.
3. **Git is the database.** All shared state lives in `.skald/` and is
   committed alongside the code it describes. Machine-local state (which
   projects exist here, personal preferences, the running server) lives in
   the user's config directory and is never committed.
4. **Skald owns the frontmatter, people and agents own the body.** Board
   state is only ever written by Skald. The Markdown body is free-form.
5. **Advisory, not enforcing.** Dependencies and limits produce warnings,
   never hard errors. The agent's judgement is trusted.
6. **Projects are named in the repo, located on the machine.** The name in
   `config.json` is stable across clones; the machine-local index maps names
   to paths. Cross-project references use the name.
7. **Small surface.** Every command and endpoint must earn its place.

---

## 2. Layout and resolution

### 2.1 Package

```
src/skald/
  __init__.py        __version__
  __main__.py        python -m skald
  errors.py          exception hierarchy with exit codes and HTTP statuses
  util.py            timestamps, slugs, atomic writes, checklist parsing
  config.py          ProjectConfig: .skald/config.json, columns and roles
  store.py           story format and the per-project Store
  registry.py        config home, Registry (projects.json), UserConfig, Workspace
  gitutil.py         thin git CLI wrappers
  cli.py             argparse commands
  server.py          HTTP API, board serving, background server management
  web/index.html     the board (package data)
  templates/AGENTS.md  agent contract written by `init` (package data)
```

Console scripts: `skald` and `git-skald`, both `skald.cli:main`. Git finds
`git-skald` on the PATH, so `git skald ...` needs no alias.

### 2.2 Repository layout

```
.skald/
├── config.json     project name, format version, columns   (committed)
├── AGENTS.md       agent contract, written once by init     (committed)
├── stories/        one file per story                       (committed)
├── archive/        terminal stories moved by `archive`      (committed)
└── templates/      optional story body templates            (committed)
```

### 2.3 Machine-local state

The config home is `$SKALD_HOME` if set, else `%APPDATA%\skald` on Windows,
else `$XDG_CONFIG_HOME/skald` defaulting to `~/.config/skald`. It holds:

- `projects.json`: `{"projects": {"<name>": {"path": "<abs .skald dir>", "registered_at": "..."}}}`
- `config.json`: user settings with defaults `author ""`, `push false`,
  `port 8321`, `host "127.0.0.1"`, `stale_days 3`.
- `server.json` and `server.log`: the background server's pid, host, port.

### 2.4 Finding the project

For any project command, the `.skald` directory is `$SKALD_DIR` if set, else
the first `.skald` directory found walking up from the current directory.
`-p NAME` before the command selects a registered project instead.

Opening a project has two side effects: if `config.json` is missing it is
written with a name derived from the parent directory and a notice is
printed, and the project is registered (or its path updated) in
`projects.json`. So a colleague who clones a repository and runs any command
is registered without a separate step.

`init` creates the layout when absent and is otherwise non-destructive. It
also migrates the 0.1 layout: it deletes `.skald/skald.py` and removes a git
alias equal to `!python3 .skald/skald.py`.

---

## 3. Project configuration

`.skald/config.json`:

```json
{
  "format": 1,
  "name": "api-server",
  "columns": [
    {"key": "backlog",     "label": "Backlog",     "role": "backlog"},
    {"key": "ready",       "label": "Ready",       "role": "ready"},
    {"key": "in_progress", "label": "In progress", "role": "active", "limit": 3},
    {"key": "review",      "label": "Review",      "role": "active"},
    {"key": "done",        "label": "Done",        "role": "done"},
    {"key": "wont_do",     "label": "Won't do",    "role": "closed"}
  ]
}
```

- `format` is the story-format version. A tool that sees a newer format than
  it understands refuses with a clear message. Current value: 1.
- `name` matches `^[a-z0-9][a-z0-9-]{0,63}$`.
- `columns` is a non-empty ordered list. `key` matches `^[a-z][a-z0-9_]{0,31}$`
  and is unique. `role` is one of `backlog`, `ready`, `active`, `done`,
  `closed`. At least one column must be `done` or `closed`. `limit` is an
  optional positive integer. Several columns may share a role.
- Unknown top-level keys are preserved.

**Role semantics:**

| Role | Meaning |
| --- | --- |
| `backlog` | New stories go to the first backlog column (else the first column). |
| `ready` | `next` draws from these. |
| `active` | `claim` moves into the first active column. Stale marking applies. |
| `done` | Terminal. Satisfies dependencies. Hidden from `ls` by default. Archivable. |
| `closed` | Terminal, like done, but satisfying a dependency this way produces a warning. |

Moving into a `ready`, `active`, or `done` column with unmet dependencies
warns. Moving into a column over its `limit` warns. A story whose status is
not a column key is not corrupt: it sorts last, the board shows it in an
"Unknown status" column, and `check` reports it as a problem.

---

## 4. Story files

### 4.1 Filename and id

```
<id>-<slug>.md          e.g.  a3f9c2-implement-wireguard-overlay.md
```

`id` is six lowercase hex characters from `secrets.token_hex(3)`, regenerated
until unique within the project (stories and archive). `slug` is derived from
the title at creation, cosmetic, never updated, never used for lookup. **The
filename is the authoritative id.** Any command taking an id accepts a unique
prefix.

### 4.2 Format

```markdown
---
title: "Implement WireGuard overlay network"
status: "ready"
rank: 20
tags: ["infrastructure", "v1.0"]
blocked_by: ["7b21e0", "api-server:c4d811"]
assignee: "claude"
created_at: "2026-09-05T10:00:00Z"
updated_at: "2026-09-06T08:12:41Z"
---
## Requirements

...
```

- The file begins with a line that is exactly `---`; the frontmatter ends at
  the next such line. Everything after is the body, byte for byte.
- Each frontmatter line is `key: value` where `value` is a JSON literal.
  Blank lines are ignored. Block lists, unquoted strings, comments, and
  multi-line values are corrupt. Corrupt files are skipped by listings with a
  warning and cause exit 2 when addressed directly.
- On write, Skald re-serialises the frontmatter in canonical order (known
  fields, then unknown fields in original order) and appends the body
  unchanged. Line endings in the body are preserved.

| Field | Type | Notes |
| --- | --- | --- |
| `title` | string | Required, non-empty. |
| `status` | string | Required, non-empty. Should be a column key. |
| `rank` | integer | Sort order within a column. Lower first. Default 0. |
| `tags` | array of strings | Stored lowercase, sorted, unique. |
| `blocked_by` | array of strings | `id` or `project:id`. Sorted, unique. |
| `assignee` | string | Omitted from the file when empty. |
| `created_at`, `updated_at` | string | ISO 8601 UTC with `Z`. `updated_at` set on every write. |

### 4.3 Body

Created as `## Requirements\n\n<body>`, or from a template in
`.skald/templates/<name>.md` with any given body appended after a blank line.
`note` appends `\n## [<author>] <YYYY-MM-DD HH:MM> UTC\n<text>\n` after a
blank line. Task-list items are counted as `checklist: {done, total}`.

### 4.4 Derived state

- Sort order is column index, then rank, then `created_at`, then id.
- New stories get `max(rank in column) + 10`, or 10. A reorder rewrites the
  column as 10, 20, 30... in the given order, with unlisted stories after.
- A dependency resolves to one of: a column key, `archived`, `missing` (no
  such story), or `unavailable` (project not registered here). It is
  satisfied when the target is archived or in a terminal column. A story is
  blocked when any dependency is unsatisfied. Cycle detection covers local
  references.
- A story is stale when its role is `active` and `updated_at` is at least
  `stale_days` old.

### 4.5 Archive

`archive` moves every story in a terminal column to `.skald/archive/`.
Archived stories are excluded from listings unless `--archived`, still
resolve as satisfied dependencies, still resolve by id, cannot be updated or
deleted until unarchived, and are included in `changelog`.

### 4.6 Other branches

`Store.snapshot(ref)` reads a project's `config.json`, stories, and archive
at any git ref through `git ls-tree` and one `git cat-file --batch` call,
never through the working tree or index. The result is a read-only
`Snapshot` that duck-types the read side of `Store`. Dependencies resolve
only within the snapshot; cross-project references are `unavailable`. The
checked-out branch is always the truth; snapshots are informational. The
server caches snapshots by the commit a ref resolves to.

`branch_diff` compares a snapshot with the working tree by id: stories only
there, only here, and those whose status, title, or archived flag differ.

### 4.7 Concurrency and git

Writes go to a temp file then `os.replace`. Board body edits carry the SHA-256
of the body they loaded and get 409 on mismatch. Random ids mean branches
never collide on creation. `check` reports conflict markers.

---

## 5. Identity

- CLI commands act as `--as NAME`, else `$SKALD_AUTHOR`, else `agent`.
- Board actions act as `$SKALD_AUTHOR`, else the user setting `author`, else
  git `user.name`, else `human`.
- `claim` sets `assignee` to the actor and moves a backlog or ready story into
  the first active column. `next` skips stories assigned to someone other than
  the actor; without an actor it skips all assigned stories.

---

## 6. CLI

`skald [-p NAME] <command>`. Exit codes: 0 success (warnings on stderr as
`WARNING: ...`, notices as `NOTE: ...`), 1 usage error or not found, 2 corrupt
story or configuration. Commands that print stories take `--json`.

| Command | Behaviour |
| --- | --- |
| `init [--name N]` | Section 2.4. Prints what it did and the CLAUDE.md line. |
| `status [--json]` | Name, path, branch, per-column counts, unknown-status count, ready-and-unblocked count, uncommitted files under `.skald/`. |
| `ls [--status C] [--tag T] [--assignee A] [--unblocked] [--all] [--archived] [--all-projects] [--branch REF] [--all-branches]` | Table `ID STATUS RANK BLOCKED ASSIGNEE TAGS TITLE`. Terminal columns hidden unless `--all` or `--status`. `--all-projects` qualifies ids. `--branch` lists a snapshot. `--all-branches` lists stories only on or differing on other branches with their local status. |
| `next [--as N] [--all-projects]` | First ready, unblocked story available to the actor. Exit 1 and a stderr message if none. |
| `show <id> [--branch REF]` | Raw file. `--json` adds derived fields, `body`, `body_sha256`. |
| `branches [--json]` | Every local and remote branch with story count and diff counts against the working tree. |
| `new "<title>" [--status C] [--tags a,b] [--blocked-by refs] [--body TEXT\|-] [--template T] [--assignee A]` | Create; prints the id. |
| `mv <id> <column>` | Change status; rank goes to the bottom of the new column. |
| `claim <id> [--as N]` | Section 5. |
| `set <id> title=.. rank=N assignee=..` | Field edits. |
| `tag <id> +t -t`, `block <id> +ref -ref` | Set edits. Adding an unknown local id or a missing story in a registered project is an error; a self-reference is an error; a cycle warns. |
| `note <id> "text"\|- [--as N]` | Append a note. |
| `rm <id> [--force]` | Delete; refuses while other stories depend on it. |
| `log <id>` | `git log --follow` on the file. |
| `archive [--dry-run]`, `unarchive <id>` | Section 4.5. |
| `check [--json] [--hook]` | Problems: corrupt files, bad filenames, duplicate ids, unknown status, invalid or dangling or self references, cycles, conflict markers. Warnings: references to unregistered projects, archived non-terminal stories. `--hook` adds uncommitted story files as a problem. Exit 2 on problems. |
| `commit [-m MSG] [--push]` | `git add -A -- .skald && git commit -- .skald`. Pushes with `--push` or the `push` setting. |
| `changelog --since REF [--until REF]` | Stories terminal at `until` that were absent or non-terminal at `since`, read from git objects. |
| `columns`, `templates`, `projects [rm NAME]`, `config [KEY [VALUE]] [--unset]` | Inspection and settings. |
| `hooks claude [--install] [--strict]` | Prints or merges into `.claude/settings.json`: SessionStart `skald status && skald ls`; Stop `skald check` (or `skald check --hook` with `--strict`). |
| `serve [--host H] [--port P] [--open]` | Foreground server. |
| `server start\|stop\|status` | Background server via `server.json`. |
| `open` | Start if needed, open the browser on the current project. |

---

## 7. HTTP API

`ThreadingHTTPServer`, bound to `127.0.0.1` by default, no authentication.
Project names in URLs are resolved through the registry; the API never
accepts a filesystem path. A fresh `Workspace` is built per request so
registry and config edits are picked up immediately. See the README for the
endpoint table; it is the reference.

`GET .../version` returns a hash of story file names, sizes, and mtimes.
`GET .../events` is a server-sent event stream that emits `hello` on connect
and `change` whenever that hash changes, checked every half second on the
handler thread. The board subscribes to the stream and refetches on `change`;
it falls back to polling `version` every 1.5 seconds when the stream is
unavailable, and polls every 15 seconds as a safety net while it is live.

---

## 8. Web board

One page for all projects. Header: project switcher (plus "All projects"),
branch, filter, identity, commit button when `.skald/` has uncommitted
changes, new-story button. Board: columns from config with counts and
limits, an "Unknown status" column when needed. Cards: title, tags, lock with
dependency tooltip, stale marker, checklist progress, assignee, id, age.
A branch dropdown switches to a read-only snapshot of another branch with a
banner, no dragging, disabled fields, and no write buttons; a badge counts
stories that exist only on other branches.
Modal: title, status, assignee, tags, blockers, dependency chips that open
the target (switching project if needed), body with Markdown preview, save
with conflict detection, reload, claim, delete, notes, history tab. Toasts
for warnings and errors. Keyboard: `n` new, `/` filter, `Esc` close.
Not in scope: authentication, mobile layout, multi-select.

---

## 9. The agent contract

`src/skald/templates/AGENTS.md` is the normative text, written to
`.skald/AGENTS.md` by `init`. Summary: orient with `status` and `ls`; pick
with `next`; claim with `claim --as`; treat warnings as advisory and record
decisions; note progress; create stories for discovered work and link real
dependencies, using `project:id` across repositories; finish to review; commit
story changes with the code; never hand-edit frontmatter or `config.json`.

---

## 10. Testing

`python -m unittest` from the repository root, standard library only.
`tests/__init__.py` puts `src/` on the path. Coverage: format round-trips and
corruption cases, config validation, store behaviour including ranks,
dependencies, cross-project states, roles, limits, archive, templates,
registry and user config, every CLI command, every API endpoint, the
background server lifecycle, and this repository's own backlog passing
`check`. CI runs the suite on Python 3.9 through 3.13 on Linux, plus 3.12 on
macOS and Windows, and builds the wheel. Tags matching `v*` publish to PyPI
via trusted publishing.

---

## 10a. MCP server

`skald mcp` serves the store over the MCP stdio transport: newline-delimited
JSON-RPC 2.0 with `initialize`, `notifications/initialized`, `ping`,
`tools/list`, and `tools/call`; batches are supported. Only the `tools`
capability is offered. Each tool mirrors a CLI command, takes an optional
`project`, and returns JSON text. Skald errors are returned as tool results
with `isError: true`, never as JSON-RPC errors, so the agent sees the message.

## 11. Future

- A dependency graph view.
- Multi-select and bulk moves on the board.
- Renaming a project with reference rewriting across registered projects.
