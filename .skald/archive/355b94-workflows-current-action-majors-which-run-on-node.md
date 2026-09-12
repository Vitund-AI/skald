---
title: "Workflows: current action majors, which run on Node 24"
status: "done"
rank: 10
tags: ["ci"]
blocked_by: []
assignee: "claude"
released: "0.5.1"
created_at: "2026-09-12T05:52:54Z"
updated_at: "2026-09-12T18:23:20Z"
---
## Requirements

Every run warns that actions/checkout@v4 and actions/setup-python@v5 target Node 20. The current majors run on Node 24.

- [x] test.yml, publish.yml, skald.yml and the template skald hooks github writes use checkout@v7, setup-python@v7, upload-artifact@v7, download-artifact@v8
- [x] the artifact pairing in publish.yml still lands the wheel at dist/ (upload archives by default; download extracts by name into path)
- [x] CHANGELOG

## [claude] 2026-09-12 05:54 UTC · result
checkout v7, setup-python v7, github-script v9, upload-artifact v7, download-artifact v8: each latest major's action.yml says runs.using node24 (checked at the tags). upload v7 archives by default and download v8 extracts by name into path, so publish.yml's dist/ handoff is unchanged; digest-mismatch now errors instead of warning, which is the intended default. github-script v9 only breaks scripts that require @actions/github or declare getOctokit; the diff job does neither. Bumped in test.yml, publish.yml, skald.yml, and the template in cli.py; the generated-workflow test still passes.
