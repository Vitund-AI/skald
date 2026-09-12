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

### D51. No rename command; a rename with references would be an alias
A story proposed `skald rename NEW` that would update `config.json`, the
registry, and every `blocked_by` reference in every registered project.
Dropped. The common rename happens early, when the name chosen at `init`
from the directory turns out wrong and no cross-project reference exists
yet; that is one line in `config.json` plus `skald projects rm` for the
stale row, both already available. The rewriting part is the only thing
the command would add, and it cannot be done well: it would edit story
files in other repositories on this machine, uncommitted, and leave every
other clone, branch, and colleague still pointing at the old name. It
would also be the one command that writes outside the repository it is
run in. If a rename with live references ever comes up, the answer is an
alias: `config.json` gains `"aliases": ["old-name"]`, the registry indexes
aliases, and old references keep resolving on every clone with nothing
rewritten. Not built until someone needs it.

### D52. The 0.1 migration is gone, because nobody had 0.1
`init` deleted a vendored `.skald/skald.py` and the matching git alias, and
the docs carried upgrade sections, all for a layout that never left this
repository. Code that migrates from a state no user has ever been in is
clutter for every reader and a test surface with no purpose, so it was
removed rather than kept "just in case". The decisions that mention 0.1
(D1, D6, D9) stay as written: they record why the design is what it is.

### D53. A heading, not a length limit, decides what `resume` prints
`resume` printed everything above the first note, which on a design record
of several hundred lines was the design, the options, and the history,
every session, before the agent had asked for any of it. The fix is not a
line cap: a cap would cut mid-sentence at a number nobody can see in the
file. The `## Requirements` heading that `new` already writes is the cut.
When it exists, `resume` prints that section and a map of the rest, and an
agent pays for a section only when it asks. Bodies without the heading are
unchanged, so nothing existing prints differently unless its author put
the heading there on purpose. `release` reads the changelog section from
the prelude, not the requirements, so it is unaffected.

### D54. A question is a note, not a section, and any later decision closes it
Design records carried a section of open questions for the owner,
invisible until an agent reread the record, and answered by hand with
strikethrough. A section has no date, no author, and no way to be
answered by something with a date and an author, which is why the
strikethrough convention grew. A note has all three, so a question is
`note --kind question` and an answer is `note --kind decision`; nothing
new in the file format. The closing rule is coarse on purpose: one dated
decision after the question closes every question before it, whatever it
says. A decision that names the question it answers is a refinement to
build only if the coarse rule proves noisy. "Waiting on a human" is
derived from that, never a column, because it is a condition that can
hold at any stage; a column would lose where the story was.

*Addendum, after the first adoption review.* Design records carry several
unrelated questions, so a decision about one silently closed the others.
The refinement is `answer --question N`: the decision's first line names
the question it answers (`Answers [author] stamp · its first line`, since
two questions can share an author and a minute), and `open_questions`
closes only that one. A decision without that line still closes
everything, so the coarse rule remains the default and the file format is
unchanged. The `context` section that lists waiting stories is capped at
five, newest first, for the reason in D50: it runs on every session start.

*Second addendum, after the first real design story.* The coarse rule
lasted one release. On a design story decisions and questions interleave,
so an agent that recorded a choice as a decision, which is what the
contract asks, closed four questions the owner had not answered, twice in
one session, and could not tell from the output which ones. So closing is
explicit: a decision closes only the questions its leading lines name,
`answer` is the only verb that writes those lines, and `note --kind
decision` is what it says. Questions are numbered by order of appearance
rather than by position among the open ones, because the latter shifts
every time one closes and is racy across two agents; the tool still
matches on author, stamp, and first line, and the Q-label is for the
person reading the file. `--withdraw` exists so a dropped question leaves
a trail that says dropped, not answered. The format did not change: the
naming line was already in the file as of 0.4.0, so the cost is that
questions a plain decision used to close are open again, which is the
honest state for the ones never answered, and `check` lists the rest.

