# Changelog

## Unreleased

### Changed
- Python 3.10 or newer. 3.9 has been end of life since October 2025; CI
  now runs 3.10 through 3.14 on Linux and 3.12 on macOS and Windows.

### Added
- `SECURITY.md`: how to report a vulnerability privately, what to expect,
  which versions receive fixes (the latest; an earlier line at the
  maintainers' discretion), what is in and out of scope, and what happens
  after a fix. docs/git-and-ci.md describes patching an earlier release
  from a branch cut at its tag, and the two standing rules: a published
  tag is never deleted or moved, and a vulnerable release on PyPI is
  yanked, never deleted.
- `scripts/release.sh X.Y.Z`: the release as one checked sequence. It
  refuses to start unless on a clean `dev` in step with origin with an
  untagged, newer version, previews the changelog section, then bumps the
  version file, runs `skald release`, tests, pushes, opens and merges the
  pull request to `main`, tags, and merges `main` back into `dev`.
  `--dry-run` runs the checks and the preview and changes nothing. Tested
  against a fixture repository with a stub `gh`.

## 0.5.1 (2026-09-12)

### Fixed
- `skald release v1.2.0` writes `## 1.2.0` and `released: "1.2.0"`: the
  tag's `v` is not part of the version. The version guard test now fails
  on a release heading it cannot read instead of passing silently, which
  is how a `v`-prefixed heading let a tag go out against an unbumped
  package.

### Changed
- The repository's workflows and the one `skald hooks github` writes use
  the current action majors (checkout v7, setup-python v7, github-script
  v9, upload-artifact v7, download-artifact v8), which run on Node 24, so
  runs no longer warn that the actions target Node 20.

### Added
- A lint job runs ruff (pyflakes, pycodestyle, bugbear, and the
  bandit-derived `S` rules) on every pull request, configured in
  `pyproject.toml` with the intentional findings waived per file; the
  package stays standard library. Dependabot keeps the action versions
  current. The findings it raised are fixed: unused names, a `raise` inside
  `except` that lost its cause, and the sha1 fingerprints marked
  `usedforsecurity=False`.
- `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`.

### Fixed
- From CodeQL's first run: every workflow, and the one `skald hooks github`
  writes, starts the token read-only (`permissions: contents: read`) and
  the jobs that write say so; a template name is a plain slug, so
  `--template ../x` cannot read a Markdown file outside
  `.skald/templates/`; and the question reference parser no longer has a
  whitespace pattern that was quadratic on a long run of spaces.

### Stories

- Workflows: current action majors, which run on Node 24 (355b94)
- Lint in CI: ruff with the bugbear and bandit rule sets, Dependabot for actions (dd8c14)
- Code of conduct and contribution guide (5dd1b9)
- CodeQL findings: workflow token permissions, template name traversal, question reference regex (b635fa)

## 0.5.0 (2026-09-12)

### Changed
- The README opens with the idea-to-release arc: "Track work from idea to
  release, in Markdown, in your repo, with your coding agents." The PyPI
  description and `skald --help` say the same.

### Added
- `skald next --tag TAG` (and `tag` on MCP `skald_next`) picks the next
  ready, unblocked story carrying the tag, so a loop that routes work by a
  facet such as `effort:deep` asks in one call.
- `examples/model-routing/`: a worked Claude Code setup for routing stories
  to model-pinned subagents by an `effort:` tag, an executive skill that
  drains the backlog through them, and a report joining the intended tier
  with the authors that finished each story. The contract says a story
  tagged with an intent you do not match is not yours to claim; model and
  cost stay conventions over tags and note authors (D61).

### Fixed
- `skald import`: `created_at` from git was empty on Python 3.9 and 3.10
  with a recent git, which prints UTC dates ending in `Z`; the author date
  is read as a Unix timestamp now. A record with Windows line endings
  became a story with `\r\n` in its body, and the link pass rewrote files
  with the platform's line ending; line endings are normalised on import
  and preserved everywhere else.
- The `skald check` notice about questions a plain decision used to close
  names 0.4.1, the release that changed the rule.

### Stories

- README: hero line and opening paragraph sell the idea-to-release arc (07d6b4)
- next --tag: the next unblocked ready story carrying a tag (da3085)
- Model routing example: intent tags, model as author, an executive loop over subagents (092468)

## 0.4.1 (2026-09-10)

### Changed
- Skald is on PyPI as `skald-kanban`. The README, getting started guide,
  agent contract, and the workflows `skald hooks github` generates install
  `skald-kanban` instead of the repository; the git URL remains the way to
  run the unreleased head.
- The package classifier is Development Status 4, Beta.
- A question closes only when a decision names it. A plain `note --kind
  decision` records a choice and closes nothing; `skald answer` writes the
  decision that closes a question, and is the only thing that does. Questions
  are numbered Q1, Q2, ... by order of appearance for the story's life, and
  `resume`, `context`, `ls`, and the board show the label; `--question`
  takes `3` or `Q3`. With one question open `answer` targets it; with
  several it refuses unless told which, or `--all`; with none it refuses.
  `--withdraw` records a question as dropped rather than answered. `resume`
  lists closed questions with the decision that closed them. Questions an
  unnamed decision used to close are open again; `skald check` names each
  such story so one `answer --all` (or one per question) settles it.
- The board's story dialog lists open questions as Q1, Q2, ..., each with
  an Answer button: select one and the reply closes only that question;
  "Answer all" names every open question. `POST .../notes` takes
  `question`, `all`, and `withdraw`, and the CLI, MCP tool, and server share
  one `Store.answer`.

### Fixed
- `skald import --rewrite-links ROOT` rewrites links inside the new
  stories even when `ROOT` does not contain `.skald/`, and resolves a
  reference against every ancestor of the referencing file up to `ROOT`
  and against the project root, so bucket-relative and repository-relative
  links are found. The mapping is validated before any file is read, with
  errors naming the rule, instead of a traceback on a `$2` with one group.
- `created_at` on import falls back to the commit that added the file
  (`fallback: git-added`, the default), then now; `fallback: error` keeps a
  regex miss as a problem. Tag and status rules can match `on: path`, the
  path under the project root, and `--tag TAG` adds a fixed tag per run.
- A test cited a commit by its short sha, which one run in about thirty has
  no letter in; the audit extractor rightly reads such a token as a number.
  The test cites the full sha.

### Stories

- Changelog 0.4.0: drop the duplicated bullets and the stale 0.3.0 line (307343)
- Publish to PyPI (b91662)
- Board: answer one question at a time (abb68f)
- Flaky test: audit test cites the seed commit by short sha, which may have no letters (ce0dac)
- Import review 0.4.0: links across roots, git-added dates, path tags, mapping validation (b82d9b)

## 0.4.0 (2026-09-10)

### Added
- `skald import PATH... --map FILE` brings an existing folder of Markdown
  records into the backlog: titles from the H1, bodies kept byte for byte,
  dates, statuses, tags, and dated notes extracted by rules in a JSON mapping
  file, links across the repository rewritten to the new story files with
  `--rewrite-links`, sources removed with `--rm` so one commit keeps the
  history, and `--dry-run` to see it all first. See docs/importing.md.

### Changed
- `skald rm --force` clears the deleted story's id from other stories'
  `blocked_by` and the `parent` field of its children, printing each change,
  instead of leaving references that `skald check` reports as problems.
- `skald context` lists at most five stories under "Waiting on a human",
  newest question first, and says how many more there are; `skald ls
  --questions` has the full list.
- `skald resume` lists a long section map one heading per line.
- `skald answer --question N` closes only the Nth open question, as `resume`
  numbers them, by naming it in the decision's first line; a decision
  without that line still closes every open question. MCP `skald_answer`
  takes `question`.
- The package version is 0.4.0. A test now fails when the newest release
  heading in the changelog does not match the version in the package, since
  `release` never edits version files.

## 0.3.0 (2026-09-10)

### Added
- Questions: `skald note --kind question` records something only a human
  can decide, open until a later decision note on the story. `skald answer
  <id> "..."` closes them. `skald context` lists every story waiting on a
  human, `resume` prints the open ones, `ls` shows `?N` in a new `Q` column
  and `--questions` filters, and the board has an amber badge, a "Waiting
  on a human" filter, and an Answer button in the story dialog. MCP:
  `skald_answer`, and `waiting` and `open_questions` in context and resume.

- Backdating for migrations: `skald note --at WHEN` stamps the note heading
  with a given instant and `skald new --created-at WHEN` sets `created_at`
  and `updated_at`, so a script bringing an existing Markdown backlog into
  Skald keeps its history. Both default to now. MCP `skald_note` takes `at`
  and `skald_new` takes `created_at`.
- Parents: a story can be one piece of another. `skald new --parent ID`
  (facet tags inherited unless `--no-inherit`), `skald set ID parent=ID`
  or `parent=-`, `skald ls --parent ID`; `ls` marks parents and children;
  `resume` on a child prints the parent's requirements first; `check`
  reports dangling parents and cycles; `rm` refuses while children exist;
  moving a parent to done, or releasing it, with an open child warns. MCP
  `skald_new` and `skald_set` take `parent`. `skald epics` lists structural
  parents beside the `epic:` facet; `skald commits <parent>` includes the
  children's commits, tagged (`--no-children` to turn off). On the board a
  parent card shows its children's progress, the dialog has a Parent field,
  lists the children, and adds one with "+ child", the History tab unions
  the children's commits, and swimlanes can split by parent. The API takes
  `parent` and `inherit` on create and `parent` on patch, returns `children`
  and `parent_story` on a story, and unions children in history.
- `skald audit <id>` checks a story's cited paths, `path:line` references,
  and commit hashes against the tree, lists referenced files changed since
  the last audit, and appends an `audit` note with the summary. `resume`
  shows when the story was last audited and how many referenced files
  changed since. MCP: `skald_audit`.
- Lanes: `"facet_limits": {"lane": 1}` in `config.json` means at most one
  story per `lane:` value may be active at once, counting claims on other
  branches and in other checkouts. `next` skips a story whose lane is busy
  and says who holds it; `claim` and a move into an active column warn.
  `columns` lists the limits, `status` reports busy lanes, and the board's
  swimlane header shows the count in red when a lane is full.
- Lifecycle columns: `skald init --columns lifecycle` writes `idea`, `plan`,
  `ready`, `in_progress`, `review`, `done`, so ideation and planning have a
  place before anything is schedulable. Moving a story from a backlog
  column into ready with an open question warns.

### Changed
- `skald resume` prints the `## Requirements` section when the body has
  one, then a one-line map of the other sections with their sizes; `--section
  NAME` prints one section and `--full` the whole body. A body without the
  heading prints whole, as before. The MCP `skald_resume` tool takes `section`
  and `full` and returns `sections`.
- The Claude Code SessionStart hook written by `skald hooks claude` runs
  `skald context`, a bounded orientation block, instead of `skald status &&
  skald ls`, which printed every open story into the agent's context on
  every session start, resume, clear, and compaction. `--as NAME` bakes the
  agent's name into the hook. Re-run the install to update an existing hook.

### Removed
- The migration from the unreleased 0.1 single-file layout: `init` no longer
  looks for a vendored `skald.py` or the old git alias, and the upgrade
  sections are gone from the docs. 0.2.0 was the first release anyone
  installed.

### Fixed
- `skald serve --port 0` and `skald server start` with port 0 ask the
  operating system for a free port instead of silently using the configured
  one. The test suite now passes on a machine with a board already running
  on 8321.

### Stories

- `skald serve --port 0` and `skald server start` with port 0 now ask the operating system for a free port instead of silently using the configured one. The test suite passes on a machine with a board already running. (a25045)
- The Claude Code SessionStart hook written by `skald hooks claude` now runs `skald context`, a bounded orientation block, instead of listing the whole open backlog on every session start. `skald hooks claude --as NAME` bakes the agent's name into the hook; otherwise set `SKALD_AUTHOR`. Re-run the install to update an existing hook. (f3bac3)
- The migration from the unreleased 0.1 single-file layout is gone from init and the docs; 0.2.0 is the first release anyone installed. (2f74dd)
- skald resume at the right altitude: requirements section only, table of contents, --section and --full (45f306)
- Questions as a note kind: open until a later decision, surfaced in context, resume, ls, and the board with a waiting-on-a-human filter (cb3bd6)
- Lifecycle columns: idea and plan before ready, an init preset, and a plan-to-ready warning on open questions (32076e)
- Document the design-record layout: long stories, sections the tools understand, a template (4798f4)
- Lanes: facet limits so stories that must not run concurrently are not picked together (67f581)
- skald audit: check a story's paths, line references, and commit hashes against the tree, and note it (cff9e4)
- Parents: a parent field so an epic can have a body and children (fe6d27)
- Backdating flags: note --at and new --created-at for migration scripts (fcecad)
- Parents on the board and in history: children in the modal, epics merge, commits union (da2a34)

## 0.2.0 (2026-09-09)

The first release: a Python package with a CLI, a local web board, an MCP
server, and hooks for Claude Code.

### Added
- Checkouts: a project with several working trees on one machine (git
  worktrees, or a second clone) keeps one primary and knows the others.
  The board's branch dropdown lists every working tree (`worktree` or
  `clone`, directory, branch) and shows the chosen one, uncommitted changes
  included, editable; a branch a working tree is on is marked `committed
  only`. `skald projects` lists
  checkouts with branch and dirty count; `skald projects use` picks the
  primary. `next`, `claim`, and `context` see claims made in other checkouts
  before they are committed. A second checkout no longer replaces the
  registered path each time a command runs there; when the primary's
  directory has gone, a surviving checkout is promoted on the next listing.
