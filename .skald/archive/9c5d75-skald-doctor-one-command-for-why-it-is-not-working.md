---
title: "skald doctor: one command for why it is not working"
status: "done"
rank: 90
tags: ["roadmap"]
blocked_by: []
assignee: "claude"
released: "0.7.0"
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-14T15:24:52Z"
---
## Requirements

`skald doctor` checks the environment and the wiring, one line each with the
fix to run, and exits 1 if anything is red. It is read-only: it prints the
fix command, it does not apply it. `--json` for machine reads.

Scope is the environment, not the backlog data: `check` already validates the
story files (corrupt frontmatter, ids, dates, duplicate ids, dangling and
cross-project dependencies, conflict markers, a stale rendered file). `doctor`
owns what `check` cannot, much of it before a story even loads, and ends by
running `check` and folding its result into one exit code.

- [ ] Prerequisites: Python at or above the floor; `git` on PATH and a repo around `.skald/`; `git config user.name`/`user.email` set (commits, `release`, and hooks fail without them).
- [ ] Project config: `config.json` parses as JSON and passes schema validation (roles present, at least one terminal column, unique keys); its `format` is not newer than this skald; `.skald/` and the stories dir exist and are writable.
- [ ] Registry: each registered project's `.skald` path still exists and is readable (name the gone ones with `skald projects rm`); no two entries share a name or a path; the current directory is a registered project.
- [ ] Server: `server.json` names a live process (not stale after a crash or reboot); a running server's version is not older than the installed package; the token file exists and is not world-readable.
- [ ] Agent wiring: Claude Code SessionStart/Stop hooks installed and their command resolves to a skald that exists, with an `--as <author>` set; the pre-commit hook is skald's and not overwritten; `.skald/AGENTS.md` and `.claude/skills/skald/SKILL.md` match the current template.
- [ ] Context, always shown: the effective `SKALD_HOME`/`SKALD_DIR` and the resolved author identity, so a surprising override is visible even when nothing is red.
- [ ] Ends by running `check`; one exit code covers setup and data. Documented in troubleshooting.md; a `--fix` for the safe subset (delete a stale `server.json`, chmod the token, re-copy the contract, render) is a possible follow-up, not required here.

## Why

Every adopter's first hour hits one of these, and `docs/troubleshooting.md`
is a list of them. The checks are all reads of state Skald already owns, and
a bad `config.json` is the case nothing else can catch, because the store
never opens to run `check`.

## [agent] 2026-09-14 05:35 UTC · result
New src/skald/doctor.py + skald doctor command, dispatched before the store opens so it runs even when config.json is broken. Checks (read-only, one line each with the fix, --json): Python floor; git on PATH, a repo, and user.name/user.email set; config.json parses and validates via ProjectConfig.load (the case check can't reach); stories dir present and writable; registry paths (gone entries, duplicate paths, current dir registered); server (stale server.json via pid_alive, a version behind the package via health, a world-readable token); Claude Code hooks present with --as and the AGENTS.md/SKILL.md contract copies against the template; plus an info line for SKALD_HOME/DIR/AUTHOR. Ends by folding skald check into one exit code (1 on any FAIL). gitutil gained user_email. Verified manually (healthy vs broken config vs missing identity) and with tests/test_doctor.py (6 cases). SPEC command table, docs/troubleshooting.md, CHANGELOG Unreleased, docs/cli.md regenerated. Suite 167 green, ruff clean.
