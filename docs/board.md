# The board

One local web page that shows every registered project, updates live, and
needs no account: `skald open` carries the key.

```sh
skald open              # ensure the background server is running, open this project
skald server start      # or manage it explicitly
skald server status
skald server stop
skald serve             # run in the foreground instead
```

The server binds to `127.0.0.1` on port 8321 by default (`skald config port`
changes it). The page loads Tailwind and marked from CDNs, so styling and
Markdown preview need internet access; without it the board still works,
unstyled.

## Access

The server requires a key. `skald open` handles it: the first server start
generates a random token in your machine-local directory (a private file,
never committed), and `skald open` opens the board with the key in the URL
fragment. The page trades it for a session cookie and drops it from the
address bar. A board opened by typing the address shows one line asking you
to run `skald open`.

Why: a localhost bind keeps the network out, but not other users on the
machine, and not the web pages you visit, which can send requests to
`127.0.0.1` from your own browser. The cookie is `HttpOnly` and
`SameSite=Strict`, and the server refuses requests whose `Host` header is
not this machine, so neither a hostile page nor a DNS name pointing at
127.0.0.1 can ride your session.

Scripts send the same token as a header, from `skald server token`:

```sh
curl -H "Authorization: Bearer $(skald server token)" http://127.0.0.1:8321/api/projects
skald server token --rotate      # new token; browser sessions and scripts must reconnect
```

`/api/health` is the only open endpoint. Exposing the server on another
interface still means plaintext HTTP, so do that deliberately.

## Header

- **Project** switches between registered projects. "All projects: ready
  work" is a single list of ready, unblocked stories everywhere; click one to
  open it in its project.
- **Branch** shows the working tree by default. When the project has more
  than one checkout on this machine, the dropdown starts with a "Working
  trees" group: one entry per checkout reading `worktree` or `clone`, then
  the directory, the branch, and a count of uncommitted story files, such
  as `worktree skald-agent-two · agent-two · 2 uncommitted`. Choosing one
  shows that working tree, edits and all, and it is editable; a banner
  names the path. Below that, choosing a branch, local or remote, shows a
  read-only view of the backlog as it is committed there, with a banner and
  no editing; a branch that one of the working trees is on reads
  `committed only`, because the working tree above it has the rest. A badge
  counts stories that exist only on other branches. See
  [Working trees and branches](#working-trees-and-branches).
- **Filter** matches title, id, tag, or assignee. `/` focuses it.
- **Facet filters and swimlanes** appear when stories carry `key:value`
  tags. One dropdown per key filters; "swimlanes by" splits the board into
  one lane per value with a progress bar per lane.
- **Waiting on a human** appears when any story has an open question and
  filters the board to those stories; the count is in the label.
- **Graph** (`g`) draws the dependency graph.
- **Identity** is the name notes and commits from the board will carry.
- **Commit N changes** appears when story files are uncommitted. It commits
  only `.skald/` and, when enabled, the rendered snapshot; with `skald
  config push true` it can push too.
- **Theme** cycles Auto, Light, Dark. Auto follows the operating system and
  the choice is remembered per browser.
- **?** opens the Help panel: shortcuts, what the card markers mean, the
  story file format, and the full CLI reference generated from the same
  parser as `skald --help`.

## Columns and cards

Columns come from `.skald/config.json` with their labels and WIP limits; a
column over its limit turns its count red. A story whose status matches no
column appears in an "Unknown status" column. Columns share the width on
wide screens and stack vertically on phones.

A card shows the title, tags, checklist progress, id, assignee, and age.
Markers:

- **Red left edge and a lock**: blocked by an unmet dependency. Hover the
  lock for the list.
- **Amber left edge and "stale"**: an active story untouched for
  `stale_days`.
- **"also name@branch"**: the story is claimed by someone else on another
  branch.
- **"? N" in amber**: N open questions, waiting on a human. The dialog lists
  them, and its Answer button appends your text as a decision note, which
  closes them.

Drag a card to move it between columns or reorder it within one. Tab
reaches cards and Enter opens them. Clicking a card opens it.

## The story dialog

Title, status, assignee, tags, and blockers are editable fields. Dependency
chips below them show each blocker's state and open it on click, switching
project if it lives elsewhere. The body is Markdown with a Preview toggle;
Save writes it back and refuses with a message if the file changed on disk
while you were editing, so nothing is silently overwritten. Add a note
appends a dated note under your identity. Claim assigns the story to you and
starts it. Delete removes the file, asking first if other stories depend on
it. The History tab lists code commits that reference the story above the
story file's own history.

## Selecting several cards

Press and hold a card for about half a second, or press `x` on a focused
card, to start a selection in that column. Every card in the column shows a
circle; selected ones show a check. Click cards to add or remove them. Drag
any selected card and the whole batch moves, landing in selection order at
the drop point. The bar at the bottom moves the batch to a column, adds a
tag to each story, or archives them when the column is done or closed.
Clicking in another column or pressing `Esc` ends the selection.

<img src="images/multi-select.png" alt="Three cards selected in the Review column with the bulk action bar offering Move to, a tag box, and Clear" width="100%">

## Working trees and branches

The dropdown offers two different things. A **working tree** is a checkout
of the project on this machine: the primary, a git worktree, or another
clone. Its view is the files on disk, so an agent working in a worktree
shows up mid-task, claims and notes included, before it commits anything.
Everything works there: drag, edit, notes, claims, and the commit button,
which commits in that checkout on its branch. Cards claimed in another
working tree show the "also name@branch" badge, so two agents in two
worktrees cannot both take a story.

A **branch** is a read-only snapshot of what is committed there. Use it to
review a branch you do not have checked out, or to compare. It cannot show
uncommitted work, which is why worktrees get their own entries, and why a
branch with a working tree on it is marked `committed only`. Hovering the
control says which of the two the current choice is.

Worktrees are found from `git worktree list` each time the list is
refreshed, which the board does every thirty seconds while the tab is
visible, so a new worktree appears within half a minute of `git worktree
add` and leaves when it is removed; nothing needs to run inside it. A
separate clone is the one case that needs a `skald` command run inside it
once, because nothing else can find it. The address bar carries an opaque
id for the checkout shown, never a path. See [Multiple projects](multi-project.md#several-checkouts-of-one-repository)
for how the primary is chosen.

## The graph

`g` toggles a layered dependency graph. Only stories with a dependency
appear, so it stays readable. Nodes are coloured by column role,
cross-project targets are dashed, satisfied edges are grey, unmet edges are
highlighted, and cycles are red. Click a node to open it.

<img src="images/graph.png" alt="The board's graph view: blockers on the left, blocked stories on the right, arrows coloured by whether the dependency is met" width="100%">

## Live updates

The page listens to a server-sent event stream, so a change made from the
CLI, by an agent, or by a hook appears within a second without a refresh. A
toast announces changes made outside the board and new commits on the
branch. Columns keep their scroll position across updates.

## Keyboard shortcuts

| Key | Action |
| --- | --- |
| `n` | New story |
| `/` | Focus the filter |
| `g` | Toggle the graph |
| `?` | Help |
| `x` | Start or toggle selection on the focused card |
| `Tab`, `Enter` | Move between cards, open the focused one |
| `Esc` | Close a dialog, end a selection |