### D55. The lifecycle is two backlog columns, and waiting is not one of them
A full lifecycle from idea through plan and discussion to execution needs
no new role: two columns with the `backlog` role before `ready` are the
whole gate, because "not in ready means not schedulable" is already the
rule `next` follows. A `plan` role or a `design` role would have added a
concept for a distinction the roles already make. The one thing the
lifecycle needed from the code is a warning on the move that matters,
backlog to ready with an open question, which is the human's gate in the
same sense that acceptance is the gate to done. "Waiting on a human" was
proposed as a column between plan and ready and rejected: it is a
condition that can hold in plan, in progress, or in review, and a column
can hold only one state, so moving a story there loses where it was and
moving it back is a step someone forgets. The question badge and filter
show the same set without the loss. The preset is opt-in at `init`; the
default set is unchanged so nothing existing moves.

### D56. Mutual exclusion is a facet limit, not a new relation
Four stories that each rewrote one migration file had no order between
them, so `blocked_by` could not say "not at the same time", and running
them in parallel worktrees produced an enum that silently went missing
rather than a merge conflict anyone would notice. The only tool was a
note saying "serial". The constraint is about concurrency of a resource,
and facets already name resources, so a lane is a facet key with a limit
in `config.json`, and the rule is the one column limits already follow:
`next` skips, `claim` and `move` warn, nothing refuses. Counting claims on
other branches and in other checkouts is what makes it hold across
agents, and that knowledge already existed for claims. A new relation or
a new field would have needed its own syntax, validation, and rendering
for something a tag and one config key express.

### D57. `audit` checks claims; the agent checks premises
Design records cite `path:line` references and commit hashes by the
hundred, and both drift within days. Agents wrote hand-made "premise
audit" blocks re-verifying every checkable claim, rarely, because the work
is dull and the record is long. The dull half is mechanical: does the
path exist, is the file that long, is the hash a commit, which cited
files changed since the last look. That is the whole of `audit`. It
deliberately does not judge whether the headline is still true, because a
tool that says "still valid" will be believed, and the code can only show
that nothing it can see has changed. The split keeps the command honest:
it lists, the agent decides, and the decision goes in an ordinary note
beside the audit note. Identifier grepping was proposed and left out: a
backticked token with zero hits could be prose or a rename, so the result
would have been "unverified" either way, and a fixed-string grep over a
large tree is slow for an answer that decides nothing.

### D58. A `parent` field beside the `epic:` tag, not instead of it
D28 chose `epic:` as a tag so an epic needed no field and no body. On a
design-record backlog the epic is the thing with the body: the record,
whose pieces ship separately across sessions and agents. Five records
kept a table of pieces with commit hashes by hand, which is exactly what
`Skald-Story` trailers exist to make derived, and a tag cannot carry a
body, a question, a decision, or an audit date. So a story gains an
optional `parent`, a local id, and a child is an ordinary story with that
one field. The tag stays: it costs nothing, it works across repositories,
and most epics never need a body. The parent is local only, because
cross-project references already carry the `unavailable` problem and a
parent that may not be on this machine is worse than a tag that always
resolves. `format` stays at 1: unknown fields are preserved, so an older
tool reads a story with a parent and simply does not know what it means.
The board, the `epics` merge, and the union of children's commits are a
second story, once children exist in practice.

### D59. Children on the board are chips in the dialog and lanes, not nested cards
With a `parent` field the board had to show the family somewhere. Nesting
child cards inside the parent's card was rejected: a card is a drag
target and a column is a list, and a card that contains a list breaks
both, besides needing every column to know about every other. Instead a
parent card carries one number, children done over total, the dialog
lists the children as chips that open them and has a "+ child" button,
and "swimlanes by parent" gives a lane per parent when you want the
overview. That reuses the three things the board already had (a progress
bar, a chip, a lane) and leaves drag and columns untouched. The History
tab unions the children's commits for the same reason `commits` does on
the CLI: the hand-kept table of pieces and hashes is the thing this
replaces.

