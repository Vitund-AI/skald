# Multiple projects

Skald is installed once per machine and knows every repository you have
used it in. That gives you one board for all of them and dependencies that
cross repository boundaries.

## The project index

Every `skald` command registers the current project in a machine-local
index: `~/.config/skald/projects.json` (`$XDG_CONFIG_HOME/skald` if set),
`%APPDATA%\skald` on Windows, or `$SKALD_HOME` anywhere. Nothing in that
directory is ever committed.

```sh
skald projects                    # what is registered here
skald -p api-server ls            # act on another project from anywhere
skald ls --all-projects           # everything, ids shown as project:id
skald next --all-projects         # the next story anywhere
skald epics --all-projects
skald projects rm old-thing       # forget one (files untouched)
```

The project name comes from `.skald/config.json`, so it is the same on every
clone. If you move a repository, the next command run inside it updates the
path.

## Several checkouts of one repository

A project has one name and one primary path: the checkout that `-p NAME`,
cross-project references, and the board open by default. Any other checkout
of the same repository, a git worktree or a second clone, is a checkout of
that project, not a second project. Worktrees of the primary are found on
their own through `git worktree list`; a separate clone is recorded the
first time a command runs there, with a note saying where the primary is.
Neither replaces the primary. Only when the primary's directory has gone does
the next checkout to run a command take its place, which is what you want
after moving a repository.

```sh
skald projects                    # each project, then its checkouts with branch and dirty count
skald projects use                # make this checkout the primary
skald projects use ../other-clone
```

Commands always act on the checkout you run them in. What the primary
decides is what `-p NAME` means from elsewhere and which working tree the
board shows first. On the board, the branch dropdown lists every working
tree of the project; picking one shows and edits that tree, uncommitted
changes included. See [The board](board.md#working-trees-and-branches).

Claims count across checkouts. `skald next`, `skald claim`, and `skald
context` read the other working trees, so an agent that claimed a story in
its worktree holds it for everyone the moment the file is written, not when
it commits.

## Cross-project dependencies

A `blocked_by` entry written as `project:id` points at a story in another
registered project:

```sh
skald block a3f9c2 +api-server:c4d811
skald new "Client for the new endpoint" --blocked-by api-server:c4d811
```

The dependency resolves through the index, so it works on any machine that
has both repositories. On a machine that does not, it counts as unmet and
is reported as a warning rather than an error, because you may simply not
have cloned the other repository yet. The board's dependency chips and the
graph show cross-project targets dashed and open them in the other project
on click.

Facet tags are plain strings, so an epic can span repositories:

```sh
skald ls --all-projects --tag epic:auth
```

## One board

The board server shows every registered project. Switch with the dropdown,
or choose "All projects: ready work" for a single list of ready, unblocked
stories across all of them; clicking one opens it in its project. The
server is started once with `skald open` or `skald server start` and serves
whichever project, and whichever of its checkouts, you ask for.

## Your settings

```sh
skald config                      # show all
skald config author "Jon"         # name for notes and claims made from the board
skald config push true            # the board's commit button also pushes
skald config port 9000            # board server port (default 8321)
skald config host 127.0.0.1
skald config stale_days 5         # days before an active story is marked stale (default 3)
skald config author --unset
```

Settings live in the same machine-local directory and apply to every
project, as does the board's access token (`skald server token`). Identity works like this: notes from the CLI are labelled `agent`
unless you pass `--as NAME` or set `SKALD_AUTHOR`; notes from the board use
`SKALD_AUTHOR`, then the configured `author`, then your git `user.name`.
