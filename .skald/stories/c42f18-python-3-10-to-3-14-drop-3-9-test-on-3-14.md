---
title: "Python 3.10 to 3.14: drop 3.9, test on 3.14"
status: "review"
rank: 10
tags: ["ci"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-12T19:12:34Z"
updated_at: "2026-09-12T19:15:01Z"
---
## Requirements

Python 3.9 has been end of life since October 2025 and 3.14 has been out as long. People running coding agents are on current interpreters.

- [x] requires-python >= 3.10; ruff target py310; classifiers name 3.10 to 3.14
- [x] test.yml runs 3.10 to 3.14 on Linux, 3.12 on macOS and Windows
- [x] README, getting started, CONTRIBUTING, SPEC goal 2 and the CI paragraph, CLAUDE.md, git-and-ci.md say 3.10 or newer; CHANGELOG; a DECISIONS entry

## [claude] 2026-09-12 19:15 UTC · result
requires-python >=3.10, ruff target py310, classifiers 3.10 to 3.14; test.yml matrix 3.10 to 3.14 on Linux with 3.12 on macOS and Windows; README, getting started, CONTRIBUTING, SPEC goal 2 and CI paragraph, CLAUDE.md, git-and-ci.md; CHANGELOG under Unreleased; D62 states the rule (drop a version when upstream does, add one when it ships). The py310 target surfaced one bugbear finding, zip without strict in gitutil, fixed with strict=True since both lists come from the same paths. Suite green on 3.10 through 3.13 here; 3.14 is CI's to confirm.
