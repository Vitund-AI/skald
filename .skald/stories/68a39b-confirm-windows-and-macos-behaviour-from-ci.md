---
title: "Confirm Windows and macOS behaviour from CI"
status: "ready"
rank: 20
tags: ["packaging"]
blocked_by: []
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-06T07:04:42Z"
---
## Requirements

The suite was only run on Linux by the agent. The CI matrix includes macOS and Windows; watch the first run, especially the background server test (pid liveness uses OpenProcess on Windows, D15) and git path handling in changelog.
