---
title: "1.0 compatibility promise: declare the stable surface, pin the --json fields, add skald migrate"
status: "ready"
rank: 10
tags: ["area:release", "release:1.0.0", "roadmap"]
blocked_by: []
created_at: "2026-09-20T00:58:52Z"
updated_at: "2026-10-04T02:42:12Z"
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
- The HTTP API, if Q1 decides so (see notes). Documenting every route is
  c9e05f either way.

**Not covered:** human-readable (non-`--json`) output, the rendered
`.skald/README.md` layout, the board's look, and the Python modules (an
example that imports `skald.*` relies on internals).

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
- [ ] SPEC.md Compatibility section: stable surface, exclusions, deprecation rule, migrate promise
- [ ] README + working-with-agents.md point at it; "--json is stable" now links to the defined list
- [ ] contract test pins --json field sets and MCP tool schemas (removal/rename fails, addition passes)
- [ ] skald migrate (no-op at format 1) with --check, documented, tested
- [ ] HTTP API status recorded per Q1
- [ ] DECISIONS entry; CHANGELOG
- [ ] python3 -m unittest green, ruff clean, skald docs --check

## Changelog

Skald now states what 1.x keeps stable: the story and config format, CLI
commands and flags, the fields of `--json` output, MCP tools, and the agent
contract. CI pins them, so a breaking change cannot ship by accident. A new
`skald migrate` command is the upgrade path for any future format change;
today it confirms the backlog is current.

## [claude] 2026-10-04 02:42 UTC · question
Q1: Is the board's HTTP API part of the 1.x stability promise, or documented but internal to the board? The maintainer wants it documented either way (c9e05f). Stable means scripts written against /api can rely on it until 2.0, but every board feature that needs a new response shape becomes additive-only. Internal keeps the board free to evolve, and scripts are pointed at the CLI's --json and MCP instead. Leaning internal unless someone is already scripting against it.
