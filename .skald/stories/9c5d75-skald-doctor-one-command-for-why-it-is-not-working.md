---
title: "skald doctor: one command for why it is not working"
status: "idea"
rank: 30
tags: ["roadmap"]
blocked_by: []
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-12T20:39:49Z"
---
## Requirements

Checks and reports, one line each, with the fix: git on PATH and a repository around; `.skald/` found and readable; the registry's paths exist (or which are gone); the server state file agrees with a live process and the token file is private; Claude Code hooks installed and the SessionStart command's --as author; the contract copy current with the template; Python version. Exit 1 if anything is red.

## Why

Every adopter's first hour hits one of these, and docs/troubleshooting.md is a list of them. The checks are all reads of state Skald already owns.
