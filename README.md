# Skald

Track work from idea to release, in Markdown, in your repo, with your coding
agents.

Skald turns a folder of Markdown files into a backlog that travels with your
code. Capture an idea, plan it, hand it to an agent, answer the questions it
raises, review the result, and ship it in a release, with every step recorded
as a dated note in the story's own file. Agents drive it from a small CLI that
fits in a session's context. You drive it from a local board that shows every
project and worktree on the machine. There is no database and no service: one
dependency-free Python package, and git is the history.

```
.skald/
├── config.json   # project name, story format version, columns  (committed)
├── AGENTS.md     # what an agent needs to know, written by `init` (committed)
├── stories/      # one Markdown file per story                   (committed)
│   └── a3f9c2-implement-wireguard-overlay.md
└── archive/      # stories shipped in a release, moved out of the way
```

Stories are committed with the code they describe, so the board travels with
the branch and shows up in pull request diffs.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/board-dark.png">
  <img src="docs/images/board-light.png" alt="The Skald board showing this repository's backlog: Backlog, Ready, In progress, Review, and Done columns, a story claimed by an agent, and a button to commit the changed story files" width="100%">
</picture>

<table>
<tr>
<td width="50%" valign="top"><img src="docs/images/cli-session.png" alt="A terminal session: skald status, skald claim, skald resume, a handoff note, skald move, and skald diff"></td>
<td width="50%" valign="top"><img src="docs/images/story.png" alt="A story open on the board with a dependency chip, an acceptance checklist, and dated notes"></td>
</tr>
<tr>
<td align="center"><sub>An agent's session: claim, resume, hand off, move, and see the diff.</sub></td>
<td align="center"><sub>The same story on the board: dependencies, acceptance criteria, notes.</sub></td>
</tr>
</table>

## What you get

- **A workflow agents can follow.** `context` orients a session in one
  block, `next` and `claim` pick work without stepping on other agents,
  `resume` reads what the last session left behind, notes carry kinds such
  as `decision` and `handoff`, and acceptance checklists gate the move to
  done. The contract is one Markdown file that `init` writes for you.
- **A board for the human.** Every registered project in one page, live
  updates, drag, multi-select, dependency graph, the working tree of every
  worktree on the machine, read-only views of other branches, dark mode,
  and a Help panel with the full CLI reference.
- **Git as the database.** Story changes commit with the code they describe
  and carry `Skald-Story` trailers. `diff`, `activity`, and `changelog` read
  history back; `render` commits a snapshot GitHub shows in place; `release`
  turns the done column into a changelog section and a versioned archive.
- **More than one repository.** A machine-local index gives you one board
  and `project:id` dependencies across every repository you use Skald in.
- **Nothing to run.** Python standard library only, Python 3.9 or newer,
  Linux, macOS, and Windows. Tab completion for bash, zsh, and fish.

## Is Skald the right tool?

Several projects keep a tracker inside the repository. They make different
trade-offs, so this table is about focus rather than ranking. Checked against
each project's README in September 2026; follow the links for current detail.

