# Working with Skald

This repository tracks its backlog with Skald. Stories are Markdown files in
`.skald/stories/`. The tool is the `skald` command, which also works as
`git skald`. It runs from any directory inside the repository.

If `skald` is not installed, install it with one of:

```
pip install skald-kanban          # or: pipx install skald-kanban
uvx --from skald-kanban skald     # run without installing
```

If you cannot run shell commands, the same operations are available as MCP
tools from `skald mcp` (see the README).

## Workflow

1. **Orient.** Run `skald context --as <your-name>` at the start of a
   session. It shows what is assigned to you with the last note on each, the
   next unblocked story, blocked work, claims in other checkouts or on
   other branches, and uncommitted story files. `skald columns` shows this project's columns.
2. **Pick work.** `skald context` names the next story; `skald next --json
   --compact` prints it. Stories claimed by another agent in another
   checkout or on another branch, even before they commit, are skipped, and
   so is a story whose `lane:` tag names a lane that is busy; do not take
   one by hand, and tag work that must not run alongside other work with
   the same `lane:` value. If nothing is ready, run `skald ls --json --compact` and
   either pick an unblocked ready story or ask the human.
3. **Claim it.** Run `skald claim <id> --as <your-name>`. That assigns the
   story to you and moves it into the first active column. Then run
   `skald resume <id>`: it prints the requirements, the checklist and
   acceptance state, dependencies, decisions, and the latest handoff note,
   which is everything a previous session left for you. On a long story it
   ends with a map of the other sections; read one with `skald resume <id>
   --section <name>` or all of them with `--full`. When the story cites
   files or commits, run `skald audit <id>`: it checks that the cited
   paths, lines, and hashes still exist and lists referenced files that
   changed since the last audit, so you re-read those before building on
   the story's premises. Use `skald show <id>` only when you need the full
   history.
4. **Warnings are advisory.** If a command prints a `WARNING:` about unmet
   dependencies, decide whether to stub the missing piece or work the blocker
   first. Record your decision with a note.
5. **Record progress.** Use `skald note <id> "text" --as <your-name>`, or
   `skald note <id> - --as <your-name>` with the text on stdin. Give notes a
   kind when it fits: `--kind decision` for a choice and why, `--kind blocker`
   for something you cannot get past, `--kind question` for something only
   the human can decide. Questions are numbered Q1, Q2, ... for the story's
   life; one closes only when `skald answer <id> --question N "..."` names
   it (a plain decision note closes nothing), so keep working on whatever
   does not depend on it, and `skald context` lists every story waiting on
   a human with the question's number. `--withdraw` drops a question that
   became moot. Task-list items (`- [ ]` / `- [x]`) in
   the body show up as progress on the board. Put acceptance criteria under a
   `## Acceptance` heading as a checklist and tick them as you verify each;
   moving to review or done with unchecked items prints a warning.
6. **Discovered work.** When you find work outside the current story, create
   a story for it with `skald new "title" --body "..."` and link it with
   `--blocked-by <id>` or `skald block <id> +<other>` where a real dependency
   exists. A dependency on a story in another repository is written as
   `project:id`. Work that belongs to the story you are on but is a piece
   of its own becomes a child: `skald new "title" --parent <id>`. Do not
   silently expand the scope of the story you are on.
7. **Finish.** Move the story to the review column with a closing note that
   says what changed and how it was verified. A human moves stories to done.
   If the human has told you to close stories yourself, move to done instead.
   If the change is visible to users, add a `## Changelog` section to the
   story body first: one or two sentences written for users, not a summary
   of the work. `skald release` copies it into the project's changelog.
8. **Commit together.** Story file changes go in the same commit as the code
   they describe, and the commit message carries a trailer naming the story:
   `git commit -m "..." --trailer "Skald-Story: <id>"`. Never leave `.skald/`
   changes uncommitted at the end of a task. `skald check` tells you whether
   the backlog is consistent, and `skald status` lists uncommitted story
   files.

## Rules

- Never edit the lines between the two `---` fences of a story file by hand,
  and never create story files by hand. Use `skald new`, `skald move`,
  `skald set`, `skald tag`, `skald block`, and `skald claim`.
- You may edit the body of a story (everything after the second `---`) with
  any tool. Prefer `skald note` for appending.
- Do not edit `.skald/config.json` unless the human asks you to change the
  project's name or columns.
- Tags of the form `key:value` are facets. Use `epic:<name>` to group stories
  into an epic; `skald epics` shows progress and `skald ls --tag epic:<name>`
  lists one.
- Any command that takes an id accepts a unique prefix: `skald show a3f`.
- Prefer `--json` output when you need to parse results.
- Exit codes: 0 success (warnings on stderr), 1 usage error or not found,
  2 corrupt story or configuration. Run `skald check` if something looks wrong.

## Command reference

```
skald status                      project, branch, counts, uncommitted story files
skald context --as NAME [--json]     orientation: mine, next, blockers, claims elsewhere
skald resume <id> [--json]           requirements, checklist, deps, latest handoff
skald ls [--status COL] [--tag T] [--assignee A] [--unblocked] [--all] [--json] [--compact]
skald next [--as NAME] [--json] [--compact]
skald show <id> [--json]
skald new "<title>" [--status COL] [--tags a,b] [--blocked-by id,proj:id] [--body TEXT | --body -] [--template NAME]
skald claim <id> --as NAME
skald move <id> <column>
skald set <id> title="..." rank=N assignee=NAME
skald tag <id> +tag -tag
skald block <id> +id -id            (use project:id for another repository)
skald note <id> "<text>" | -  --as NAME [--kind handoff|decision|blocker|question]
skald answer <id> "<text>" --as NAME [--question N | --all] [--withdraw]   closes a question; nothing else does
skald log <id>                      git history of the story file
skald commits <id>                  code commits that reference the story
skald graph                         dependency graph as Mermaid
skald check [--hook]
skald columns
skald rm <id> [--force]
```
