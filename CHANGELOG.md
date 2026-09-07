# Changelog

## 0.2.0 (unreleased)

The single-file tool became a package. Run `skald init` once in each existing
repository to migrate; story files are unchanged.

### Added
- Board: dark theme (follows the OS, or forced from the header), a Help panel
  (`?`) with shortcuts, card markers, the story file format, and the CLI
  reference served by `GET /api/help` straight from the argparse parser.
- Board: keyboard access to cards, an empty-project hint, columns that share
  the width and stack on phones, and toasts for changes made outside the
  board or a new commit on the branch.
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

### Removed
- The vendored `.skald/skald.py` and the `git config alias.skald` shim.
  `init` removes both.

## 0.1.0

First version: single-file `skald.py` with CLI, JSON API, and embedded board.
