---
title: "1.0 compatibility promise: declare the stable surface, pin the --json fields, add skald migrate"
status: "done"
rank: 30
tags: ["area:release", "release:1.0.0", "roadmap"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-20T00:58:52Z"
updated_at: "2026-10-05T21:42:50Z"
---
## Requirements

1.0 is a semver promise: nothing public breaks until 2.0. Today Skald never
says what "public" is, and docs/working-with-agents.md already claims
"`--json` output is stable" without defining it. Write the promise down and
make CI hold it.

**Stable for 1.x (additive changes only):**
- The story file format and `config.json` (`format: 1`, config.py's forward
  guard already refuses a newer format). Any format bump ships an automatic,
  lossless, idempotent `skald migrate` in the same release.
- CLI command names and flags; exit codes; the field sets of `--json`
  output (`ls`, `show`, `next`, `context`, `resume`, `status`, `export`, ...).
- MCP tool names and their arguments.
- The `AGENTS.md` contract's commands and rules.
- The HTTP API's **data plane** (Q1, revised 2026-10-05): bearer auth and
  the Host check, the error format, `GET /api/health`, `/api/projects`,
  `/api/ready`, `/version`, `/events`, and the story routes. docs/api.md
  marks the planes and tests/test_api_docs.py pins the route set.

**Not covered:** human-readable (non-`--json`) output, the rendered
`.skald/README.md` layout, the board's look, the Python modules (an
example that imports `skald.*` relies on internals), and the HTTP API's
**board backend** (the routes shaped for the board's screen), which is
documented in docs/api.md but may change in any release.

**Deprecation rule:** nothing is removed in 1.x. A deprecated flag, field,
or tool keeps working and warns for at least one minor release; removal
waits for 2.0 and is listed in its changelog.

## Change

- A "Compatibility" section in SPEC.md (the authoritative list above), a
  short pointer from README and docs/working-with-agents.md, a DECISIONS
  entry.
- A contract test that pins the field set of each stable `--json` output
  and each MCP tool schema: adding a field passes, removing or renaming one
  fails with a message pointing at the compatibility section.
- `skald migrate`: at format 1 it validates and reports "already at the
  current format" (exit 0); `--check` for CI. The entry point exists before
  format 2 needs it.

## Acceptance
- [x] SPEC.md Compatibility section: stable surface, exclusions, deprecation rule, migrate promise
- [x] README + working-with-agents.md point at it; "--json is stable" now links to the defined list
- [x] contract test pins --json field sets and MCP tool schemas (removal/rename fails, addition passes)
- [x] skald migrate (no-op at format 1) with --check, documented, tested
- [x] contract test also pins the response fields of the HTTP data-plane routes (the route set itself is pinned by tests/test_api_docs.py)
- [x] DECISIONS entry; CHANGELOG
- [x] python3 -m unittest green, ruff clean, skald docs --check

## Changelog

Skald now states what 1.x keeps stable: the story and config format, CLI
commands and flags, the fields of `--json` output, MCP tools, and the agent
contract. CI pins them, so a breaking change cannot ship by accident. A new
`skald migrate` command is the upgrade path for any future format change;
today it confirms the backlog is current.

## [claude] 2026-10-04 02:42 UTC · question
Q1: Is the board's HTTP API part of the 1.x stability promise, or documented but internal to the board? The maintainer wants it documented either way (c9e05f). Stable means scripts written against /api can rely on it until 2.0, but every board feature that needs a new response shape becomes additive-only. Internal keeps the board free to evolve, and scripts are pointed at the CLI's --json and MCP instead. Leaning internal unless someone is already scripting against it.

## [claude] 2026-10-04 16:52 UTC · decision
Answers Q1 [claude] 2026-10-04 02:42 UTC · Q1: Is the board's HTTP API part of the 1.x stability promise, or documented but internal to the board? The maintainer wants it documented either way (c9e05f). Stable means scripts written against /api can rely on it until 2.0, but every board feature that needs a new response shape becomes additive-only. Internal keeps the board free to evolve, and scripts are pointed at the CLI's --json and MCP instead. Leaning internal unless someone is already scripting against it.
Maintainer's decision (2026-10-04): the HTTP API stays internal to the board for 1.x and is not part of the stability promise; revisit after 1.0. It is still documented in full in docs/api.md for our own reference (c9e05f), with a note at the top saying it is internal and may change in any release. Scripts should use the CLI's --json output or MCP, which are covered.

## [claude] 2026-10-05 01:28 UTC · decision
Q1 revised with the maintainer (2026-10-05), superseding the 2026-10-04 answer: the HTTP API splits into a data plane and a board backend (BFF). The data plane is stable for 1.x on the same terms as --json and MCP: auth (bearer token, Host check), the error format, GET /api/health, /api/projects, /api/ready, /version, /events, and the story routes (create, read, patch, delete, body, notes, claim). Its story object is the same story_dict that --json and MCP return, so pinning it costs nothing new. The board backend (/board, /branches, /checkouts, settings, /update, /help, /git, git/commit, /history, /templates, /releases, /archive, the session cookie, the page and assets, and the ?ref=/?checkout= parameters) stays internal and may change in any release. Promotion BFF -> data plane is allowed in any 1.x minor; nothing is demoted before 2.0. Why: Skald already invited scripting against the server (the board's token dialog, docs/board.md, skald server token), the server offers what CLI and MCP cannot (a live change stream, one long-running endpoint across projects), and the routes that mirror CLI operations cost almost nothing extra to keep stable.

## [claude] 2026-10-05 19:12 UTC · handoff
Done. SPEC 10d Compatibility (1.x): stable = data format at format 1, CLI commands/flags/exit codes and every --json + export field set, MCP tools and arguments (no new required args), the HTTP data plane (D77), the AGENTS contract; not covered = text output, rendered snapshot, board look, HTTP board backend, *(internal)* fields, Python modules; deprecation = keep + warn for >=1 minor, remove only in 2.0; format changes ship a skald migrate step. New src/skald/migrate.py + skald migrate [--check] [--json]: STEPS registry (empty at format 1), runs under the mutation lock, rewrites format after each step; --check exits 1 when needed (matches docs --check). tests/test_contract.py + tests/contract.json: fixture covering every optional field, runs all 22 --json commands, export and the 11 data-plane routes with bodies (+ the events hello), reduces to field paths with data-keyed maps collapsed, pins every command's flags and every MCP tool's arguments/required; command and MCP checks need no fixture. Mutation-checked: dropping story 'stale', making an MCP arg required, removing ls --compact each fail with a named message. Update with SKALD_CONTRACT_UPDATE=1. Also: SPEC format bullet, command table, module list; README + working-with-agents links; troubleshooting entry; DECISIONS D78; CHANGELOG. unittest OK (220), ruff clean, docs --check.
