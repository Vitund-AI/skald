---
title: "Refuse a release when stories tagged for the version are not done, gated by config, with --allow-incomplete to override"
status: "review"
rank: 10
tags: ["area:release"]
blocked_by: []
assignee: "agent"
created_at: "2026-09-17T04:57:46Z"
updated_at: "2026-09-17T05:03:43Z"
---
## Requirements

The release: facet already warns about stories tagged for the version that are not done. Turn that into an enforceable gate:

- New project config.json key block_release_on_incomplete (boolean, default false, validated). When true, skald release <v> refuses (errors, changes nothing) if any story tagged release:<v> (matching the version) is not in a terminal column.
- --allow-incomplete flag on skald release overrides the gate.
- The refusal applies to --dry-run too, so scripts/release.sh stops early before the version bump; release.sh gains a forwarded --allow-incomplete.
- Reuse the exact set the existing warning names (plan.blocking). Default off preserves current warn-only behaviour.

Docs: SPEC, git-and-ci.md, conventions.md, cli.md regen, DECISIONS. Standard library only.
