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
`check` reports them. Only `mv` and `new` reject a status that is not a
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
