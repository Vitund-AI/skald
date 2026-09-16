---
title: "release.sh tags the merge commit, not a [skip ci] render HEAD"
status: "done"
rank: 20
tags: ["area:release"]
blocked_by: []
assignee: "claude"
released: "0.8.0"
created_at: "2026-09-14T16:54:50Z"
updated_at: "2026-09-16T07:11:46Z"
---
## Requirements

The v0.7.0 publish workflow never ran: the tag landed on main's HEAD, which
was the skald render job's `skald: refresh rendered board [skip ci]` commit,
and GitHub skips every workflow — a tag push included — when the head commit
message carries a skip instruction.

## Changelog

`scripts/release.sh` now tags the newest non-skip ancestor of main (the merge
commit, which carries the version bump) instead of HEAD, so the tag push
always triggers publish. It verifies that commit's version file still reads
the release version before tagging.

## Acceptance
- [x] step 5 walks back over [skip ci] commits (and GitHub's other documented
      skip strings) to the merge commit
- [x] version-file guard on the chosen commit
- [x] docs/git-and-ci.md and DECISIONS.md (D65) updated
- [x] tests green, ruff clean
