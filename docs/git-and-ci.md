# Git and CI

Stories are committed with the code they describe, so git is where Skald
keeps its history. This page covers the commands that read and write it,
the hooks and workflow that keep things consistent, and the release flow.

## Linking commits to stories

`skald commit` commits everything under `.skald/` and nothing else, adding
a `Skald-Story: <id>` trailer for every story file it touches:

```sh
skald commit                              # message: skald: update N story file(s)
skald commit -m "Groom the backlog" --push
```

For code commits, add the same trailer yourself, or put `[a3f9c2]` in the
subject:

```sh
git commit -m "Add wg0 template" --trailer "Skald-Story: a3f9c2"
skald commits a3f9c2                      # every commit that references the story
skald log a3f9c2                          # the story file's own history
```

The board's History tab shows both lists. The agent contract asks for the
trailer on every commit, which is what makes the rest of this page work.

## Reviewing what changed

```sh
skald status                              # branch, counts, uncommitted story files
skald diff --since main                   # new, changed, removed stories vs the working tree
skald diff --since v1.0 --until v1.1 --markdown
skald activity --since HEAD~20            # every backlog event per commit, oldest first
skald changelog --since v1.0              # stories that reached done between two refs
```

`diff` compares two states by id and reports status, assignee, title, tag,
blocker, and archive changes, plus notes added. `activity` walks every
commit that touched `.skald/` and reports the same events per commit, which
is the quickest way to see what agents did overnight. `changelog` is the
read-only view; `release` below is the one that writes.

## Other branches

```sh
skald branches                            # per-branch counts and how each differs
skald ls --all-branches                   # stories that exist only on, or differ on, other branches
skald ls --branch feature/x               # a branch's board, read-only
skald show a3f9c2 --branch origin/main
```

Skald reads `.skald/` from any branch straight from git objects without
touching your working tree, so these views show committed state only; for
the uncommitted state of another worktree, the board's working-tree
entries are the tool (see [The board](board.md#working-trees-and-branches)).
The board has the same view in its branch
dropdown. Dependencies never resolve across branches.

## The committed snapshot

```sh
skald render                     # writes .skald/README.md
skald render --enable            # and make commit, the board button, and hooks re-render it
skald render --format html --out docs/board.html
```

The snapshot is Markdown by default and lives at `.skald/README.md`, so
clicking into the `.skald` folder on GitHub shows the board as of that
commit. Every id links to its story file, terminal columns are collapsed,
epics get a progress table, and the dependency graph is embedded as Mermaid.
The output is deterministic, with a content hash instead of a timestamp, so
an unchanged backlog produces no diff. `skald check` warns when the snapshot
is stale.

## Hooks

```sh
skald hooks git --install        # pre-commit: skald check, then skald render --stage
skald hooks github --install     # .github/workflows/skald.yml
skald hooks claude --install     # Claude Code SessionStart and Stop hooks, plus the skill
```

Each installer prints the hook without `--install`. The pre-commit
installer refuses to overwrite a hook it did not write. The GitHub workflow
runs `skald check` on pull requests and pushes, posts `skald diff
--markdown` as a comment on every pull request and keeps it up to date, and
commits a fresh render on the default branch. Both `git` and `github` enable
automatic rendering in `config.json` if it is not already on.

`skald check` is the thing to run anywhere you want a gate: it exits 2 on
corrupt files, dangling or self references, unknown statuses, cycles, and
conflict markers, and `--hook` also fails while story files are
uncommitted.

## Checks

Every pull request and every push to `main` runs the test suite on Linux
for Python 3.9 to 3.13 and on macOS and Windows, builds the wheel, and
lints with [ruff](https://docs.astral.sh/ruff/): pyflakes, pycodestyle,
bugbear, and the bandit-derived `S` rules, configured in `pyproject.toml`.
Ruff is a development tool only; the package itself stays standard library.
Run the same check locally with `pip install ruff` and `ruff check src
tests examples`. The few `S` findings that are intentional, git run as an
argument list, `--host 0.0.0.0` for a board on the LAN, are waived per
file in the configuration with the reason beside each.

Dependabot watches the action versions in the workflows and opens a pull
request against `dev` when a new major appears. GitHub's CodeQL default
setup, enabled in the repository settings rather than in a file, runs its
own analysis on pushes and pull requests.

## A release flow

With a `dev` branch for day-to-day work and `main` as the release line:

1. Work lands on `dev` through pull requests. The workflow checks the
   backlog and comments the diff on each one. Agents move finished stories
   to review; you move them to done as you accept them.
2. When it is time to ship, on `dev`:

   ```sh
   # bump the version file first and commit it; a test fails until the
   # changelog's newest release heading matches it
   skald release 1.2.0 --dry-run          # read the section
   skald release 1.2.0                    # CHANGELOG.md, released stamps, archive, commit
   ```

   The version is `1.2.0`, not `v1.2.0`: the `v` belongs to the tag, and
   `release` strips one if given.

3. Merge `dev` to `main`, then tag: `git tag -a v1.2.0 -m "Release 1.2.0"`
   and push the tag. The publish workflow checks the tag against the
   version file, runs the tests, builds, and publishes. A tag that does
   not match the version file fails before anything is uploaded; fix the
   file on `main`, move the tag, and push it again.

`skald release` deliberately stops at the changelog and the archive. The
version bump and the tag are the project's own, because they depend on the
language and the packaging, and a release that does not touch them is safe
to run on any repository.

## Conflicts

Two people or agents editing the same story on different branches produce
an ordinary git conflict in one Markdown file. Resolve it like any other;
`skald check` reports leftover conflict markers. The board refuses to save
a body that changed on disk while you were editing it, so concurrent edits
on one machine surface immediately instead of overwriting each other.
