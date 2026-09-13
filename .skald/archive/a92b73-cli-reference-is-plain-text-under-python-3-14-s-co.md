---
title: "CLI reference is plain text under Python 3.14's coloured argparse"
status: "done"
rank: 100
tags: ["ci", "cli"]
blocked_by: []
assignee: "claude"
released: "0.6.0"
created_at: "2026-09-13T21:44:28Z"
updated_at: "2026-09-13T21:49:59Z"
---
## Requirements

## Problem

Python 3.14 colours argparse usage output when the stream is a TTY. `command_reference()` builds each command's `usage` from `parser.format_usage()`, so on 3.14 run from a terminal the reference carries ANSI SGR codes. `test_cli_reference_is_current` and `test_help_reference_matches_parser` then fail. CI did not catch it because its pipes are not TTYs, so `can_colorize()` returns false there; it only bit the maintainer's local release run.

## Fix

- [ ] Strip ANSI escape sequences from the usage string in `command_reference()`, the single place a formatter's output enters the reference, so docs/cli.md and /api/help are identical on every Python version and in or out of a terminal.
- [ ] Interactive `skald --help` keeps its colour; only the generated reference is normalised.
- [ ] Suite and `skald docs` clean; CHANGELOG under Unreleased.

## [agent] 2026-09-13 21:46 UTC · result
Root cause: Python 3.14 colours argparse usage output when the stream is a TTY (can_colorize checks the tty). command_reference builds each command's usage from parser.format_usage(), so a 3.14 run from a terminal carried SGR codes into docs/cli.md and /api/help; test_cli_reference_is_current and test_help_reference_matches_parser failed. CI's pipes are not TTYs so can_colorize returned false and it stayed green, which is why only the local release run saw it. Fix: a module-level _ANSI regex strips the escape sequences from the usage string in command_reference, the one place formatter output enters the reference. Interactive skald --help is untouched and keeps colour. Verified on 3.11-3.13 here and by monkeypatching format_usage to emit 3.14-style colour: command_reference and docs_markdown come back clean and both failing assertions pass. Suite (155) and ruff green; skald docs unchanged; CHANGELOG under Unreleased > Fixed.
