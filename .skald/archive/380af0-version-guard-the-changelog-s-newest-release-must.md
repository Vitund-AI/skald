---
title: "Version guard: the changelog's newest release must match __version__"
status: "done"
rank: 20
tags: ["packaging"]
blocked_by: []
assignee: "claude"
released: "0.4.0"
created_at: "2026-09-10T18:21:55Z"
updated_at: "2026-09-10T20:18:46Z"
---
## Requirements

0.3.0 was released without bumping src/skald/__init__.py, so skald --version reported 0.2.0 for a 0.3.0 install. release deliberately never edits version files (D46), so a test now pins the rule: when the first ## heading of CHANGELOG.md is a version, it must equal __version__. Bumped to 0.3.0. From the 0.3.0 adoption review (finding 2).

## Changelog

The package version is 0.3.0, and a test now fails when the newest release heading in the changelog does not match the version in the package.

## Acceptance
- [x] __version__ is 0.3.0
- [x] test_repo checks the newest changelog release heading against __version__ (Unreleased is skipped)

## [claude] 2026-09-10 18:26 UTC · result
__version__ is 0.3.0; test_repo checks the newest changelog release heading against it, skipping Unreleased.