- The board server requires a per-machine token. `skald open` handles the
  handshake through a session cookie; scripts send `Authorization: Bearer`
  with the value from `skald server token`. Requests from a non-local `Host`
  are refused. This closes cross-site requests from web pages and other
  local users.
- User guides under `docs/`: getting started, working with agents, the
  board, stories, git and CI, multiple projects, the HTTP API, and
  troubleshooting. `skald docs` generates `docs/cli.md` from the parser and
  every CLI argument now has help text. The README is the front door.
- `skald release VERSION` writes a changelog section from the done column,
  stamps the stories with `released`, archives them, and commits; stories can
  carry a `## Changelog` section written for users; `ls --release VERSION`
  lists what shipped.
- `skald completion bash|zsh|fish`: Tab completes commands, flags, story ids
  with titles, columns, tags, blockers, projects, templates, branches, and
  note kinds; `git skald` too.
- Board: multi-select with press-and-hold (or `x`), batch drag between
  columns, and a bar to move, tag, or archive the selection. `skald archive`
  and `POST .../archive` accept specific ids.
- Board: dark theme (follows the OS, or forced from the header), a Help panel
  (`?`) with shortcuts, card markers, the story file format, and the CLI
  reference served by `GET /api/help` straight from the argparse parser.
- Board: keyboard access to cards, an empty-project hint, columns that share
  the width and stack on phones, and toasts for changes made outside the
  board or a new commit on the branch.
