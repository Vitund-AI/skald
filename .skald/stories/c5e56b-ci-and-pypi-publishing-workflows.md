---
title: "CI and PyPI publishing workflows"
status: "review"
rank: 170
tags: ["packaging"]
blocked_by: []
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-06T07:04:42Z"
---
## Requirements

GitHub Actions: unittest on 3.9-3.13 Linux plus macOS and Windows 3.12, wheel build; publish.yml uses trusted publishing on v* tags and checks the tag matches __version__.

## [claude] 2026-09-06 07:04 UTC
Implemented. One-time human step: add the pending publisher on pypi.org for this repo, workflow publish.yml, environment pypi.
