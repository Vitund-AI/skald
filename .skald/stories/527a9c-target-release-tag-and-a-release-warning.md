---
title: "Target-release tag and a release warning"
status: "done"
rank: 10
tags: ["roadmap"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-13T22:38:49Z"
---
## Requirements

A `release:0.6` facet on stories marks what a release should carry. `skald release 0.6.0 --dry-run` (and the real run) warns about stories tagged for that release that are not in done, and the board filters on the facet like any other. No new field.

## Why

Planning a release is a filter on the board and a check at the end. The facet machinery (epic:, lane:) already does the filtering; only the warning in release.plan is new. Document beside the other conventions.

## [agent] 2026-09-13 22:38 UTC · result
release.plan() now warns about every non-terminal story whose release:<v> facet targets the version. release_matches(tag_value, version) is true on an exact match or a dotted prefix either way, so release:0.6 covers 0.6.x and matches the 0.6.0 run; release:0.7 and release:0.60 do not. Done stories ship and closed ones are a deliberate drop, so neither warns. The warning rides the existing _warn(plan.warnings) path, so both the dry run and the real run print it, and scripts/release.sh surfaces it. No new field and no board code: facets are already generic, so release: gets a filter and swimlanes like any other key. Docs: SPEC 4.5b, docs/stories.md Releases, the AGENTS contract (copied to .skald/AGENTS.md and .claude/skills/skald/SKILL.md), CHANGELOG under a new Unreleased. New test in test_release covers the warning both ways and the matcher; suite 156 green, ruff clean.
