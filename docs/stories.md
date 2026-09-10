# Stories

Everything about the files in `.skald/`: the story format, design records,
columns, facets, templates, archiving, and releases.

## A story file

```markdown
---
title: "Implement WireGuard overlay network"
status: "ready"
rank: 20
tags: ["infrastructure", "epic:networking"]
blocked_by: ["7b21e0", "api-server:c4d811"]
assignee: "claude"
created_at: "2026-09-05T10:00:00Z"
updated_at: "2026-09-06T08:12:41Z"
---
## Requirements

Configure the wg0 interface on every node...

## Acceptance
- [x] write wg0.conf template
- [ ] systemd unit

## Changelog

Nodes now join a WireGuard overlay automatically on first boot.

## [claude] 2026-09-06 08:12 UTC · decision
Chose wg-quick over a custom unit; it handles restarts for free.
```

- The **filename** is `<id>-<slug>.md`. The six hex characters are the id;
  the slug is cosmetic and never has to match the title.
- The **frontmatter** between the `---` fences is owned by Skald. Every value
  is a JSON literal, one field per line. Change it with the CLI or the board,
  never by hand. Unknown fields are preserved, so you can add your own.
- The **body** is free-form Markdown owned by people and agents. Edit it with
  anything; `skald note` appends dated sections.

Frontmatter fields:

| Field | Meaning |
| --- | --- |
| `title` | Free text. |
| `status` | A column key from `config.json`. |
| `rank` | Position within the column; lower sorts first. `new` appends, `move` goes to the bottom of the new column, drag reorders. |
| `tags` | Lowercase, sorted, unique. `key:value` tags are facets. |
| `blocked_by` | Story ids, or `project:id` for another repository. Advisory. |
| `assignee` | Free text, omitted when empty. `next` skips stories assigned to someone else. |
| `released` | Set by `skald release`: the version the story shipped in. |
| `created_at`, `updated_at` | ISO 8601 UTC. `updated_at` moves on every write. |

## Sections the tools understand

- **`## Requirements`** is what `skald resume` prints. When the body has
  the heading, only that section is shown, followed by a one-line map of
  the other sections with their sizes; `resume --section design` prints
  one, `resume --full` prints everything. A body without the heading is
  printed whole. So the author of a long story decides the cut by where
  the heading sits.
- **Checklist items** (`- [ ]` and `- [x]`) anywhere in the body become the
  progress bar on the card.
- **`## Acceptance`** holds the definition of done. Moving a story into a
  done or closed column, or forward past the first active column, with
  unchecked items prints a warning.
- **`## Changelog`** is one or two sentences written for users. `skald
  release` uses it as the story's line in the project changelog; the title
  is the fallback.
- **Notes** are headings of the form `## [author] YYYY-MM-DD HH:MM UTC`,
  optionally followed by `· kind`. `skald note` writes them; `resume` shows
  every `decision`, every open `question`, and the latest `handoff`.
- **Questions** are notes with `--kind question`: something only a human
  can decide. A question is open until a later `decision` note on the same
  story, whoever writes it; `skald answer <id> "..."` is the human's verb
  for that. Open questions show in `skald context` under "Waiting on a
  human", as `?N` in the `Q` column of `skald ls` (`--questions` filters to
  them), and as a badge and filter on the board. They are notes rather than
  a section because a note is dated, authored, and answerable by another
  dated note.

## Long stories and design records

A story can be a design record: requirements, the design, the options
considered, what was left out, and the history, all in one file that lives
for months. The tools cope with that because they read sections by heading
and notes by their dated headings, so the layout below keeps a long body
useful without any new format:

```markdown
## Requirements
Two to ten lines: what must be true when this is done. This is what
`skald resume` prints.

## Acceptance
- [ ] one checkable item per line; `resume` and the board count these,
      and moving to done with any unchecked warns

## Design
Free-form. Options, the chosen one, why.

## Residuals
Work deliberately left out, each a candidate for its own story.

## References
Paths, commits, other stories. `skald audit` checks these.

## Changelog
One or two sentences for users; `skald release` uses them.
```

The history does not go in these sections. Questions (`--kind question`),
decisions, handoffs, and audits are dated notes appended by `skald note`,
which is what keeps the sections stable: a question is answered by a
later decision note, not by editing the body, and `resume` reads the
notes in the order that matters. `resume` prints the requirements and a
one-line map of the other sections; `--section design` or `--full` reads
the rest on request.

Put the skeleton in `.skald/templates/design.md` and create records with
`skald new "Title" --template design`. Templates stay project-owned; `init`
does not write one.

Bringing existing records in is a script's job, and two flags keep their
history honest: `skald new --created-at "2024-03-01 09:30"` sets the
creation stamps, and `skald note <id> "..." --at "2024-03-02 10:00" --kind
decision` backdates a note. Both take `YYYY-MM-DD HH:MM` in UTC, an ISO
instant, or a bare date, and both default to now.

## Columns and roles

Each project defines its columns in `.skald/config.json`:

```json
{
  "format": 1,
  "name": "api-server",
  "columns": [
    {"key": "backlog",     "label": "Backlog",     "role": "backlog"},
    {"key": "ready",       "label": "Ready",       "role": "ready"},
    {"key": "in_progress", "label": "In progress", "role": "active", "limit": 3},
    {"key": "qa",          "label": "QA",          "role": "active"},
    {"key": "done",        "label": "Done",        "role": "done"},
    {"key": "wont_do",     "label": "Won't do",    "role": "closed"}
  ]
}
```

Roles give the columns their meaning. `next` picks from `ready` columns.
`claim` moves into the first `active` column. `done` and `closed` columns are
terminal: hidden from `ls` unless `--all`, they satisfy dependencies (a
closed blocker satisfies with a warning), and `archive` and `release` act on
them. Moving into `ready`, `active`, or `done` warns about unmet
dependencies. A `limit` is a WIP limit; exceeding it warns and turns the
column count red on the board.

