# Working with Skald

This repository tracks its backlog with Skald. Stories are Markdown files in
`.skald/stories/`. The tool is the `skald` command, which also works as
`git skald`. It runs from any directory inside the repository.

If `skald` is not installed, install it with one of:

```
pip install skald-kanban        # or: pipx install skald-kanban
uvx --from skald-kanban skald   # run without installing
```

## Workflow

1. **Orient.** Run `skald status` and `skald ls` at the start of a session.
   `skald columns` shows this project's columns and their roles.
2. **Pick work.** Run `skald next --json`. It prints the first ready,
   unblocked, unassigned story. If it prints nothing, run `skald ls --json`
   and either pick an unblocked ready story or ask the human.
3. **Claim it.** Run `skald claim <id> --as <your-name>`. That assigns the
   story to you and moves it into the first active column. Then run
   `skald show <id>` and read the whole file, including notes from humans.
4. **Warnings are advisory.** If a command prints a `WARNING:` about unmet
   dependencies, decide whether to stub the missing piece or work the blocker
   first. Record your decision with a note.
5. **Record progress.** Use `skald note <id> "text" --as <your-name>`, or
   `skald note <id> - --as <your-name>` with the text on stdin, for progress,
   decisions, and checklists. Task-list items (`- [ ]` / `- [x]`) in the body
   show up as progress on the board.
6. **Discovered work.** When you find work outside the current story, create
   a story for it with `skald new "title" --body "..."` and link it with
   `--blocked-by <id>` or `skald block <id> +<other>` where a real dependency
   exists. A dependency on a story in another repository is written as
   `project:id`. Do not silently expand the scope of the story you are on.
7. **Finish.** Move the story to the review column with a closing note that
   says what changed and how it was verified. A human moves stories to done.
   If the human has told you to close stories yourself, move to done instead.
8. **Commit together.** Story file changes go in the same commit as the code
   they describe. Never leave `.skald/` changes uncommitted at the end of a
   task. `skald check` tells you whether the backlog is consistent, and
   `skald status` lists uncommitted story files.

## Rules

- Never edit the lines between the two `---` fences of a story file by hand,
  and never create story files by hand. Use `skald new`, `skald mv`,
  `skald set`, `skald tag`, `skald block`, and `skald claim`.
- You may edit the body of a story (everything after the second `---`) with
  any tool. Prefer `skald note` for appending.
- Do not edit `.skald/config.json` unless the human asks you to change the
  project's name or columns.
- Any command that takes an id accepts a unique prefix: `skald show a3f`.
- Prefer `--json` output when you need to parse results.
- Exit codes: 0 success (warnings on stderr), 1 usage error or not found,
  2 corrupt story or configuration. Run `skald check` if something looks wrong.

## Command reference

```
skald status                      project, branch, counts, uncommitted story files
skald ls [--status COL] [--tag T] [--assignee A] [--unblocked] [--all] [--json]
skald next [--as NAME] [--json]
skald show <id> [--json]
skald new "<title>" [--status COL] [--tags a,b] [--blocked-by id,proj:id] [--body TEXT | --body -] [--template NAME]
skald claim <id> --as NAME
skald mv <id> <column>
skald set <id> title="..." rank=N assignee=NAME
skald tag <id> +tag -tag
skald block <id> +id -id            (use project:id for another repository)
skald note <id> "<text>" | -  --as NAME
skald log <id>                      git history of the story
skald check [--hook]
skald columns
skald rm <id> [--force]
```
