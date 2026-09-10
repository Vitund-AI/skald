# Decisions

A log of choices that were not obvious, with the reasoning. Newest last.
Entries marked **(autonomous)** were made without the maintainer present and
are the first things to revisit if they feel wrong.

## 0.1

### D1. The id lives in the filename, not in the frontmatter
Every story has an id (see D2 for its form). The 0.1 draft stored it twice,
as an `id:` frontmatter field and as the filename prefix, and two sources of
truth can disagree. The frontmatter field was dropped; the filename prefix is
the only place the id is written. `a3f9c2-implement-wireguard.md` has id
`a3f9c2`. Renaming a file therefore changes the id, and `check` reports the
dangling references.

### D2. Random six-hex ids instead of integers
Sequential ids produce add/add merge conflicts whenever two branches create
a story. Six hex characters are short enough to type, unique-prefix lookup
makes them shorter still, and collisions are regenerated at creation.

### D3. Frontmatter values are JSON literals
Hand-writing a YAML parser is a bug farm. Restricting every value to a JSON
literal makes the parser `json.loads` per line while the file remains valid
YAML flow syntax for any other tool. The cost is that block-style lists are
rejected as corrupt, which `check` explains.

### D4. `rank`, not `priority`
"Priority 100 sorts after priority 10" reads backwards. `rank` is a position.

### D5. Warnings never block
Dependency warnings, WIP-limit warnings, and cycle warnings are printed and
the operation proceeds. The agent is expected to read stderr and decide.

## 0.2

### D6. A pip package, not a vendored file **(autonomous, agreed in outline)**
The 0.1 single file was copied into every repository. That guaranteed
availability in any agent sandbox but meant every repository had its own
tool version and upgrades were manual. With `skald-kanban` on PyPI the tool
is installed once per machine, `git skald` comes for free from a `git-skald`
console script, and the vendored mode was dropped entirely rather than kept
as a second install path. Sandboxes without the package can use
`uvx --from skald-kanban skald` or add one line to a setup script; the
generated `AGENTS.md` says so.

### D7. Distribution name `skald-kanban`
`skald` on PyPI is an unrelated experiment logger. The import name and the
command stay `skald`; only the distribution name differs.

### D8. Auto-registration on every command, `init` for creation
A colleague who clones a repository already has the backlog. The only thing
missing is an entry in their machine-local index. Rather than an `import`
command, any command run inside a project registers it. `init` is reserved
for creating the layout and is otherwise non-destructive.

### D9. `config.json` is created lazily when missing **(autonomous)**
A 0.1 repository has no `config.json`. The first 0.2 command writes one with
a name derived from the directory and prints a notice asking for it to be
committed. The alternative, refusing until `init` is run, would break every
agent's first command after an upgrade. The file is small and committing it
is the right outcome anyway.

### D10. Project identity lives in the repository, location on the machine
Cross-project references must survive cloning, so the name is committed in
`config.json`. Paths differ per machine, so they live in `projects.json`.
Re-registering a name from a different path updates the path with a notice.

### D11. Two identity rules, one for each interface **(autonomous)**
CLI actions default to `agent` (overridable with `--as` or `SKALD_AUTHOR`)
because the CLI is primarily driven by agents. Board actions default to the
configured `author`, then git `user.name`, because the board is driven by
people. Using one rule for both would label agent notes with the human's
name whenever the human had configured one.

### D12. The commit button stages only `.skald/`
A human committing from the board while an agent has half-finished code in
the tree must not sweep that code into the commit. `git add -A -- .skald`
and `git commit -- .skald` touch nothing else. Push is off by default and
enabled only by a per-user setting, never by anything in the repository.

### D13. The API never accepts a path
Project names in URLs are resolved through the registry. The server binds to
localhost without authentication and writes files, so a browser tab must not
be able to point it at arbitrary directories.

### D14. A version hash endpoint, with events layered on top **(autonomous)**
The board originally polled a cheap hash of story file names, sizes, and
mtimes every 1.5 seconds. Server-sent events were added afterwards (D25) on
top of the same hash, so the polling endpoint stays as the fallback and the
hash remains the single definition of "something changed".

### D15. Background server writes its own state file
`serve` writes `server.json` with its pid and port on startup and removes it
on exit, whether started in the foreground or by `server start`. `status`
checks the pid is alive and the health endpoint answers, so a stale file
after a crash is ignored. On Windows `os.kill(pid, 0)` would terminate the
process, so liveness uses `OpenProcess` there.

## 0.3

### D16. Columns carry roles **(autonomous, agreed in outline)**
Custom column names are meaningless to the tool without semantics: which
column `next` reads, where `claim` moves, what satisfies a dependency, what
`ls` hides. Each column therefore declares a role from a fixed set. Several
columns may share a role, so "QA" and "In progress" can both be active.