- The `skald-kanban` package provides `skald` and `git-skald`. Until the first
  PyPI release, install it from GitHub with `pip install git+https://github.com/Vitund-AI/skald.git`.
- Machine-local project index; every command registers the current project,
  `skald projects` lists them, `-p NAME` and `--all-projects` act across them.
- `.skald/config.json` with project name, format version, and custom columns
  with roles (`backlog`, `ready`, `active`, `done`, `closed`) and WIP limits.
- Cross-project dependencies written as `project:id`.
- `assignee` field, `claim`, and `next --as`.
- Archive: `archive`, `unarchive`, `ls --archived`.
- Git integration: `status`, `commit`, `log`, `changelog`, and a commit
  button on the board. Push is opt-in via `skald config push true`.
- Identity: `--as`, `SKALD_AUTHOR`, `skald config author`, git `user.name`.
- Story templates in `.skald/templates/`.
- Claude Code hooks: `skald hooks claude --install [--strict]`.
- Background server: `skald open`, `skald server start|stop|status`.
- Board: project switcher, all-projects ready view, per-column limits, stale
  and checklist markers, dependency chips, Markdown preview, history tab,
  claim button, branch display, keyboard shortcuts, change-hash polling.
- Dependency graph: `skald graph` (Mermaid, DOT, JSON), a Mermaid block in
  the rendered snapshot, and an SVG graph toggle on the board.
