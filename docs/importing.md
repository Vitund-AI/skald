# Importing an existing backlog

Every repository with a `backlog/` or `docs/backlog/` folder faces the same
migration. `skald import` does it from a mapping file you write, shows you
the result before writing anything, and leaves a history git can follow.

```sh
skald import docs/backlog --map skald-import.json --dry-run
skald import docs/backlog --map skald-import.json --rm --rewrite-links .
git add -A && git commit -m "Move the backlog into Skald"
```

## What it does with each file

- **Title** comes from the first `# H1` line, which is dropped from the
  body. A file with no H1 is titled from its filename.
- **The body is kept byte for byte** apart from that line, lines matched by
  `strip`, blocks extracted as notes, and Windows line endings, which
  become `\n`. It is placed under `##
  Requirements` unless the body already has that heading, so `resume` shows
  the opening paragraphs and maps the rest.
- **Notes** are extracted by rules and appended as dated notes in their
  original order, using `note --at`, so the story's history reads as it
  happened. Their author is `--as NAME`, default `import`.
- **Status and tags** come from rules; `--status COLUMN` overrides every
  status rule, and `--tag TAG` (repeatable) adds a fixed tag to every story
  in the run, so a bucket imported on its own can carry `area:fleet-hosts`.
- **`created_at`** comes from a regex when the mapping has one, else from
  git: the author date of the commit that added the file, following
  renames. A file git does not know is stamped now. The dry run says which
  of the three applied to each file.
- The mapping is checked before any file is read: every regex must compile,
  a `$N` in a template must not exceed the regex's groups, `on` must name a
  subject, a status must be a column, and a notes rule needs `block` or
  `section`. The errors name the rule (`tags[2]: template refers to $2 but
  the regex has 1 group(s)`).
- Nothing is written if any file has a problem (a date that does not parse,
  a status that is not a column): the errors name the files, and you fix the
  mapping.

## The mapping file

JSON, so nothing beyond the standard library reads it. Every key is
optional. `$1` in a value is the first group of the rule's regex.

```json
{
  "created_at": {"regex": "^\\*\\*Filed:\\*\\*\\s*(\\d{4}-\\d\\d-\\d\\d)", "group": 1},
  "status": [
    {"regex": "^needs-plan-", "on": "filename", "status": "plan"},
    {"default": "idea"}
  ],
  "tags": [
    {"regex": "^([a-z-]+)/", "on": "relpath", "tag": "area:$1"},
    {"regex": "^(?:needs-plan-)?(common|sdlc)-(low|medium|high)-", "on": "filename", "tag": "track:$1"},
    {"regex": "^(?:needs-plan-)?(?:common|sdlc)-(low|medium|high)-", "on": "filename", "tag": "priority:$1"}
  ],
  "notes": [
    {"block": "^> \\*\\*Update (\\d{4}-\\d\\d-\\d\\d)[^*]*\\*\\*", "kind": "note", "date_group": 1, "until": "^(?!>)"},
    {"block": "^> \\*\\*Premise audit (\\d{4}-\\d\\d-\\d\\d)", "kind": "audit", "date_group": 1, "until": "^(?!>)"},
    {"section": "^## Open questions", "kind": "question", "per": "bullet"}
  ],
  "strip": ["^\\*\\*Priority:\\*\\*.*$", "^\\*\\*Status:\\*\\*.*$"],
  "requirements": {"wrap_body_under": "## Requirements", "unless_heading_present": true},
  "exclude": ["archived/**", "wont-do/**", "*/README.md", "THEME-*.md"]
}
```

| Key | Rule | Meaning |
| --- | --- | --- |
| `created_at` | `{regex, group, fallback}` | Searched in the body; the group is the date (`YYYY-MM-DD`, `YYYY-MM-DD HH:MM`, or an ISO instant). Sets `created_at` and `updated_at`. When the regex does not match, or there is no rule, `fallback` applies: `git-added` (the default: the commit that added the file, then now), `now`, or `error` (no match is a problem). |
| `status` | list of `{regex, on, status}` and `{default}` | The first matching rule wins; `on` is `filename`, `relpath` (under the directory you gave), `path` (under the project root), or `body` (the default). |
| `tags` | list of `{regex, on, tag}` | Every matching rule adds its tag, lowercased. `relpath` is relative to the directory you gave, so a rule on the bucket name matches only when you import the parent of the buckets; use `path` for the same rule bucket by bucket, or `--tag`. |
| `notes` | `{block, until, date_group, kind}` | A line matching `block` starts a note that runs until a line matching `until` (or the end); `date_group` names the group holding its date; blockquote markers are removed. |
| `notes` | `{section, per, kind}` | An H2 heading matching `section` and everything under it leave the body; with `per: "bullet"` each top-level bullet becomes one note of that kind, stamped at the story's `created_at`. |
| `strip` | list of regexes | Lines to drop, typically bold status lines whose meaning moved into the frontmatter. |
| `requirements` | `{wrap_body_under, unless_heading_present}` | Defaults shown above. |
| `exclude` | list of globs | Matched against the path relative to the directory you gave; `**` spans directories. |

Notes of kind `question` are open until answered, so an imported "Open
questions" section shows up in `skald context` under "Waiting on a human"
on day one.

## Links and history

`--rewrite-links ROOT` scans text files under `ROOT`, and the new stories
wherever `.skald/` is, for references to each imported file, as Markdown
links or bare paths, and rewrites them to the new story file, relative to
the referencing file. A reference is resolved against the referencing
file's directory, every ancestor of it up to `ROOT`, and the project root,
so `other.md`, `fleet-hosts/other.md` written from a sibling bucket, and
`docs/backlog/fleet-hosts/other.md` all find the file. Inside an imported
story the record's original directory is tried first, since that is where
its links pointed. `ROOT` should normally be the repository root; a
narrower `ROOT` only limits which files are scanned. It reports counts per
file.

`--rm` deletes each source file in the same operation. Commit the removals
and the new stories together: the body is unchanged apart from the title
line and the frontmatter is a few lines, so git's rename detection pairs
them and `git log --follow` on a story reaches the record's history. That
pairing needs the body to be most of the file; a record of a few lines
gains more frontmatter than it keeps body and will not pair, which costs
nothing but the `--follow` history.

`--dry-run` prints, per file, the title, status, tags, `created_at`, body
size, and every note with its stamp, then the link counts and a summary,
and writes nothing. Run it until the output is what you want.

## Why a mapping file

Backlogs differ in how they mark dates, priorities, and updates, and a
tool that guessed would guess wrong quietly. The mapping is the one place
those conventions are written down, it lives in the repository beside the
records, and the dry run shows exactly what each rule produced. There is no
MCP tool for `import`: a migration is a set-up step a person runs from a
shell, and the MCP surface stays for the operations agents perform at run
time.
