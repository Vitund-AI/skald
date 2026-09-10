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

1. **Install once per machine.** The `skald-kanban` distribution provides
   `skald` and `git-skald`. Until the first PyPI release it installs from the
   GitHub repository (`pip install git+https://github.com/Vitund-AI/skald.git`),
   and generated workflows do the same. Repositories carry data only, never
   the tool.
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

- `projects.json`: `{"projects": {"<name>": {"path": "<abs .skald dir>", "registered_at": "...", "checkouts": ["<abs .skald dir>", ...]}}}`.
  `path` is the primary; `checkouts` (optional) are other working trees of
  the same project recorded when a command ran there.
- `config.json`: user settings with defaults `author ""`, `push false`,
  `port 8321`, `host "127.0.0.1"`, `stale_days 3`.
- `server.json` and `server.log`: the background server's pid, host, port.

### 2.4 Finding the project

For any project command, the `.skald` directory is `$SKALD_DIR` if set, else
the first `.skald` directory found walking up from the current directory.
`-p NAME` before the command selects a registered project instead.

Opening a project has two side effects: if `config.json` is missing it is
written with a name derived from the parent directory and a notice is
printed, and the project is registered in `projects.json`. So a colleague
who clones a repository and runs any command is registered without a
separate step.

Registration keeps one primary path per name. A command run in another
checkout of the same project while the primary's directory still exists
records that checkout beside it and prints a notice; it never replaces the
primary. The primary moves only when its directory has gone (a moved
repository). `projects use` makes the current checkout the primary.
`Registry.checkouts(name)` lists the primary, the recorded checkouts, and
the git worktrees of the primary (from `git worktree list`), each with an
opaque id (a hash of the path) so the HTTP API never carries paths; recorded
checkouts whose directory has gone are forgotten. `Workspace.open_checkout`
opens one by id; `Workspace.other_checkouts(store)` opens every other working
tree of a store's project.

`init` creates the layout when absent and is otherwise non-destructive. It
also migrates the 0.1 layout: it deletes `.skald/skald.py` and removes a git
alias equal to `!python3 .skald/skald.py`. It appends the one-line pointer to
`.skald/AGENTS.md` to the root `CLAUDE.md` and `AGENTS.md` when they exist
and lack it, and creates `AGENTS.md` with the pointer when neither exists.

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
| `released` | string | Set by `release`; the version the story shipped in. Only on archived stories in practice. |
| `created_at`, `updated_at` | string | ISO 8601 UTC with `Z`. `updated_at` set on every write. |

### 4.3 Body and notes

Notes appended by `note` have the heading
`## [<author>] <YYYY-MM-DD HH:MM> UTC` followed by ` · <kind>` when a kind
was given. `parse_notes` recovers `{author, stamp, kind, text}` from the
body; the text before the first note heading is the requirements.
`## Acceptance` (or `## Acceptance criteria`) introduces a section whose
task-list items are the acceptance criteria; `acceptance_progress` counts
them and `update` warns when a story moves into a terminal column, or forward
into an active column other than the first, with any unchecked.


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
- `next` skips ready stories assigned to someone else unless the assignment
  is stale, in which case it offers them with a warning; it also skips
  stories that are active with a different assignee on any other local
  branch (`claims_elsewhere`, computed from snapshots). `claim` warns in both
  cases and proceeds.

### 4.5 Facets

A tag of the form `key:value` (split at the first colon, both sides
non-empty) is a facet. `facets(stories, config)` groups stories by key and
value with `total`, `done` (terminal status), `open`, and `ids`. Epics are
the `epic` facet by convention; nothing in the format knows about them. The
board response carries `facets`, and `facets`/`epics` aggregate across
projects with `--all-projects`.

### 4.5a Archive

`archive` moves every story in a terminal column to `.skald/archive/`.
Archived stories are excluded from listings unless `--archived`, still
resolve as satisfied dependencies, still resolve by id, cannot be updated or
deleted until unarchived, and are included in `changelog`.

### 4.5b Releases

`release VERSION` gives the done column a meaning: done is finished but not
shipped; archived with `released` is shipped in that version. It collects
every story in a `done` or `closed` column, builds a changelog section
(`## VERSION (DATE)` with one bullet per done story and a `### Not doing`
list for closed ones), merges it into the changelog, sets `released` on each
story, archives them, and commits `.skald/`, the changelog, and the rendered
snapshot with a `Skald-Story` trailer per story.

