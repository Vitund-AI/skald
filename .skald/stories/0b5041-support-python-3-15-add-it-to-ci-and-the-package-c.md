---
title: "Support Python 3.15: add it to CI and the package classifiers"
status: "review"
rank: 10
tags: ["area:ci"]
blocked_by: []
assignee: "claude"
created_at: "2026-10-09T20:15:22Z"
updated_at: "2026-10-09T20:25:39Z"
---
## Requirements

Python 3.15.0 was released. Per D62 (CI adds a version when it ships), add it to the unittest matrix and the classifiers, and update the version range in SPEC, CONTRIBUTING, and docs/git-and-ci.md. No release needed.

## [claude] 2026-10-09 20:15 UTC · handoff
Done. 3.15 added to the test matrix, with allow-prereleases until setup-python lists the final 3.15.0, which falls back to rc.3 today. The classifier and the version ranges in SPEC, CONTRIBUTING and git-and-ci.md are updated, and SPEC's stale 'no tag has been cut yet' is removed. Verified locally on CPython 3.15.0 via uv: 235 tests pass, with no deprecation warnings.

## [claude] 2026-10-09 20:25 UTC · decision
Python support policy revised with the user. requires-python is exactly what CI tests. A version past upstream support is tested, not promised: it stays while free and goes in any minor release. Prefer a small version gate over dropping a version. Drop it when a gate won't do, when the LTS distros that ship it leave support, or promptly when an unfixed interpreter security defect affects Skald. Recorded as a D62 addendum, in the SPEC principle and the 10d Python versions paragraph, in SECURITY.md and in the CHANGELOG.
