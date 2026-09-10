---
title: "Publish a pre-commit hook recipe that runs skald check"
status: "done"
rank: 70
tags: ["docs"]
blocked_by: []
created_at: "2026-09-06T02:16:15Z"
updated_at: "2026-09-08T17:24:16Z"
---
## Requirements

Document a one-line pre-commit hook and a GitHub Actions step that run `python3 .skald/skald.py check` so corrupt story files and dangling blockers never land on main.

## Changelog

A pre-commit hook and a GitHub Actions step run `skald check`, so corrupt story files and dangling blockers never land on the main branch.

## [claude] 2026-09-06 07:04 UTC
Done in README.md: a pre-commit recipe (exec skald check) and the CI note. skald hooks claude also installs a Stop hook for agents.
