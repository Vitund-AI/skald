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
whichever project you ask for.

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
