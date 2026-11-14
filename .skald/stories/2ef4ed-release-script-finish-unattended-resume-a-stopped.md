---
title: "Release script: finish unattended, resume a stopped release, refuse when main is ahead of dev"
status: "review"
rank: 10
tags: ["area:release"]
blocked_by: []
assignee: "claude"
created_at: "2026-11-14T22:38:20Z"
updated_at: "2026-11-14T22:42:52Z"
---
## Requirements

Three releases in a row needed hand work after `scripts/release.sh`:

- **1.3.1** stopped at the pull request to `main`, when a test failed. It
  was finished by hand.
- **1.3.2**'s pull request conflicted on render commits that `main` had and
  `dev` lacked (73ea3b1, c2c236b).
- The latest release waited on a `y` after the checks passed. The person
  had walked away, so nothing shipped.

Changes:

- **Unattended after the preview.** The one confirmation left is the
  release notes preview at the start, while you are at the terminal
  (`--yes` skips that too). Once the checks pass, the script merges the
  pull request, tags, pushes the tag, merges `main` back into `dev`, and
  watches the publish run to the end. `--ask` restores the stop before the
  merge.
- **Refuse when `main` is ahead of `dev`.** A preflight check lists the
  commits `main` has that `dev` lacks, and the merge that fixes it, before
  anything changes.
- **Resume.** `scripts/release.sh X.Y.Z --resume` picks up a release that
  stopped partway, from whichever step it reached:
  - bumped but not pushed;
  - the pull request open (it reuses the open `dev` → `main` PR);
  - merged but not tagged;
  - tagged but `main` not merged back.
  Failure messages point at `--resume`, not at doing steps by hand.
- **Publish without a person.** The publish job's manual approval on the
  `pypi` environment is a repository setting; the owner turns it off. In
  its place, the publish workflow refuses a tag whose commit is not on
  `main`, so only code that went through the pull request and its checks
  can be uploaded. The test gate in publish stays.

## Acceptance
- [x] After the preview confirmation, a release runs to the end with no further input; `--ask` stops before the merge.
- [x] The preflight refuses, changing nothing, when `origin/main` has commits `origin/dev` lacks, and names them.
- [x] `--resume` continues from each stopping point: bumped, PR open, merged, tagged.
- [x] The script waits for the publish run and reports its result; it merges `main` back into `dev` first.
- [x] publish.yml refuses a tag that is not on `main`.
- [x] Tests for the new checks and the resume detection; docs/git-and-ci.md, CHANGELOG, DECISIONS updated.

## [claude] 2026-11-14 22:42 UTC · handoff
Done.
- scripts/release.sh: one confirmation at the preview (--yes skips it, --ask adds one before the merge).
- Preflight refuses while origin/main has commits HEAD lacks, listing them, with the fix.
- Stage detection for --resume, from the version file, origin/main's version and the tag on origin: pr, tag or back. It reuses an open dev -> main PR and waits for the PR head to reach the pushed commit before reading checks. It waits for main's skald.yml run (the render job) before tagging, pushes a matching local tag left by a stopped run, merges main back into dev, then watches the publish run with gh run watch --exit-status.
- shellcheck clean.
- publish.yml: fetch-depth 0, and a step that refuses a tag whose commit is not an ancestor of origin/main.
- Tests in tests/test_repo.py: the main-ahead refusal; resume detection at each stage; a full unattended run against a fake gh that merges dev into main on the local origin; --ask stopping before the merge, then --resume finishing.
- Owner action needed: in GitHub Settings -> Environments -> pypi, remove the required reviewers and limit deployments to v* tags.
