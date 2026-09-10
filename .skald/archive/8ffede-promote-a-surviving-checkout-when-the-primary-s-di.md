---
title: "Promote a surviving checkout when the primary's directory has gone"
status: "done"
rank: 380
tags: ["core"]
blocked_by: []
assignee: "claude"
released: "0.2.0"
created_at: "2026-09-10T00:45:44Z"
updated_at: "2026-09-10T00:56:31Z"
---
## Requirements

When a project's primary directory disappears but another checkout survives (a recorded clone, or a worktree of a repository whose main checkout was deleted), the registry today heals only when a command runs inside the survivor. It should heal on any listing: skald projects, the board's project list, or -p NAME from anywhere promote the survivor on the spot with a moved-from notice. A project with no surviving checkout stays listed as missing, because an unmounted drive looks the same as a deletion; skald projects rm forgets it.

## Changelog

When a project's primary directory has gone and another checkout of it survives, the survivor is promoted the next time anything lists or opens the project, with a notice, instead of waiting for a command to run inside it. A project with no surviving checkout stays listed as missing.

## Acceptance
- [x] Registry.checkouts promotes a surviving checkout when the primary is missing and records a notice
- [x] Workspace.open and skald projects pick up the promotion; -p NAME works from anywhere afterwards
- [x] A project with no surviving checkout stays listed as missing
- [x] Docs: multi-project, troubleshooting, SPEC 2.4, CHANGELOG

## [claude] 2026-09-10 00:47 UTC · result
Registry.checkouts promotes the first surviving recorded checkout when the primary's stories dir is missing and records a notice; Workspace.open triggers it when the registered path is missing and surfaces the notice; skald projects prints it. No survivor: the project stays listed as missing. Tests cover the registry, a stale in-memory registry opening by name, the CLI listing, and -p from elsewhere afterwards. Docs: multi-project, troubleshooting, SPEC 2.4, CHANGELOG.
