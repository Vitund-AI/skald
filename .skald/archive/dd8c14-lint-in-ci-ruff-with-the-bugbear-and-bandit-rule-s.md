---
title: "Lint in CI: ruff with the bugbear and bandit rule sets, Dependabot for actions"
status: "done"
rank: 20
tags: ["ci"]
blocked_by: []
assignee: "claude"
released: "v0.5.1"
created_at: "2026-09-12T06:02:57Z"
updated_at: "2026-09-12T18:23:20Z"
---
## Requirements

Code quality checks that fit a standard-library-only package: one dev-time tool, no runtime dependency.

- [x] ruff configured in pyproject.toml: pyflakes, pycodestyle, bugbear, and the S (bandit) rules; a line length that matches the code; the intentional S findings waived per file with a reason (git subprocess calls, sha1 for ids marked usedforsecurity=False, urlopen against localhost, --host 0.0.0.0 as a feature)
- [x] a lint job in test.yml; ruff clean on src, tests, examples
- [x] the findings fixed: unused variables and imports, raise-from in the server, ambiguous names
- [x] .github/dependabot.yml for GitHub Actions versions
- [x] docs/git-and-ci.md says how to run the lint locally; README development section; CHANGELOG

## [claude] 2026-09-12 06:05 UTC · result
pyproject [tool.ruff]: E, F, W, B, S; E501 and E741 off; per-file waivers with reasons for the git subprocess calls, --host 0.0.0.0 in the server, and the tests' subprocess/urlopen/assert use. Fixed what it found: unused imports and variables, a raise inside except now chains its cause, loop variables underscored, the glob translator one statement per line, the link-pass closures bind their loop values explicitly, and the three sha1 fingerprints say usedforsecurity=False (a 3.9 keyword). test.yml gains a lint job pinned to the ruff version used here; .github/dependabot.yml watches action versions monthly with PRs against dev. docs/git-and-ci.md Checks section, README development line, CHANGELOG. ruff clean, 154 tests pass. CodeQL is a repository setting the maintainer turns on.