The bullet text is the story's `## Changelog` section (everything under that
heading up to the next heading, joined into one paragraph; notes are never
included) or, when absent, the title. Merge rule: if the changelog's first
`##` section heading contains "unreleased", that heading becomes
`## VERSION (DATE)` and the generated list is appended to the end of the
section under `### Stories` (with `#### Not doing`), so curated notes for the
version are kept; otherwise the new section is inserted above the first
`##` heading. A missing changelog is created with a `# Changelog` title.
Skald never edits version files or creates tags. `--dry-run` prints the
section and the count and touches nothing; `--no-commit` writes and archives
only. It is an error when no story is in a terminal column.

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

`claims_elsewhere(checkouts=...)` also reads the other working trees of the
project, so a claim made in a worktree counts before it is committed; such
entries carry `checkout`. A working tree stands in for its branch, which is
then not scanned from objects, so nothing is counted twice. The CLI passes
`Workspace.other_checkouts(store)` from `next`, `claim`, and `context`.

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
| `context [--as N] [--json]` | Orientation block: assigned stories with last note and handoff flag, next story, blocked ready stories, stale claims by others, claims on other branches, uncommitted files. |
| `resume <id> [--json]` | Compact story plus requirements, dependency states, decision and blocker notes, latest handoff (else latest note), note count. |
| `next [--as N] [--all-projects] [--compact]` | First ready, unblocked story available to the actor per section 4.4. Exit 1 and a stderr message if none. |
| `show <id> [--branch REF]` | Raw file. `--json` adds derived fields, `body`, `body_sha256`. |
| `branches [--json]` | Every local and remote branch with story count and diff counts against the working tree. |
| `new "<title>" [--status C] [--tags a,b] [--blocked-by refs] [--body TEXT\|-] [--template T] [--assignee A]` | Create; prints the id. |
| `move <id> <column>` | Change status; rank goes to the bottom of the new column. |
| `claim <id> [--as N]` | Section 5. |
| `set <id> title=.. rank=N assignee=..` | Field edits. |
| `tag <id> +t -t`, `block <id> +ref -ref` | Set edits. Adding an unknown local id or a missing story in a registered project is an error; a self-reference is an error; a cycle warns. |
| `note <id> "text"\|- [--as N] [--kind K]` | Append a note; `K` matches `^[a-z][a-z0-9_-]{0,31}$`. |
| `rm <id> [--force]` | Delete; refuses while other stories depend on it. |
| `log <id>` | `git log --follow` on the file. |
| `archive [id ...] [--dry-run]`, `unarchive <id>` | Section 4.5; ids restrict it and must all be terminal. |
| `release VERSION [--changelog PATH] [--date D] [--dry-run] [--no-commit]` | Section 4.5b. |
| `ls --release VERSION` | Archived stories with that `released` value. |
| `check [--json] [--hook]` | Problems: corrupt files, bad filenames, duplicate ids, unknown status, invalid or dangling or self references, cycles, conflict markers. Warnings: references to unregistered projects, archived non-terminal stories. `--hook` adds uncommitted story files as a problem. Exit 2 on problems. |
| `commit [-m MSG] [--push] [--no-trailers]` | `git add -A -- .skald && git commit -- .skald`, with a `Skald-Story: <id>` trailer per touched story. Pushes with `--push` or the `push` setting. |
| `commits <id> [--all-branches] [--json]` | `git log --grep` for the trailer or `[id]`. |
| `diff --since REF [--until REF] [--markdown] [--json]` | `diff_states` between two snapshots (or the working tree): added, removed, and changed stories with field deltas, notes added, body edits. Markdown output starts with `<!-- skald-diff -->` for comment upserts. |
| `activity [--since REF] [--until REF] [--json]` | For each commit touching `.skald/` in the range, `diff_states(parent, commit)` rendered as events. Default range is 20 commits. |
| `changelog --since REF [--until REF]` | Stories terminal at `until` that were absent or non-terminal at `since`, read from git objects. |
| `facets [KEY] [--all-projects] [--json]`, `epics` | Facet values with counts and progress. |
| `columns`, `templates`, `projects [rm NAME \| use [PATH]]`, `config [KEY [VALUE]] [--unset]` | Inspection and settings. `projects` lists each project's other checkouts beneath it with branch and dirty count; `use` makes a checkout the primary. |
| `hooks claude [--install] [--strict]` | Prints or merges into `.claude/settings.json`: SessionStart `skald status && skald ls`; Stop `skald check` (or `skald check --hook` with `--strict`). |
| `hooks git [--install]`, `hooks github [--install]` | Section 10b. `hooks claude --install` also writes `.claude/skills/skald/SKILL.md` from the contract template. |
| `graph [--format mermaid\|dot\|json] [--all] [--archived]` | Section 10c. |
| `render [--format md\|html] [--out PATH] [--archived] [--stage] [--stdout] [--enable]` | Section 10b. |
| `serve [--host H] [--port P] [--open]` | Foreground server. |
| `server start\|stop\|status` | Background server via `server.json`. |
| `open` | Start if needed, open the browser on the current project. |
| `docs [--out PATH] [--stdout] [--check]` | Writes `docs/cli.md` from `docs_markdown()`, which walks `command_reference()`; a repository test fails when the committed file is stale, and `--check` does the same for CI. |
| `completion bash\|zsh\|fish` | Prints a shim that calls the hidden `_complete -- CWORD WORD...` for candidates (`value<TAB>description` lines). `completion.py` derives commands and flags from `command_reference()` and reads the store for ids, columns, tags, authors, templates, branches, and projects; it never raises into the shell. `_complete` is intercepted before argparse and absent from `--help` and the reference. |

