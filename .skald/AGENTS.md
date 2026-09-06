# Working with Skald

This repository tracks its backlog with Skald. Stories are Markdown files in
`.skald/stories/`. The tool is `python3 .skald/skald.py`, which works from
any directory in the repository. `git skald ...` may also work on machines
where `skald init` has been run, but do not rely on it. The examples below
abbreviate the command to `skald`.

## Workflow

1. **Orient.** Run `skald ls` at the start of a session to see the board.
2. **Pick work.** Run `skald next --json`. It prints the first `ready`,
   unblocked story in rank order. If it prints nothing, run `skald ls --json`
   and either pick an unblocked `ready` story or ask the human.
3. **Claim it.** Run `skald mv <id> in_progress`. Then run `skald show <id>`
   and read the whole file, including any notes from humans.
4. **Warnings are advisory.** If `mv` prints a `WARNING:` about unmet
   dependencies, decide whether to stub the missing piece or work the blocker
   first. Record your decision with a note.
5. **Record progress.** Use `skald note <id> "text"` (or `skald note <id> -`
   with the text on stdin) for progress, decisions, and checklists.
6. **Discovered work.** When you find work outside the current story, create
   a story for it with `skald new "title" --body "..."` and link it with
   `--blocked-by <id>` or `skald block <id> +<other>` where a real dependency
   exists. Do not silently expand the scope of the story you are on.
7. **Finish.** Run `skald mv <id> review` with a closing note that says what
   changed and how it was verified. A human moves stories to `done`. If the
   human has told you to close stories yourself, move to `done` instead.
8. **Commit together.** Story file changes go in the same commit as the code
   they describe. Never leave `.skald/` changes uncommitted at the end of a
   task.

## Rules

- Never edit the lines between the two `---` fences of a story file by hand,
  and never create story files by hand. Use `skald new`, `skald mv`,
  `skald set`, `skald tag`, and `skald block`.
- You may edit the body of a story (everything after the second `---`) with
  any tool. Prefer `skald note` for appending.
- Any command that takes an id accepts a unique prefix: `skald show a3f`.
- Prefer `--json` output when you need to parse results.
- Exit codes: 0 success (warnings on stderr), 1 usage error or not found,
  2 corrupt story file. Run `skald check` if something looks wrong.

## Command reference

```
skald ls [--status S] [--tag T] [--unblocked] [--all] [--json]
skald next [--json]
skald show <id> [--json]
skald new "<title>" [--status S] [--tags a,b] [--blocked-by id,id] [--body TEXT | --body -]
skald mv <id> <backlog|ready|in_progress|review|done>
skald set <id> title="..." rank=N
skald tag <id> +tag -tag
skald block <id> +id -id
skald note <id> "<text>" | -   [--as LABEL]
skald rm <id> [--force]
skald check [--json]
skald serve [--port 8321] [--open]
```
