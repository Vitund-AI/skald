---
title: "Support Python 3.15: add it to CI and the package classifiers"
status: "review"
rank: 10
tags: ["area:ci"]
blocked_by: []
assignee: "claude"
created_at: "2026-10-09T20:15:22Z"
updated_at: "2026-10-09T20:15:22Z"
---
## Requirements

Python 3.15.0 was released. Per D62 (CI adds a version when it ships), add it to the unittest matrix and the classifiers, and update the version range in SPEC, CONTRIBUTING, and docs/git-and-ci.md. No release needed.

## [claude] 2026-10-09 20:15 UTC · handoff
Done. 3.15 added to the test matrix, with allow-prereleases until setup-python lists the final 3.15.0, which falls back to rc.3 today. The classifier and the version ranges in SPEC, CONTRIBUTING and git-and-ci.md are updated, and SPEC's stale 'no tag has been cut yet' is removed. Verified locally on CPython 3.15.0 via uv: 235 tests pass, with no deprecation warnings.