---

## 7. HTTP API

`ThreadingHTTPServer`, bound to `127.0.0.1` by default. Project names in
URLs are resolved through the registry; the API never accepts a filesystem
path.

Access: `serve` generates a 32-byte hex token on first start, stored as
`token` in the machine-local directory with mode 0600 (directory 0700), and
re-reads it whenever the file's mtime changes so `server token --rotate`
takes effect immediately. Every `/api/` route except `GET /api/health` and
`/api/session` requires the token as `Authorization: Bearer` or as the
`skald_session` cookie, compared in constant time; failures are 401. Before
that, every `/api/` route except health checks the `Host` header against
`localhost`, `127.0.0.1`, `::1`, or the bound address, and refuses with 403
otherwise (DNS rebinding); the check is skipped when bound to all
interfaces, where the token is the only gate. `POST /api/session {token}`
sets the cookie (`HttpOnly`, `SameSite=Strict`, `Path=/`) and `DELETE`
clears it. `skald open` and `serve --open` put the key in the URL fragment
(`/#key=…`), which browsers never send to the server; the page posts it to
`/api/session` and rewrites the URL. The CLI and MCP server read files
directly and are unaffected. A fresh `Workspace` is built per request so
registry and config edits are picked up immediately. See the README for the
endpoint table; it is the reference.