### The lifecycle set

`skald init --columns lifecycle` writes a set that covers ideation and
planning as well as execution:

| Column | Role | Meaning |
| --- | --- | --- |
| `idea` | backlog | captured; nobody has thought about it yet |
| `plan` | backlog | someone is writing the requirements and design |
| `ready` | ready | decided; `next` picks from here |
| `in_progress` | active | |
| `review` | active | |
| `done` | done | |

Two backlog-role columns give a gate with no new rule: not in ready means
not schedulable, so an agent can capture an idea or draft a plan and nothing
starts until a person moves it on. Moving from a backlog column into ready
while the story has an open question warns, the same way unchecked
acceptance warns on the move to done. "Waiting on a human" is not a column,
because it is a condition that can hold at any stage: it is the question
badge and filter, so a story keeps its place while it waits. Any project can
adopt the set by editing its `columns` list; existing stories keep their
status, and a status that no longer matches a column shows as unknown until
you move it.

Renaming or removing a column does not break stories: a status that matches
no column still lists, shows in an "Unknown status" column, and is reported
by `skald check`. `skald columns` prints the current set. The project `name`
is what cross-project references use, so it is the same on every clone.

## Dependencies

```sh
skald new "Write the docs" --blocked-by a3f9c2
skald block a3f9c2 +7b21e0 -c4d811        # add and remove
skald block a3f9c2 +api-server:c4d811     # another registered project
skald ls --unblocked
skald graph                               # Mermaid, DOT, or JSON
```

Dependencies are advisory: moving a blocked story forward warns and
succeeds. A missing target, a self reference, and a cycle are reported by
`skald check`. A target in a project that is not registered on this machine
counts as unmet with a warning, because you may simply not have cloned it.

## Epics: a tag, or a parent

There are two ways to say "this story is part of that one", and they suit
different sizes of thing.

A tag written as `key:value` is a facet. `epic:auth` makes an epic without a
schema change, and because tags are plain strings it works across projects:

```sh
skald new "Login form" --tags epic:auth,area:web
skald ls --tag epic:auth                  # one epic
skald ls --all-projects --tag epic:auth   # the same epic across every repo
skald epics                               # progress per epic
skald facets                              # every key and value with done/open counts
```

The board shows one filter per facet key and can split into swimlanes by
any of them.

When the epic is itself a story with a body, a design record whose pieces
ship separately, use a parent instead. A child is an ordinary story with
one extra field:

```sh
skald new "Login form" --parent a3f9c2          # inherits a3f9c2's facet tags
skald new "Session cookie" --parent a3f9c2 --no-inherit
skald set 7b21e0 parent=a3f9c2                  # parent=- clears it
skald ls --parent a3f9c2                        # the children
skald resume 7b21e0                             # shows the parent's requirements first
```

`ls` marks a parent with `(children 1/3)` and a child with `(child of
a3f9c2)`. A parent is local to the project; `check` reports a missing
parent or a cycle; `rm` refuses while children exist; moving a parent to
done with a child still open warns, as does `release`. `next` treats
children as ordinary stories, so a parent usually sits in a backlog column
while its children move. The tag stays the lightweight option and works
across repositories; the parent carries a body, questions, decisions, and
an audit date, which a tag cannot.

### Lanes

Dependencies express order. Some work has no order but must not run at the
same time: four stories that each rewrite the same migration file, say,
which collide semantically rather than as clean merge conflicts when two
agents take them in parallel worktrees. A lane is a facet with a limit:

```json
{
  "facet_limits": {"lane": 1}
}
```

in `config.json` means at most one story per `lane:` value may be active
at once, counting stories active in this checkout and stories claimed on
other branches or in other checkouts. Tag the stories that share a
resource with the same value, `lane:alembic-baseline`, and `skald next`
skips the second while the first is active, saying who holds the lane;
`claim` and a move into an active column warn and proceed. Any facet key
can carry a limit; `lane` is the convention. `skald columns` lists the
limits, `skald status` reports busy lanes, and the board's swimlane header
shows `1/1 active` in red when a lane is full.

## Templates

Put Markdown files in `.skald/templates/` and create stories from them:

```sh
skald new "Login crashes on Safari" --template bug
skald templates
```

The template becomes the body; any `--body` text is appended after it.

## Archiving

```sh
skald archive --dry-run          # what would move
skald archive                    # every done or closed story to .skald/archive/
skald archive a3f9c2 7b21e0      # only these; each must be done or closed
skald unarchive a3f9c2
skald ls --archived --all
```

Archived stories leave the board and the default listings but still resolve
by id, still satisfy dependencies, and cannot be edited until unarchived.

## Releases

`skald release VERSION` is archiving with a meaning attached: done is
finished but not shipped; archived with a version is shipped.

```sh
skald release 1.2.0 --dry-run    # preview the changelog section
skald release 1.2.0              # write it, stamp and archive the stories, commit
skald ls --release 1.2.0         # what shipped in 1.2.0
```

It takes every story in a done or closed column, writes a `## 1.2.0 (date)`
section into `CHANGELOG.md` (or `--changelog PATH`), stamps each story with
`released: "1.2.0"`, archives them, and commits with a `Skald-Story` trailer
per story. Closed stories are listed under "Not doing". If the changelog's
first section is marked unreleased, it becomes this version and the
generated list is appended to it under `### Stories`, so hand-written notes
survive; otherwise a new section goes in above the first one. Skald never
bumps version files or creates tags; `--no-commit` leaves the changes for
your own release commit. [Git and CI](git-and-ci.md) shows the whole release
flow.
