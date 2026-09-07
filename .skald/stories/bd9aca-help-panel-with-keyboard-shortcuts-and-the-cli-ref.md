---
title: "Help panel with keyboard shortcuts and the CLI reference"
status: "review"
rank: 340
tags: ["docs", "ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-07T01:29:56Z"
updated_at: "2026-09-07T01:37:51Z"
---
## Requirements

## Requirements

Add a Help panel to the board (header button and the ? key) so a person can look up reference information without leaving the page: keyboard shortcuts, the CLI command reference, and a short note on the story file format.

The CLI reference must be generated from the argparse parser via GET /api/help, not hand-copied into the page, so it cannot drift from the real commands.

## Acceptance
- [x] ? opens Help; Esc closes it
- [x] Shortcuts tab lists every board shortcut
- [x] CLI tab lists every subcommand with its help text and options, filterable
- [x] /api/help is covered by a test that checks it against build_parser()

## [claude] 2026-09-07 01:37 UTC · result
Help panel opens with ? or the header button: Shortcuts, CLI reference, Story files. The reference comes from GET /api/help, built by cli.command_reference() from the argparse tree (D42); a test asserts it matches build_parser(). The filter box narrows and expands matching commands.
