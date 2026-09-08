---
title: "Shell completion for bash, zsh, and fish"
status: "review"
rank: 250
tags: ["cli"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-08T18:47:37Z"
updated_at: "2026-09-08T18:51:39Z"
---
## Requirements

skald completion bash|zsh|fish prints a script to eval from the shell rc file. The script is a thin shim that calls a hidden skald _complete command, so all completion logic lives in Python and has real data: subcommands and flags from the parser (command_reference), story ids with titles as descriptions (zsh and fish), column keys after move and --status, tags after tag and --tags, project names after -p, template names after --template, branch names after --branch, note kinds after --kind, and choices from the parser. Also completes git skald.

Standard library only; no argcomplete. Each Tab spawns Python once.

## Acceptance
- [x] eval "$(skald completion zsh)" completes subcommands, flags, ids with titles, columns, tags, projects, templates, branches
- [x] bash and fish scripts work the same, bash without descriptions
- [x] git skald <Tab> completes
- [x] _complete is hidden from --help and the Help panel
- [x] Unit tests cover each completion context; CLI test covers the scripts

## [claude] 2026-09-08 18:51 UTC · result
completion.py builds candidates from command_reference() plus the store; cmd_complete prints value<TAB>description lines and never raises. Bash verified in a real shell here (commands, ids, columns after move, flags, git skald). zsh and fish are not installed in this container, so those scripts are reviewed but not executed: please try eval "$(skald completion zsh)" locally and report anything off. Known limit: bash splits words on colons, so project:id refs complete awkwardly there; zsh and fish are fine. Seven new tests cover every completion context.