### D60. `import` is driven by a mapping file, and has no MCP tool
Backlogs differ in how they mark dates, priorities, and updates: bold
lines, blockquoted updates, a filename prefix for state. A tool that
guessed at those would guess wrong quietly, and a migration that is
wrong quietly is worse than a script. So every extraction is a rule in a
JSON mapping that lives beside the records, and the dry run shows what
each rule produced before anything is written. JSON because the standard
library reads it. The first corpus's mapping was measured over 184
records before the command was built, which is why it was built rather
than a script: the same mapping runs on the next bucket, and the next
adopter writes their own. There is no MCP tool: a migration is a set-up
step a person runs once from a shell, and the MCP surface is for the
operations agents perform at run time. Sources are removed in the same
operation as the stories are created so that one commit carries both and
git's rename detection keeps the record's history reachable from the
story.

Addendum, after the first real migration. The filing date comes from git
when no regex matches: only a third of that corpus carried a dated line,
and the commit that added a file is right more often than any pattern, so
`git-added` is the default and the regex is the override for records older
than their git history; `fallback: error` keeps the strict behaviour for
corpora where every record must carry a date. Links resolve against every
ancestor of the referencing file up to ROOT and against the project root,
because backlogs link bucket-relative and repository-relative as well as
sibling-relative, and the stories are always scanned however narrow ROOT
is, since that is where the moved bodies now live. The mapping is
validated whole before any file is read: a mapping mistake is the first
thing a new adopter hits, and it should read as a named rule, not a
traceback.

### D61. Model and cost are conventions over tags and authors, not fields
A user asked for stories to carry the model intended for the work, the
model that did it, and the tokens spent, to learn which shape of problem
suits which model. The intent is a planning fact, and the story format
already has a place for planning facts that filter and route: a facet tag,
the same shape as `epic:` and `lane:`. An effort level ages better than a
model name, since names change every quarter and what the planner means is
"this needs the expensive one". The actual is attribution, and every note
and claim already carries an author label, so `--as` with the model is the
record with no new field. Tokens stay out: Skald cannot observe them, only
the harness can, and a field another tool must fill in is stale the moment
someone forgets; a note of kind `cost` is available to a harness that
wants it. The one thing the core needed was `next --tag`, so a loop that
routes by tag asks for its next story in one call. The rest is an example,
kept in this repository under `examples/` because it is Markdown and a
script that must track the Skald version it was written against, and a
separate repository earns its existence only when something in it ships
on its own schedule.

### D62. The Python floor follows upstream support
Skald ran on 3.9 from the start because a standard-library-only package
costs nothing to keep there. Once 3.9 left upstream support the floor
moved to 3.10, and CI took on 3.14, on the reasoning that the people
running coding agents are on current interpreters and a floor below
upstream support tests a version no user has. The rule going forward:
when a version leaves upstream support, the next release drops it; when
a version ships, CI adds it. Nothing in the package depends on a feature
above 3.10, so the floor is a statement of what is tested, not a
constraint the code needs.

### D63. Fixes go to the latest release; an earlier line is patched from a branch cut at its tag, on demand
Skald is pre-1.0, has no dependencies, is one `pip install --upgrade`
away for every user, and has one maintainer. A fix costs the same
wherever it lands; maintaining older lines costs a branch, a matrix, and
a backport per fix for as long as the line lives. So the policy promises
what can be kept: the latest release receives fixes, and an earlier line
is patched only when a maintainer decides it must be. Release branches
are not created in advance because a tag on `main` is enough to cut one
the day it is needed, and the publish workflow keys on the tag, not the
branch. Two rules follow from what a release is: a published tag is the
identifier of what shipped, so it is never deleted or moved (the `v0.5.1`
move was allowed only because nothing had been published from it), and a
vulnerable release on PyPI is yanked rather than deleted, because
yanking hides it from resolvers while keeping existing pins and lockfiles
intact, and deleting breaks them and burns the number.
