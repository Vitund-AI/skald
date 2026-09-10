---
title: "Remove the 0.1 migration path and its mentions"
status: "review"
rank: 30
tags: ["cli", "docs"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T04:47:43Z"
updated_at: "2026-09-10T04:48:17Z"
---
## Requirements

Nobody ever ran 0.1 outside this repository, so the init migration (deleting a vendored .skald/skald.py and the git alias), the upgrade sections in the docs, and the 0.1 references in SPEC and CHANGELOG are clutter for every reader.

## Changelog

The migration from the unreleased 0.1 single-file layout is gone from init and the docs; 0.2.0 is the first release anyone installed.

## Acceptance
- [x] init no longer looks for skald.py or the old alias; the unused git helpers are gone
- [x] Tests updated; the subdirectory init test stays
- [x] getting-started, troubleshooting, SPEC, CHANGELOG cleaned; DECISIONS entry

## [claude] 2026-09-10 04:48 UTC · result
init no longer deletes skald.py or the alias; get_alias/unset_alias removed from gitutil as unused; subdirectory init test kept without the migration assertions; test_repo's legacy-layout test dropped. getting-started and troubleshooting upgrade sections removed; SPEC preamble and 2.4 trimmed; CHANGELOG 0.2.0 preamble now says first release, Removed subsection and 0.1.0 entry gone, Unreleased Removed entry added; D52. 128 tests pass.