- `hooks claude --install` writes a Claude Code skill; `init` writes the
  instructions pointer into `CLAUDE.md` and `AGENTS.md`.
- Git linkage and review: `Skald-Story` trailers from `commit`, `skald
  commits`, `skald diff` with a PR comment from the workflow, and `skald
  activity` for per-commit backlog events.
- Agent orientation: `skald context`, `skald resume`, note kinds
  (`--kind handoff|decision|blocker`), `--compact` JSON, an advisory
  acceptance-criteria gate, and claim awareness across worktrees with stale
  assignments offered back to `next`.
- `skald render`: a committed Markdown or HTML snapshot of the board with a
  content hash instead of a timestamp; `check` warns when it is stale;
  `commit` re-renders when enabled. `hooks git` and `hooks github` install a
  pre-commit hook and a workflow that keep it fresh.
- Facet tags: `key:value` tags drive `skald facets`, `skald epics`, per-facet
  filters and swimlanes on the board, and cross-project epic views.
- Read-only views of other branches: `skald branches`, `ls --branch`,
  `ls --all-branches`, `show --branch`, a branch dropdown on the board, and
  `?ref=` on the board and story endpoints. Reads git objects only.
- Live board updates over server-sent events, with polling as fallback.
- `skald mcp`: the store as MCP tools over stdio for agents without a shell.
- CI on Python 3.9 to 3.13, macOS and Windows; PyPI trusted publishing on tags.

