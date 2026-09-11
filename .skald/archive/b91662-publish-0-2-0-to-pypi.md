---
title: "Publish to PyPI"
status: "done"
rank: 20
tags: ["packaging"]
blocked_by: []
assignee: "claude"
released: "0.4.1"
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-11T04:56:41Z"
---
## Requirements

Human steps: create the pending trusted publisher on pypi.org (repository Vitund-AI/skald, workflow publish.yml, environment pypi), create the pypi environment in GitHub settings, then tag v0.2.0 (or current version) and push the tag. The workflow refuses if the tag does not match __version__.

## [claude] 2026-09-08 01:16 UTC
Deferred by the maintainer until Skald has seen more real backlogs. Installs come from GitHub meanwhile; see story 1b15cc and INSTALL_SPEC in cli.py for the one-line switch back.

## [claude] 2026-09-10 20:41 UTC · result
Published 0.4.0 to PyPI as skald-kanban via the tag workflow (trusted publisher, pypi environment with a required reviewer); pip install from a clean venv gives skald 0.4.0. Switched INSTALL_SPEC to skald-kanban so generated workflows install the release, test_render now asserts no git URL in the workflow, and README, getting-started, SPEC goal 1, the AGENTS template and its two copies install from PyPI with the git URL kept as the way to run the unreleased head.
