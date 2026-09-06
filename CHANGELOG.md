# Changelog

## 0.2.0 (unreleased)

The single-file tool became a package. Run `skald init` once in each existing
repository to migrate; story files are unchanged.

### Added
- `pip install skald-kanban` provides `skald` and `git-skald`.
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
- Notes from the CLI default to author `agent`; notes from the board use the
  configured author or git identity.
- `check` returns warnings as well as problems and gains `--hook`.
- `ls` hides every terminal column, not just `done`.

### Removed
- The vendored `.skald/skald.py` and the `git config alias.skald` shim.
  `init` removes both.

## 0.1.0

First version: single-file `skald.py` with CLI, JSON API, and embedded board.