| | [Skald](https://github.com/Vitund-AI/skald) | [Backlog.md](https://github.com/MrLesk/Backlog.md) | [Beads](https://github.com/steveyegge/beads) | [git-bug](https://github.com/git-bug/git-bug) | [git-issue](https://github.com/dspinellis/git-issue) |
|---|---|---|---|---|---|
| Data lives in | Markdown files under `.skald/`, committed | Markdown files under `backlog/`, committed | Dolt database under `.beads/`, with a JSONL export | Git objects, not files in the worktree | Text files under `.issues/`, committed |
| Unit of work | Story: column, rank, dependencies, tags, dated notes | Task: status, acceptance criteria, dependencies, labels, milestones | Issue: status, priority, assignee, dependencies, labels, hierarchy | Issue with comments, labels, status | Issue with comments, tags, assignee, milestone, due date |
| Built for | Coding agents first, humans reviewing on a board | Humans and agents together | Agents, with memory decay of closed work | Humans, distributed and offline-first | Humans, git-native |
| Agent interface | CLI, MCP server, Claude Code hooks and skill, `AGENTS.md` | CLI, MCP server, `AGENTS.md` | CLI with JSON output, MCP server, `AGENTS.md` | CLI | CLI |
| Human interface | Local web board across all projects on the machine | Terminal board and local web board | CLI | CLI, TUI, web UI | CLI |
| More than one repository | Yes: one board, `project:id` references | One project per workspace | Separate repos with routing and sync | Per repository, pushed to remotes | Per repository |
| Work in progress across worktrees | Board shows each checkout's working tree; a claim in a worktree is seen before it is committed | Files per checkout; the MCP server follows the current worktree | Not documented | Shared: issues are git objects, not files | Files per checkout |
| Committed snapshot | `skald render` writes Markdown or HTML with a dependency graph | `backlog board export` writes a Markdown report | No | No | No |
| Sync with hosted trackers | No | No | No | Bridges to GitHub and GitLab | Import and export with GitHub and GitLab |
| Runtime | Python, standard library only | TypeScript on Bun or Node | Go | Go | Shell, `jq`, `curl` |

Skald is a good fit when agents do most of the work, a human wants to see
that work on one board across repositories, and the backlog should read well
in a pull request diff. Reach for something else when you want threaded
discussion on issues (git-bug, or the hosted tracker you already use), a long
history that needs summarising to save context (Beads), or two-way sync with
GitHub issues (git-bug, git-issue).

## Install

```sh
pip install skald-kanban
# or: pipx install skald-kanban
# or: uv tool install skald-kanban
# latest from source: pip install git+https://github.com/Vitund-AI/skald.git
cd your-repo
skald init
```

The distribution name is `skald-kanban`; the command is `skald`, and `git
skald` works too. `init` creates `.skald/`, writes the agent contract, registers the
project on your machine, and points your `CLAUDE.md` or `AGENTS.md` at the
contract. Shell completion is one line in your rc file:

```sh
eval "$(skald completion zsh)"       # or bash; fish: skald completion fish > ~/.config/fish/completions/skald.fish
```

## Quick start

```sh
skald new "Implement WireGuard overlay" --tags infra --body "Configure wg0 on every node."
skald new "Write the network docs" --status ready --blocked-by a3f9c2
skald ls
skald open            # starts the board server if needed and opens this project
```

An agent's session looks like this:

```sh
skald context --as claude         # mine, next, blockers, claims elsewhere, uncommitted
skald claim a3f9c2 --as claude    # assign it and move it to in_progress
skald resume a3f9c2               # requirements, checklist, deps, latest handoff
skald note a3f9c2 "Why we chose X" --as claude --kind decision
skald note a3f9c2 "Done: ... Remaining: ... Next: ..." --as claude --kind handoff
skald move a3f9c2 review
git add .skald src && git commit --trailer "Skald-Story: a3f9c2"
```

For Claude Code, `skald hooks claude --install --as claude` adds a
SessionStart hook that runs `skald context` so every session begins
oriented without reading the whole backlog, a Stop hook that refuses to end
with a broken backlog, and a skill that loads the contract. Agents without a
shell can use `skald mcp`.

## Documentation

| Page | Read it when |
| --- | --- |
| [Getting started](docs/getting-started.md) | You are installing Skald or adding it to a repository. |
| [Working with agents](docs/working-with-agents.md) | You want to know what the contract asks for and why, and how to hook Claude Code or any MCP client up to it. |
| [The board](docs/board.md) | You want every board feature in one place. |
| [Stories](docs/stories.md) | You want the file format, the design-record layout for long stories, columns and roles, facets and epics, templates, archiving, and releases. |
| [Git and CI](docs/git-and-ci.md) | You want commit trailers, reviewing what changed, the committed snapshot, hooks, the GitHub workflow, and the release flow. |
| [Multiple projects](docs/multi-project.md) | You have more than one repository, or more than one checkout of one. |
| [Importing](docs/importing.md) | You have an existing folder of Markdown records to bring in. |
| [CLI reference](docs/cli.md) | You need the exact flags. Generated from the parser. |
| [HTTP API](docs/api.md) | You are scripting against the board server. |
| [Troubleshooting](docs/troubleshooting.md) | Something printed an error or looks wrong. |
| [Examples](examples/) | Worked setups on top of the core: routing stories to model-pinned agents by tag, with a report on what each model finished. |

The design is in [SPEC.md](SPEC.md) and the reasoning behind non-obvious
choices in [DECISIONS.md](DECISIONS.md).

## Development

```sh
pip install -e .
python -m unittest          # standard library only
ruff check src tests examples   # the lint CI runs (pip install ruff)
skald serve                 # run against this repository's own backlog
skald docs                  # regenerate docs/cli.md after changing a command
```

This repository dogfoods Skald: its own backlog is in `.skald/`, and the
board rendered from it is at [.skald/README.md](.skald/README.md).

## License

MIT. See [LICENSE](LICENSE).