### Changed
- `new` no longer adds a second `## Requirements` heading when the body
  already starts with one.
- Board: columns keep their scroll position across re-renders, so selecting
  cards or receiving a live update deep in a long column no longer jumps to
  the top.
- `skald move <id> <column>` replaces `skald mv`; `mv` still works as an
  undocumented alias for one release.
- Board: the graph toggle stays readable when active and the story modal no
  longer overflows sideways.
- README opens with a comparison of repository-native trackers so readers
  can tell whether Skald's focus matches theirs.
- Notes from the CLI default to author `agent`; notes from the board use the
  configured author or git identity.
- `check` returns warnings as well as problems and gains `--hook`.
- `ls` hides every terminal column, not just `done`.
- The web server skips the reverse DNS lookup on bind, so `skald serve` and
  `skald server start` come up instantly on macOS and offline machines.

### Fixed
- The workflow written by `skald hooks github --install` commits the rendered
  board as `github-actions[bot]`. It used to commit as
  `skald@users.noreply.github.com`, which GitHub attributes to the unrelated
  account named `skald`. Re-run the install to update an existing workflow.

### Stories

- The board draws the dependency graph, including cross-project edges, so long chains of blockers are visible at a glance. (9bf832)
- Columns are defined per project in `config.json` with roles (backlog, ready, active, done, closed) and optional WIP limits. A story with an unknown status shows in an Unknown column and is reported by `skald check`. (b5d7d7)
- A `blocked_by` entry can name a story in another registered project as `project:id`. It resolves through the machine-local index; a project not registered here counts as unmet with a warning rather than an error. (058512)
- `skald hooks claude --install` adds Claude Code hooks: SessionStart runs `skald status` and `skald ls` so every session begins oriented, and Stop runs `skald check`; `--strict` makes the stop hook fail on uncommitted story files. (aab06f)
- Story templates live in `.skald/templates/<name>.md`; `skald new --template NAME` starts from one and `skald templates` lists them. (9e4f8e)
- Select several cards with press-and-hold or `x`, drag the whole batch between columns, and use the bar at the bottom to move, tag, or archive the selection. `skald archive` and the API accept specific ids. (c78e01)
- GitHub Actions run the test suite on Linux for Python 3.9 to 3.13 and on macOS and Windows, build the wheel, and publish to PyPI from `v*` tags with trusted publishing after checking the tag matches the package version. (c5e56b)
- The board updates live over a server-sent event stream when story files change, with polling as the fallback. A toast announces changes made outside the board. (883a6a)
- `skald mcp` serves the backlog as MCP tools over stdio (list, next, show, new, move, claim, note, tag, block), so agents without shell access can work from it. Standard library JSON-RPC only. (862dae)
- Any branch's backlog can be read without touching the working tree: `skald branches`, `skald ls --branch REF`, `skald show <id> --branch REF`, and a read-only branch view on the board. The checked-out branch stays the truth. (d8a25c)
- Tags of the form `key:value` are facets. `skald facets` and `skald epics` show values with progress, the board offers a filter per facet key and swimlanes by facet, and `epic:name` tags work across projects because tags are plain strings. (cbb58e)
- `skald render` writes a Markdown or HTML snapshot of the board, by default `.skald/README.md`, so GitHub shows the backlog in place at any commit. `skald render --enable` re-renders on commit, `skald hooks git --install` adds a pre-commit hook, and `skald hooks github --install` writes a workflow that checks the backlog and refreshes the snapshot. (46b5d3)
- Notes can carry a kind: `--kind handoff`, `decision`, or `blocker` stamps the heading. `skald resume <id>` prints a story's requirements, checklist state, dependencies, and only the latest handoff, so the next session starts from the state of play. (04625a)
- A `## Acceptance` checklist in the body is an advisory gate: moving a story past the first active column or into done warns while items are unchecked, and the board shows acceptance progress on the card. (aa1ade)
- `skald context --as NAME` prints one orientation block: your assigned stories with their last note, the next unblocked story, blockers, stale claims, claims elsewhere, and uncommitted story files. `--compact` on `ls` and `next` trims the JSON. (dea072)
- `skald next` skips, and `skald claim` warns about, stories claimed by someone else on another local branch. A claim on an active story untouched for `stale_days` counts as free again, with a warning. (654c29)
- Commits link to stories through a `Skald-Story` trailer. `skald commit` writes it for the stories it touches, the contract asks agents to add it to code commits, and `skald commits <id>` and the board's History tab list the commits that reference a story. (5c4f0c)
- `skald diff --since REF --until REF` lists stories that were created, moved, claimed, or archived between two refs, as text, JSON, or Markdown. The GitHub workflow posts the Markdown as a comment on pull requests. (610eef)
- `skald activity --since REF --until REF` lists every new story, status change, claim, and note between two refs, one line per event with commit, author, and date, so a person can review what agents did overnight. (f4fa85)
- `skald hooks claude --install` also writes a Claude Code skill from the contract template, and `skald init` appends the one-line pointer to `.skald/AGENTS.md` to the root `CLAUDE.md` and `AGENTS.md`, creating `AGENTS.md` when neither exists. (419b5c)
- The dependency graph is drawn three ways: a Mermaid block in the rendered snapshot that GitHub draws, `skald graph --format mermaid|dot|json`, and a layered SVG on the board (`g`) with click-to-open. Only stories with a dependency appear. (12c4d1)
- The test suite runs on Linux for Python 3.9 to 3.13 and on macOS and Windows for 3.12, and the background server and git path handling were fixed where those platforms differed. (68a39b)
- The board has a dark theme that follows the operating system or a header toggle, columns that flex to the window, a story dialog that no longer overflows, keyboard access to cards, and empty-state messages. (c5f90f)
- The board has a Help panel (`?`): keyboard shortcuts, what the card markers mean, the story file format, and the full CLI reference generated from the same parser as `skald --help`. (bd9aca)
- The board was verified in a real browser with its stylesheet loaded, and the layout problems found were fixed. (f7674b)
- `skald mv` is now `skald move <id> <column>`, the Kanban verb. `mv` still works as a hidden alias for this release. (d3c39e)
- Skald is not on PyPI yet. The README, contract, skill, and generated workflow install from `git+https://github.com/Vitund-AI/skald.git`; the distribution is named `skald-kanban`, the command is `skald`. (1b15cc)
- `skald completion bash|zsh|fish` prints a shell script to eval. Tab completes commands, flags, story ids with their titles, columns, tags, blockers, projects, templates, branches, and note kinds; `git skald` completes the same way. (61b53c)
- The README shows the board, a story, a terminal session, shell completion, the dependency graph, and multi-select, in light and dark, with the images under `docs/images`. (664976)
- skald release VERSION turns the done column into a changelog section and archives those stories with the version they shipped in. Stories can carry a ## Changelog section written for users; ls --release VERSION shows what went out. (95e3a5)
- A docs/ folder with guides for getting started, working with agents, the board, story files, git and CI, multiple projects, and troubleshooting, plus a CLI reference generated by skald docs so it cannot drift. (71f880)
- The board server now requires a per-machine token. skald open handles it for you; scripts pass Authorization: Bearer with the value from skald server token. This closes cross-site requests from web pages and other local users. (43a999)
- The workflow written by `skald hooks github --install` commits the rendered board as `github-actions[bot]`. It used to commit as `skald@users.noreply.github.com`, an address GitHub attributes to the unrelated account named `skald`; re-run the install to update an existing workflow. (b2f19e)
- A project with several working trees on one machine keeps one primary and knows the others: git worktrees are discovered automatically and a second clone is recorded when a command runs there, without replacing the primary. The board's branch dropdown lists every working tree and shows the chosen one, uncommitted changes included and editable; `skald projects` lists checkouts and `skald projects use` picks the primary; `next`, `claim`, and `context` see claims made in other checkouts before they are committed. (8c4d2c)
- Working-tree entries in the board's branch dropdown read `worktree` or `clone`, then the directory and branch, so the closed control cannot be mistaken for a branch; a read-only branch that a working tree is on reads `committed only`, and the control's tooltip describes the current choice. (43641e)
- The README, docs index, agent contract, board Help panel, and git guide now describe working trees of several checkouts alongside branches. (b1ef9b)
- Every story that ships in 0.2.0 carries a user-facing changelog entry, so the generated release section reads as release notes rather than a list of titles. (2a929c)
- When a project's primary directory has gone and another checkout of it survives, the survivor is promoted the next time anything lists or opens the project, with a notice, instead of waiting for a command to run inside it. A project with no surviving checkout stays listed as missing. (8ffede)
- Each project carries a committed `.skald/config.json` with its name, used by cross-project references, and a format version so newer tools can refuse or migrate cleanly. (63898e)
- The story dialog renders the body as Markdown with a Preview toggle beside the editor. (e0cc9f)
- A pre-commit hook and a GitHub Actions step run `skald check`, so corrupt story files and dangling blockers never land on the main branch. (92086e)
- Notes and claims carry an identity: the CLI defaults to `agent`, overridable with `--as` or `SKALD_AUTHOR`; the board uses `SKALD_AUTHOR`, then `skald config author`, then your git `user.name`. (4ed498)
- Cards show checklist progress and mark active stories untouched for `stale_days`; the header shows the git branch; the story dialog has a History tab from git log; `n`, `/`, and `Esc` are keyboard shortcuts. (0b108f)
- `skald status` shows uncommitted story files, `skald commit` stages only `.skald/`, the board has a Commit button for changed story files, and pushing from the board is opt-in with `skald config push true`. (8d081d)
- One server shows every registered project. The header has a project switcher, and "All projects: ready work" lists ready, unblocked stories across all of them, opening each in its own project. (830b31)
- `skald archive` moves done and closed stories into `.skald/archive/` so the board and listings stay small; archived stories still satisfy `blocked_by` links and `skald unarchive` brings one back. (9a1da4)
- The board server runs in the background: `skald server start`, `status`, and `stop`, and `skald open` starts it if needed before opening the browser. `skald serve` still runs it in the foreground. (670177)
- Skald installs as a package with a global `skald` command and a `git skald` alias,. (bae374)
- Stories have an optional `assignee`. `skald next` skips stories assigned to someone else and cards show who holds them, so several agents can share one repository. (3da635)
- Every command registers the current project in a machine-local index, so one board and `-p NAME` reach every repository you use Skald in. `skald projects` lists them, `skald projects rm` forgets one, and `--all-projects` acts across all of them. (189d1b)
