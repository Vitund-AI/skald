---
title: "skald hooks git --install: register the merge driver even beside a foreign pre-commit hook, and write commands that run"
status: "done"
rank: 20
tags: ["area:git", "bug"]
blocked_by: []
assignee: "claude"
created_at: "2026-11-09T18:11:02Z"
updated_at: "2026-11-09T18:42:51Z"
---
## Requirements

Two gaps in `skald hooks git --install`, found while answering "how does a user register the merge driver after upgrading to 1.3":
- When the repository already has a pre-commit hook that is not Skald's, the installer refuses to overwrite it and stops before it registers the story merge driver, so those users get no driver unless they set it up by hand.
- The driver (and the pre-commit hook) run `skald`, which is not on PATH for a user who runs Skald through `uvx` or a virtualenv that is not active; git then falls back to a line merge, and the hook blocks every commit with "skald: not found".

## Acceptance
- [x] The merge driver and `.gitattributes` are set up even when an existing pre-commit hook is left alone; the installer says what it did and what to add to the hook, and still exits 1 for the hook part.
- [x] When `skald` is not on PATH, the driver and hook call the interpreter that ran the installer (`"<python>" -m skald`), and the installer says so.
- [x] `skald doctor` warns when the registered driver's command cannot be found.
- [x] Docs and CHANGELOG updated.

## [claude] 2026-11-09 18:14 UTC · handoff
Done.
- cli:
  - `skald_command()` returns `skald` when `shutil.which` finds it, else `"<sys.executable posix>" -m skald`;
  - `pre_commit_hook(skald)` and `merge_driver(skald)` template both;
  - `cmd_hooks_git` writes the hook unless a foreign one exists, then always installs the driver; the `.gitattributes` render line is added only when rendering is on (it was a crash risk with a foreign hook and no render setting);
  - it notes on stderr when it falls back to the interpreter, and exits 1 with the lines to add when the hook is foreign.
- doctor: `_runnable` checks the driver's program is on PATH or a file; WARN otherwise.
- Docs: git-and-ci.md Conflicts, SPEC 4.8, CHANGELOG.

Verified:
- 3 new tests in test_merge.py: a foreign hook is left untouched, with the driver and attributes set and exit 1; no skald on PATH puts the interpreter in the driver and the hook; doctor goes OK, then WARN for a missing program;
- the full suite, ruff and docs --check pass.
