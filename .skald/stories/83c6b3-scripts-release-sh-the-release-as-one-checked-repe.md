---
title: "scripts/release.sh: the release as one checked, repeatable sequence with a dry run"
status: "review"
rank: 20
tags: ["release"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-12T18:46:20Z"
updated_at: "2026-09-12T18:47:03Z"
---
## Requirements

The 0.5.1 release went wrong by hand: a bump that never landed and a v in the version. The sequence is now a script.

- [x] scripts/release.sh X.Y.Z [--dry-run] [--yes]: checks (dev, clean, in step with origin, version shape and ordering, tag free, skald and gh present), release preview, bump + skald release + bump commit + tests, push dev, PR dev to main with checks watched and merged, tag main, merge main back into dev; SKALD and GH overridable
- [x] tests in a fixture repository with a bare origin and a stub gh: the dry run passes every check and changes nothing; each check refuses the wrong state
- [x] docs/git-and-ci.md release flow describes the script and what it does; CONTRIBUTING, README, CHANGELOG

## [claude] 2026-09-12 18:47 UTC · result
scripts/release.sh (bash, set -euo pipefail): checks version shape (refuses a leading v with the corrected form), newer than __version__ by sort -V, on dev, clean, HEAD == origin/dev after a fetch, tag free locally and on origin, skald and a logged-in gh on PATH (both overridable via SKALD and GH); prints skald release --dry-run; --dry-run stops there. Otherwise: sed the version file (with a .bak for macOS, verified), skald release, commit the bump, python -m unittest, push dev, gh pr create dev->main, gh pr checks --watch --fail-fast, confirm, gh pr merge --merge, checkout main, verify main's version file equals the version before tagging, tag -a, push tag, print the publish workflow URL, merge main back into dev, push. Tests (skipped on Windows) build a bare origin with main and dev, a stub gh, and a skald launcher on this interpreter; the dry run passes every check and leaves HEAD, the tree, and the version file untouched; six wrong states each get their message. Docs: git-and-ci.md release flow, CONTRIBUTING, README, CHANGELOG.
