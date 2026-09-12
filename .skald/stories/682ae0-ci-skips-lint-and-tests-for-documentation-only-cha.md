---
title: "CI skips lint and tests for documentation-only changes, without leaving required checks pending"
status: "review"
rank: 30
tags: ["ci"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-12T19:58:10Z"
updated_at: "2026-09-12T19:59:19Z"
---
## Requirements

A change to the README, the guides, the policies, or the images should not run the seven-platform matrix. A path filter on the workflow would leave any required check 'expected' and block a protected branch, so the skip is a job condition instead: skipped jobs report as skipped and satisfy the requirement.

- [x] scripts/docs_only.py: reads changed paths, prints true when every one is documentation the tests never read (README, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SPEC, DECISIONS, LICENSE, docs/ except docs/cli.md); CHANGELOG.md, docs/cli.md, .skald/, the contract template, and everything else count as code
- [x] test.yml: a changes job diffs against the pull request base (or the previous push) and the lint and unittest jobs run only when the change is not documentation-only; a new branch or an unknown base runs everything
- [x] tests for the classifier; docs/git-and-ci.md Checks section; CHANGELOG

## [claude] 2026-09-12 19:59 UTC · result
scripts/docs_only.py classifies changed paths (README, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SPEC, DECISIONS, LICENSE, docs/ except docs/cli.md are documentation; CHANGELOG.md, docs/cli.md, .skald/, the contract template, and everything else are code; an empty list is not documentation-only). test.yml: a changes job with full history diffs from the merge base of the PR base (or the previous push) to HEAD and pipes the list to the script; an unusable base runs everything; lint and unittest carry needs: changes and if docs_only != true, so on a documentation-only change they report skipped, which satisfies a required check where a path-filtered workflow would leave it expected. Tests cover the classifier both ways. git-and-ci.md Checks section, CHANGELOG, ruff now also checks scripts.
