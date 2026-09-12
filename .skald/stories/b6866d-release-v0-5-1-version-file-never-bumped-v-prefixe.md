---
title: "Release v0.5.1: version file never bumped, v-prefixed heading blinded the guard"
status: "done"
rank: 20
tags: ["release"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-12T18:32:28Z"
updated_at: "2026-09-12T18:49:53Z"
---
## Requirements

The v0.5.1 tag went out with __version__ still 0.5.0; the publish job refused it, so nothing was uploaded. skald release had been run as 'release v0.5.1', so the changelog heading read '## v0.5.1' and the version guard, which only checked headings it could parse, passed silently.

- [x] __version__ is 0.5.1; the heading is '## 0.5.1'; the four archived stories say released 0.5.1
- [x] skald release strips a leading v from the version
- [x] the version guard fails on a release heading it cannot read
- [x] docs/git-and-ci.md states the real order: bump, release, merge, tag; CHANGELOG

## [claude] 2026-09-12 18:32 UTC · result
Corrected on the branch: __version__ 0.5.1, heading '## 0.5.1 (2026-09-12)', released: "0.5.1" in the four archived stories. release.plan strips a leading v (test: plan(s, 'v1.2.0').version == '1.2.0'). test_repo's guard now asserts the newest release heading reads '## X.Y.Z (YYYY-MM-DD)' and matches __version__, skipping only an Unreleased heading, instead of passing on anything it could not parse. docs/git-and-ci.md release flow: bump first, release, merge to main, tag vX.Y.Z; a mismatched tag fails before upload. CHANGELOG under 0.5.1 Fixed. Nothing was published: the publish job refused the tag.
