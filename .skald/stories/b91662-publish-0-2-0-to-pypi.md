---
title: "Publish to PyPI"
status: "ready"
rank: 10
tags: ["packaging"]
blocked_by: []
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-10T18:04:32Z"
---
## Requirements

Human steps: create the pending trusted publisher on pypi.org (repository Vitund-AI/skald, workflow publish.yml, environment pypi), create the pypi environment in GitHub settings, then tag v0.2.0 (or current version) and push the tag. The workflow refuses if the tag does not match __version__.

## [claude] 2026-09-08 01:16 UTC
Deferred by the maintainer until Skald has seen more real backlogs. Installs come from GitHub meanwhile; see story 1b15cc and INSTALL_SPEC in cli.py for the one-line switch back.
