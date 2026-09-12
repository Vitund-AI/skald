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
for Python 3.10 to 3.14 and on macOS and Windows, builds the wheel, and
lints with [ruff](https://docs.astral.sh/ruff/): pyflakes, pycodestyle,
bugbear, and the bandit-derived `S` rules, configured in `pyproject.toml`.
A change that touches only documentation the tests never read (the
README, the guides under `docs/`, the policies, SPEC and DECISIONS) skips
the lint and test jobs: a first job classifies the changed files with
`scripts/docs_only.py` and the others run on its answer. `CHANGELOG.md`,
`docs/cli.md`, `.skald/`, and the contract template count as code, since
tests read them. The skip is a job condition rather than a path filter on
the workflow, because a workflow that does not run leaves a required
status check pending forever, while a skipped job satisfies it.
Ruff is a development tool only; the package itself stays standard library.
Run the same check locally with `pip install ruff` and `ruff check src
tests examples scripts`. The few `S` findings that are intentional, git run as an
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
2. When it is time to ship, with every change for the release merged into
   `dev` and the accepted stories in done, run the release script from
   `dev`:

   ```sh
   scripts/release.sh 1.2.0 --dry-run     # every check, and the changelog section it would write
   scripts/release.sh 1.2.0
   ```

   The script stops at the first thing that is not as expected, before it
   has changed anything: it must be on `dev`, clean, and in step with
   `origin/dev`; the version must be `1.2.0` (the `v` belongs to the tag),
   newer than the one in the version file, and not yet tagged locally or
   on origin; `skald` and a logged-in `gh` must be on the path. Then, in
   order, and each step visible:

   - `skald release 1.2.0 --dry-run`, shown for confirmation.
   - Bump `src/skald/__init__.py`, `skald release 1.2.0` (changelog
     section, `released:` stamps, archive, commit), commit the bump, run
     the tests. The bump and the release land together because the version
     guard test fails while the version file is ahead of the changelog's
     newest release heading.
   - Push `dev`, open the pull request from `dev` to `main`, wait for its
     checks, merge it. The release commit gets the full matrix before it
     reaches `main`, and a pull request is the shape branch protection on
     `main` requires.
   - Tag `main` `v1.2.0` and push the tag. The publish workflow checks the
     tag against the version file, runs the tests, builds, and waits for
     approval on the `pypi` environment before uploading; the script prints
     where to approve.
   - Merge `main` back into `dev` and push, so the render job's commits on
     `main` do not conflict at the next release.

   Every step is an ordinary git or `skald` command, so a run that stops
   halfway (a failed check on the pull request, say) is finished by hand
   from that step; the script says which. A tag that does not match the
   version file fails in the publish workflow before anything is uploaded;
   fix the file through `dev` and `main`, delete the tag locally and on
   the remote, and tag again.

## Patching an earlier release

Only the latest release receives fixes as a rule (see
[SECURITY.md](../SECURITY.md)). When a maintainer decides an earlier line
needs a patch, a security fix for a version people cannot yet upgrade
from, say, the flow is:

1. **Fix forward first.** Land the fix on `dev` through a pull request and
   release it from `main` as usual, so the current line is fixed before any
   backport exists.
2. **Cut the maintenance branch from the tag**, on demand. Nothing is
   prepared in advance; the tag is enough:

   ```sh
   git fetch --tags
   git checkout -b release/0.3 v0.3.0        # or the latest 0.3.x tag
   git cherry-pick <the fix's commit>        # resolve conflicts against the old code
   ```

3. **Version and changelog on the branch.** Set `__version__` to `0.3.1`
   and add a `## 0.3.1 (date)` section above `## 0.3.0` in `CHANGELOG.md`
   with the fix, by hand; `skald release` is for the current line. The
   version guard test holds on the branch because its newest heading
   matches. Run the tests on the branch.
4. **Tag on the branch and push both:**

   ```sh
   git commit -am "Release 0.3.1"
   git tag -a v0.3.1 -m "Release 0.3.1"
   git push origin release/0.3 v0.3.1
   ```

   The publish workflow runs on any `v*` tag whatever branch it is on,
   checks the tag against the version file, tests, builds, and waits for
   approval. PyPI accepts 0.3.1 after 0.5.x exists, and anyone pinned
   below 0.4 gets it on their next install.
5. **Tell people.** Publish the advisory naming the affected and fixed
   versions on every line, and add a line to the changelog on `dev` noting
   the backport (`0.3.1 also carries this fix`). Yank the vulnerable
   releases on PyPI if the severity warrants it.

The branch stays as the record of what was released; it is not merged back,
because the fix already exists on `main`. A second patch on the same line
is another cherry-pick onto the same branch.

Two rules that hold everywhere: a tag is never deleted or moved once a
release has been published from it, and a release on PyPI is yanked, never
deleted, unless the artifact itself contains something that must not
exist, such as a leaked secret. Yanking keeps the files for anyone who has
pinned the exact version and hides the release from every other resolver;
deleting breaks existing lockfiles and burns the version number for good.

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