### D17. Unknown statuses are a check problem, not a corrupt file **(autonomous)**
When someone removes a column from `config.json`, stories in it must not
vanish or start failing every command. The parser accepts any status; the
store sorts unknown ones last; the board shows an "Unknown status" column;
`check` reports them. Only `move` and `new` reject a status that is not a
column.

### D18. A closed blocker satisfies the dependency, with a warning **(autonomous)**
If a story depends on one that will never be done, blocking forever helps
nobody. The dependency counts as satisfied so work can proceed, and moving
the dependent story forward warns that it depends on closed work, which is
the cue to rethink it.

### D19. Cross-project references to unregistered projects are warnings
A reference to `other:abc123` cannot be checked when `other` is not cloned on
this machine. That is a fact about the machine, not a defect in the
repository, so `check` reports it as a warning and the dependency counts as
unmet with state `unavailable`. A reference to a registered project whose
story does not exist is a real problem.

### D20. Archived stories stay addressable **(autonomous)**
`archive` moves files to `.skald/archive/` so listings and the board stay
small. Archived stories still resolve by id, still satisfy dependencies, and
still appear in `changelog`. They cannot be edited until `unarchive`, which
keeps the archive a read-only record.

### D21. `changelog` reads git objects, not history **(autonomous)**
Diffing the frontmatter at two refs (`git show ref:path`) answers "what
became done between these refs" without replaying every commit, and it
handles files that moved to the archive by checking both locations.

### D22. Claude Code hooks: check on stop, strict is opt-in **(autonomous)**
The Stop hook runs `skald check`, so an agent cannot finish with a corrupt
backlog. `--strict` switches it to `skald check --hook`, which also fails
while story files are uncommitted; that enforces the contract but could trap
an agent that cannot commit, so it is not the default.

### D23. Markdown preview is sanitised client-side **(autonomous)**
The preview renders with marked and strips script, iframe, object, embed,
style, and link elements plus inline handlers and `javascript:` URLs. Story
bodies are written by agents, so treating them as untrusted HTML is cheap
insurance even on a localhost-only tool.

### D24. This repository keeps the default columns
Skald's own backlog uses the five default columns so the dogfooding stays
representative of a fresh install. Stories finished by an agent go to
`review`; a human moves them to `done`.

### D25. Server-sent events on the handler thread **(autonomous)**
Each open board tab holds one handler thread that checks the version hash
twice a second and writes a `change` event when it moves. That is a thread
per tab on `ThreadingHTTPServer`, which is fine for a localhost tool with a
handful of tabs. The board keeps polling every 15 seconds while the stream is
live, so a silently dead stream degrades to slow updates rather than none.

### D26. MCP errors are tool results, not protocol errors **(autonomous)**
A Skald error such as "no story matches" is information the agent should
read and act on, so `tools/call` returns it as content with `isError: true`.
JSON-RPC errors are reserved for protocol problems: unknown methods, unknown
tools, unparsable input. Warnings ride inside successful results, matching
the CLI's stderr behaviour.

### D27. Other branches are read-only overlays
Snapshots come from `git ls-tree` and `git cat-file --batch`, so viewing a
branch never checks it out, touches the index, or takes a lock. The
checked-out branch stays the only truth: nothing can be edited through a
snapshot, and a dependency being satisfied on another branch never unblocks
a story here. The board shows the difference as a badge and a dropdown, not
as a merged view, because a merged view would invite acting on state that is
not actually in the working tree.

### D28. Epics are a tag convention, not a field
`epic:auth` is an ordinary tag. That means no format change, existing
filters already work, cross-project epics fall out of `--all-projects`, and
people can invent other facets (`area`, `milestone`) without asking. The
cost is that an epic has no body of its own; a story tagged `epic:auth`
with the epic's description is the workaround if one is wanted.

### D29. Rendered snapshots carry a hash, not a timestamp
A timestamp would change on every render and make every commit touch the
snapshot. The embedded content hash changes only when something the
snapshot shows changes, so re-rendering is a no-op on an unchanged backlog,
and `check` can compare the hash to the stories to warn that the file is
stale. The commit that contains the snapshot already records when it was
made.

### D30. The snapshot lives at `.skald/README.md` by default
GitHub renders a directory's README in place, so anyone browsing into
`.skald/` sees the board with no extra click. Story links are relative, so
they work on GitHub and in local viewers. `--out` moves it elsewhere; when
the path is outside `.skald/`, `commit` stages it as well so the "stories
and snapshot travel together" property holds.

### D31. Note kinds live in the heading, not in frontmatter
A kind is appended to the note heading as ` · handoff`. That keeps the body
free-form and human-readable, needs no format bump, and lets `resume` find
the latest handoff or every decision by parsing headings. `handoff`,
`decision`, and `blocker` are conventions the contract teaches; any short
lowercase word is accepted.

