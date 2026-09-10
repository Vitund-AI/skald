# Working with agents

Skald is built for the case where an AI coding agent does most of the work
and a person steers. This page explains the contract agents follow, why each
step is there, and how to connect the agents you use.

## The contract

`skald init` writes `.skald/AGENTS.md`. It is short, and the pointer in your
root `CLAUDE.md` or `AGENTS.md` sends every agent to it. The workflow it asks
for:

1. **Orient** with `skald context --as <name>`. One bounded block: the
   stories assigned to that name with the last note on each, the next
   unblocked story, blocked work, claims by other agents on other branches,
   and uncommitted story files. It is designed for the top of a session and
   for SessionStart hooks, where a full listing would waste context.
2. **Pick work** with `skald next`. It returns the first ready, unblocked
   story that nobody else holds, skipping stories claimed on other local
   branches and offering stale assignments back. `--json --compact` trims the
   output to what an agent needs.
3. **Claim it** with `skald claim <id> --as <name>`, which assigns the story
   and moves it into the first active column, then read `skald resume <id>`:
   the requirements, the checklist and acceptance state, dependencies, every
   `decision` note, and only the latest `handoff` note. That is what a fresh
   session needs instead of the whole file.
4. **Treat warnings as advisory.** Unmet dependencies, WIP limits, cycles,
   and unchecked acceptance criteria all warn and never block. The agent
   decides, and records the decision as a note.
5. **Record progress** with `skald note <id> "text" --as <name>`. Notes carry
   a kind in their heading: `decision` for a choice and why, `blocker` for
   something it cannot get past, `handoff` for the state it leaves behind.
   Checklist items in the body become progress on the card; a `## Acceptance`
   checklist gates moves forward with a warning.
6. **Create stories for discovered work** rather than widening the current
   one, linking real dependencies with `--blocked-by` or `skald block`.
7. **Finish** by moving to review with a closing note that says what changed
   and how it was verified, and, when the change is visible to users, a
   `## Changelog` section written for them. `skald release` copies that into
   the project changelog later. A person moves stories to done.
8. **Commit story files with the code** they describe, with a
   `Skald-Story: <id>` trailer on the commit.

The rules that follow the workflow are about safety: never hand-edit the
frontmatter, never create story files by hand, do not touch `config.json`
unless asked, prefer `--json` when parsing.

## Why it is shaped this way

- **Notes are the memory.** Sessions end, context windows fill, and the next
  agent may be a different model. Dated notes with kinds turn a story file
  into a log a fresh session can resume from. `resume` reads exactly that log
  in the order that matters.
- **Warnings, not walls.** An agent that hits a hard error stops or works
  around it in ways you did not intend. A warning plus a recorded decision
  keeps the agent moving and leaves you a trail to review.
- **Acceptance criteria are the definition of done.** Put them under
  `## Acceptance` as a checklist and the agent ticks them as it verifies each.
  The board shows the progress, and moving forward with unchecked items
  warns.
- **Commits tie it together.** The trailer lets `skald commits <id>` and the
  board's History tab show every code commit for a story, and `skald
  activity` reconstructs what happened overnight from git alone.

## Claude Code

```sh
skald hooks claude --install          # or --strict
```

This merges two hooks into `.claude/settings.json`: a SessionStart hook that
runs `skald status && skald ls`, and a Stop hook that runs `skald check` so a
session cannot end with a broken backlog. With `--strict` the Stop hook is
`skald check --hook`, which also fails while story files are uncommitted,
enforcing the commit-together rule. It also writes
`.claude/skills/skald/SKILL.md` from the contract, so Claude Code loads the
workflow as a skill whenever backlog work comes up.

`skald hooks claude` without `--install` prints what would be written.

## MCP for agents without a shell

```sh
claude mcp add skald -- skald mcp
```

`skald mcp` speaks the Model Context Protocol over stdio and exposes the
operations as tools: `skald_status`, `skald_columns`, `skald_list`,
`skald_next`, `skald_show`, `skald_new`, `skald_move`, `skald_claim`,
`skald_note`, `skald_context`, `skald_resume`, `skald_set`, `skald_tag`,
`skald_block`, and `skald_check`. Every tool takes an optional `project`
argument; without it the project is the one containing the current
directory. Warnings come back inside results, never as errors.

## Other agents

Anything that can run a command can use Skald: the CLI is the interface,
`--json` output is stable, and the contract is plain Markdown. Point the
agent's instructions file at `.skald/AGENTS.md` and give it a name to use
with `--as`. Notes made without `--as` are labelled `agent`; `SKALD_AUTHOR`
in the environment sets the default.

## Several agents at once

Agents working in parallel worktrees see each other. `skald next` skips
stories claimed by another name in another checkout of the project or on
another local branch and says so, `skald claim` warns before taking over
someone else's story, and the board marks cards claimed elsewhere with a
badge. A claim in a worktree counts from the moment the file is written,
before any commit, because the other working trees are read from disk. The
board can show each worktree's working tree, so you can watch every agent's
column mid-task; see [The board](board.md#working-trees-and-branches). An assignment that
has not been touched for `stale_days` (three by default, see
[Multiple projects](multi-project.md) for settings) is offered to `next`
again with a warning.

Dependencies never resolve across branches: a blocker done on `feature/x`
does not unblock anything on `main` until it merges.

## Reading what an agent did

```sh
skald activity --since HEAD~20     # every backlog event per commit, oldest first
skald diff --since main            # what changed on this branch vs main
skald resume a3f9c2                # the story as the next session will see it
```

The board's History tab shows the story file's commits and every code
commit that references the story. [Git and CI](git-and-ci.md) covers the
rest.
