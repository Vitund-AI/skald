# Stories

Everything about the files in `.skald/`: the story format, columns, facets,
templates, archiving, and releases.

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
  every `decision` and the latest `handoff`.

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

## Facets and epics

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