### D32. The acceptance gate fires on forward moves past the first active column
Warning on every move would be noise; warning only on `done` would be too
late for a reviewer. The gate fires when a story moves into a terminal
column or forward into an active column other than the first, which is the
"ready for review" moment in every layout tried. It never fires on backward
moves. It is a warning like everything else.

### D33. `next` skips claims on other branches; `claim` only warns
Two agents in worktrees cannot see each other's assignments, so `next`
consults snapshots of other local branches and skips stories that are
active with another assignee there, printing why. `claim` warns and
proceeds, because a human may be deliberately reassigning. Remote branches
are ignored for skipping because they may be stale; they still show in
`branches`.

### D34. Stale assignments are offered back to `next`
A story assigned but untouched for `stale_days` is treated as free by
`next`, with a warning naming the previous assignee. Without this a crashed
agent's claim hides work forever. `context` lists stale active claims by
others separately so a human or agent can decide to take them over.

### D35. Commit linkage is a trailer, matched by grep
`Skald-Story: <id>` is a standard git trailer, so `git interpret-trailers`
and hosting UIs understand it, and `[<id>]` in a subject is accepted for
people who prefer that. Lookup is `git log --grep`, which is fast enough and
needs no index of our own. `skald commit` adds trailers automatically for
the stories it touches; code commits rely on the contract.

### D36. `diff` and `activity` are the same computation at two granularities
Both call `diff_states` on two snapshots. `diff` compares two refs, or a
ref and the working tree; `activity` compares each commit with its parent
across a range. A note added counts as one event; a body edit without a new
note counts as another, so agent progress and human edits read differently.

### D37. The graph is Mermaid first, SVG second, and never a library
Dependency graphs in a backlog are sparse DAGs, so a longest-path layered
layout is enough and fits in a hundred lines of vanilla JS. Mermaid text is
what GitHub renders inside Markdown, so the committed snapshot gets a graph
with no JavaScript at all. Only stories with an edge are drawn; isolated
stories would turn the graph into a grid of unrelated boxes.

### D38. The contract ships as a Claude Code skill and init writes the pointer
`AGENTS.md` only helps an agent that reads it. A skill under
`.claude/skills/skald/` is auto-invoked when backlog work comes up, and the
root `CLAUDE.md`/`AGENTS.md` pointer is the step people forget, so `init`
appends it idempotently and creates `AGENTS.md` when neither file exists.

### D39. The server binds without a reverse DNS lookup
`http.server.HTTPServer.server_bind` calls `socket.getfqdn()` on the bound
host. On macOS CI runners (and laptops on captive or misconfigured networks)
that lookup stalls for 30 seconds or more, which made the in-process test
server slow and the background daemon miss its start timeout with an empty
log. Skald only binds loopback or an explicit host, so `SkaldServer`
overrides `server_bind` to use the address as given. Nothing reads
`server_name` except the base class.

### D40. The README compares neighbours by focus, not by feature count
A checklist of features reads as a scoreboard and goes stale the moment a
neighbour ships. The comparison table instead describes design choices:
where data lives, who the tool is built for, how agents and humans reach it.
It links every project, states the month it was checked, and names the cases
where another tool is the better choice.

### D41. The board is themed through CSS custom properties, not `dark:` on every class
The page is 800 lines of inline utility classes. Doubling each colour with a
`dark:` variant would touch most of them and tax every future change. Instead
a dozen custom properties on `:root` carry the palette, a `data-theme`
attribute picks the set, and Tailwind exposes the properties as colour names.
New markup uses the semantic names and gets both themes for free; `dark:`
survives only for a few red, amber, and violet accents. The attribute is set
by a script in `<head>` so there is no flash of the wrong theme.

### D42. The Help panel's CLI reference is generated from the parser
A hand-written command list in the page would drift the first time a flag
changed. `cli.command_reference()` walks the argparse tree and `GET /api/help`
serves it; the test asserts the endpoint matches the parser exactly. Help
strings on the parser are therefore the single source for `--help`, the
board, and any future docs generator.

### D43. `move`, not `mv`, changes a story's column
`mv` was chosen to match `ls` and `rm`, but it carries file semantics: in
Unix and git, `mv` takes a source and a destination path and relocates a
file. `skald mv <id> <column>` has that shape while leaving the file where it
is, which invites a wrong reading. `ls` and `rm` do what their names say, so
they stay. `move` is Kanban's own verb for the action. `mv` remains as a
hidden alias for one release because existing notes and hooks mention it; the
Help panel and `--help` list only `move`.