`GET /api/help` returns the CLI reference built by `cli.command_reference()`,
which walks the argparse tree; the board's Help panel renders it, so the
page never carries its own copy of the command list.

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
One filter dropdown per facet key and a swimlane control that splits the
board by a facet's values with a progress bar per lane.
A branch dropdown switches to a read-only snapshot of another branch with a
banner, no dragging, disabled fields, and no write buttons; a badge counts
stories that exist only on other branches. When the project has more than
one checkout on the machine the dropdown starts with a "Working trees"
group, one entry per checkout reading `worktree` or `clone`, the directory
name (with its parent when two share a name), branch, `primary`, and dirty
count, so the closed control cannot read as a branch; a read-only branch
that a working tree is on is suffixed `committed only`, and the control's
tooltip describes the current choice;
choosing one shows and edits that working tree (every request carries
`?checkout=ID`, including the event stream, and the id is kept in the URL),
with a banner naming the path when it is not the primary.
Modal: title, status, assignee, tags, blockers, dependency chips that open
the target (switching project if needed), body with Markdown preview, save
with conflict detection, reload, claim, delete, notes, history tab. Toasts
for warnings, errors, changes made outside the board (from the event
stream, suppressed for three seconds after the board's own writes), and a
new `HEAD` on the branch. Keyboard: `n` new, `/` filter, `g` graph, `?`
help, `Esc` close; cards, ready rows, and graph nodes are focusable and open
on Enter. An empty project shows a hint instead of five bare columns.

Multi-select: pressing and holding a card for 450ms (pointer events, so
mouse and touch) or pressing `x` on a focused card starts a selection scoped
to that card's column. Every card in the column shows a circle; selected
ones show a check. A click on a card in the column toggles it; a click on a
card or empty space in another column, or `Esc`, ends the selection. Dragging
a selected card drags the batch: the drop inserts the batch, in selection
order, at the placeholder. A bar at the bottom moves the batch to a column,
adds a tag to each, or archives it (shown only when the column is terminal).
Batch moves are sequential `PATCH` calls per story followed by one `order`
call; warnings are collected and shown once each. The selection survives
re-renders and drops ids that leave the column.
Every board render captures and restores each column's scroll offset (and
the board's own), so selecting or refreshing deep in a long column does not
jump back to the top.

Help panel: shortcuts and card markers, the CLI reference from `/api/help`
with a filter, and a story file primer with links to the docs.

Theme: a dozen CSS custom properties on `:root` define the palette; a
`data-theme` attribute on the root element selects light or dark. A script
in `<head>` sets it before first paint from `localStorage` (`skald.theme`:
`auto`, `light`, `dark`; `auto` follows `prefers-color-scheme` and tracks
changes). Tailwind is configured to expose the properties as colour names
(`bg-surface`, `text-muted`, ...) and its `dark:` variant keys off the same
attribute for the few semantic accents. The graph reads its fills from the
same properties, so it re-renders on theme change.

Layout: columns are flex items with a 15rem floor and a 28rem ceiling, so
five columns fit a laptop screen and ten scroll; below the `sm` breakpoint
they stack vertically.
Not in scope: authentication, multi-select.

---

## 9. The agent contract

`src/skald/templates/AGENTS.md` is the normative text, written to
`.skald/AGENTS.md` by `init`. Summary: orient with `status` and `ls`; pick
with `next`; claim with `claim --as`; treat warnings as advisory and record
decisions; note progress; create stories for discovered work and link real
dependencies, using `project:id` across repositories; finish to review; commit
story changes with the code; never hand-edit frontmatter or `config.json`.

---

## 9a. Documentation

User documentation lives in `docs/` as plain Markdown, one page per
question: getting started, working with agents, the board, stories, git and
CI, multiple projects, the HTTP API, troubleshooting, and the CLI reference.
The README is the front door and links to them rather than repeating them.
`docs/cli.md` is generated by `skald docs` from the parser and never edited
by hand; every other page is hand-written in the same register as the
README.

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
via trusted publishing once the project exists there; no tag has been cut yet.

---

## 10b. Rendered snapshots

`render` writes a Markdown (default) or HTML view of the board for
committing. Markdown goes to `.skald/README.md` unless `config.json` or
`--out` says otherwise, so the `.skald` folder on GitHub shows the board.
The file starts with `<!-- skald-render <hash> -->` where the hash covers
columns and every displayed story field; there is no timestamp, so an
unchanged backlog re-renders byte-identically. Ids link to story files
relative to the output location. Terminal columns are collapsed in
`<details>`; the `epic` facet produces a progress table; unknown statuses
and, with `--archived`, archived stories get their own sections.

`config.json` may carry `"render": {"path", "format", "archived"}`. When it
does, `commit` and the board's commit button re-render before staging and
include the output even when it lies outside `.skald/`. `check` warns when
the marker in the rendered file no longer matches the stories.

`hooks git --install` writes a pre-commit hook (`skald check`, then
`skald render --stage`) into git's hooks directory, refusing to overwrite a
hook it did not write. `hooks github --install` writes
`.github/workflows/skald.yml`, which runs `check` on pushes and pull requests
and commits a fresh render on the default branch, and on pull requests
posts or updates a `<!-- skald-diff -->` comment from `diff --markdown`.
Both enable `render` in `config.json` if it is off.

## 10c. Dependency graph

`graph.build_graph(store, stories, include_isolated=False)` returns nodes
(id, title, status, role, external, archived) and edges (from blocker to
blocked, with `satisfied`, `external`, `missing`, `cycle`). Only stories
with an edge appear unless isolated ones are requested; cross-project
targets are external nodes resolved through the workspace when possible.
`to_mermaid` emits `flowchart LR` with role classes, dashed external edges,
and thick cycle edges; `to_dot` the Graphviz equivalent. `render` embeds the
Mermaid block after the epics, collapsed above 25 nodes. The board draws
the same graph as inline SVG with a longest-path layered layout.

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
