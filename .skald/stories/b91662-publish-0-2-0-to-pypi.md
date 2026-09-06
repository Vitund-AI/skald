---
title: "Publish 0.2.0 to PyPI"
status: "ready"
rank: 10
tags: ["packaging"]
blocked_by: []
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-06T07:04:42Z"
---
## Requirements

Human steps: create the pending trusted publisher on pypi.org (repository Vitund-AI/skald, workflow publish.yml, environment pypi), create the pypi environment in GitHub settings, then tag v0.2.0 and push the tag. The workflow refuses if the tag does not match __version__.