### D44. Multi-select is a press-and-hold mode scoped to one column
Checkboxes on every card would clutter the board for the common case of
moving one card. A press-and-hold on a card (the maintainer's suggestion)
enters a selection mode for that card's column only, which keeps the batch
meaningful: every selected story shares a status, so "move", "tag", and
"archive" apply cleanly and the archive action can be hidden unless the
column is terminal. Clicking outside the column ends the mode, so ordinary
use resumes without a dedicated exit control; `Esc` and `x` give keyboard
users the same paths. Batch moves reuse the single-story `PATCH` rather than
a new bulk endpoint: the API stays small, warnings still come back per story,
and a partial failure leaves the board showing exactly what happened.

### D45. Completion is a self-calling shim, not argcomplete or a terminal UI
A terminal board was considered and dropped: `curses` is not in the standard
library on Windows, and it would be a second rendering of the web board. What
people actually want at the prompt is not to type hex ids, so `skald
completion` follows the pattern of `gh` and `kubectl`: the shell script is a
few lines that call `skald _complete` and print what comes back. The logic
stays in Python with access to the parser (`command_reference()`, so new
flags complete without touching the scripts) and to the story files (ids
with titles, columns, tags). `argcomplete` would have done the parser half
generically but is a third-party dependency, and it cannot know that the
word after `move` is a story id. Each Tab costs one interpreter start, which
is the same order as git's own completion.

### D46. `release` archives the done column and takes its notes from the stories
Archiving had no trigger, and "done" had no meaning beyond "finished". Tying
the two together gives the column a definition people already have in their
heads: done is not shipped yet, archived with a version is shipped. The
changelog line comes from an optional `## Changelog` section on the story
rather than the title, because titles describe work and release notes
describe outcomes; asking agents for that section at finish time makes the
release notes a byproduct of the work. Skald records the version and stops
there: bumping version files and tagging are language- and project-specific,
and doing them here would tie the tool to Python packaging. The merge rule
for an unreleased first section keeps hand-written notes, because a curated
paragraph above a generated list is what most changelogs look like.

### D47. Docs are plain Markdown pages, and the CLI reference is generated
A README that tries to be tutorial, reference, and rationale at once serves
none of them past a certain length. The guides moved to `docs/` as one page
per question a user actually has, in Markdown that GitHub renders with no
site generator to maintain; a Pages site can be layered on later without
rewriting. The command reference is the one page that would drift within
weeks if hand-written, so `skald docs` generates it from `command_reference()`
(the same source as `--help` and the board's Help panel) and a test fails
when the committed file is stale. The README keeps what a first visitor
needs: what it is, whether it fits, install, a quick start, pictures, and
links.

### D48. The board needs a token, delivered in the URL fragment
A loopback bind is not an access control: other local users can connect,
and any web page a person visits can make requests to 127.0.0.1 from their
own browser, which matters because the API reads JSON bodies whatever the
content type. A random token generated on first server start, kept in a
private file, closes both. It is passed to the browser in the URL fragment
rather than the query string because fragments never reach the server, its
log, or a Referer; the page trades it for an `HttpOnly`, `SameSite=Strict`
cookie and rewrites the URL. A `Host` check closes DNS rebinding, the one
route around same-origin rules that a cookie alone does not. The token is
generated by the server rather than at install because `pip install` has no
hook, and it lives beside `projects.json` rather than in `config.json` so a
hand edit of settings cannot expose it. Health stays open because the daemon
start-up probes it and it reveals only the version.

### D49. A project has one primary and knows its other checkouts
Projects are keyed by the name in `config.json`, because that name is what
`blocked_by` references, `-p`, and the board's project list hang on. A
second checkout of the same repository therefore cannot be a second
project, and until now it silently took over the registered path each time
a command ran there. Keying by path instead would have put two entries
under one name and pushed the tiebreak into every consumer. The fix keeps
the name as the identity and adds a list: one primary path, which only moves
when its directory has gone, plus every other checkout, recorded when a
command runs there or discovered from `git worktree list`. The board shows
any of them because the interesting case is parallel agents in worktrees,
whose work is invisible to the read-only branch views until they commit.
Checkouts travel through the API as a hash of the path rather than the path
itself, keeping the rule that the API never accepts a filesystem path. A
working tree replaces the object scan of its own branch when counting
claims, so a claim is never reported twice.

### D50. Hooks that run on every session start must be bounded
The first SessionStart hook ran `skald status && skald ls`, which is fine
on a twenty-story backlog and hundreds of rows on a real one, injected
into the agent's context not once but on every start, resume, clear, and
compaction. Hook output is paid for every time, so it must not scale with
the backlog. `skald context` was built for exactly this position and the
docs already said so; the template simply contradicted them. The hook now
runs `context`, and `ls` stays a command the agent runs when it wants the
listing. Found by an agent adopting Skald in a repository with about 180
open stories, which is the kind of thing the dogfood repository, with
fifty, could not show.
