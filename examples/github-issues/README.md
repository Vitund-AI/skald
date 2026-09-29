# GitHub issues into the backlog

`sync.py` pulls a repository's GitHub issues into its Skald backlog. It only
reads from GitHub, and it is safe to run as often as you like: an issue that
already has a story is skipped, so the board never gets duplicates.

```sh
cd your-repo                                   # a checkout with skald init done
python3 examples/github-issues/sync.py --dry-run   # what it would create, and any drift
python3 examples/github-issues/sync.py             # do it
git add .skald && git commit -m "Import GitHub issues"
```

It needs the [`gh` CLI](https://cli.github.com), logged in, and the `skald`
package on the Python you run it with. `--repo OWNER/NAME` points it at a
repository other than the one `gh` sees from the current directory.

## What carries over

| GitHub | Skald |
| --- | --- |
| Issue title | Story title |
| Issue body | Story body, under a link back to the issue |
| Issue number | A `gh:<number>` tag, which is how a re-run knows the issue is imported |
| Labels | Tags: `Type: Bug` becomes `type:bug`, `good first issue` becomes `good-first-issue` (`--no-labels` to skip) |
| Created date | The story's `created_at` |
| Comments | Dated notes of kind `comment`, by the commenter's login |

Not carried: assignees, milestones, reactions, the issue's author, and
anything that changes on GitHub after the story exists. New stories go to
the project's default column (`--status` to choose another). Only open
issues import by default; `--state all` includes closed ones.

## Re-running, and drift

A story is matched to its issue by the `gh:<number>` tag, archived stories
included, so work that has already shipped is not imported again. The script
never edits a story it created earlier, because by then the story is yours:
you have planned it, split it, or moved it on. Instead it reports drift, and
you settle it by hand:

- an issue closed on GitHub whose story is still open;
- a story done or archived whose issue is still open;
- an issue retitled since it was imported.

## Keep the `gh:` tag out of the facet views

Every `key:value` tag is a facet, and `gh:` has a different value on every
story, so it would fill the board's facet filter and swimlane menu with one
entry per issue. Exclude it in `.skald/config.json`:

```json
{ "facets": { "exclude": ["gh"] } }
```

The tag still works everywhere a tag does: `skald ls --tag gh:12` finds the
story for issue 12. See [Conventions](../../docs/conventions.md#keeping-a-key-out-of-the-facet-views).

Syncing more than one repository into one project? Give each its own key
(`--key web`, `--key api`) so issue numbers cannot collide, and exclude each.

## Why one way

Skald does not sync with hosted trackers (see the comparison in the
[README](../../README.md)), and a migration is a step a person runs, not a
core feature ([DECISIONS.md](../../DECISIONS.md) D60). Two-way sync would
need conflict rules for when both sides changed, a status map that does not
exist (six columns against open and closed), a way to stop notes and
comments echoing back and forth, and a token that can write to someone's
tracker. The one write-back that avoids all of that, closing the issue when
its story ships, is a separate idea on the backlog.

## Testing without `gh`

`--from-json FILE` reads the output of
`gh issue list --state all --json number,title,body,labels,createdAt,url,state,comments,author`
instead of calling `gh`; the repository's tests run the script this way.
`--json` prints the summary as JSON.
