---
title: "Confirm Windows and macOS behaviour from CI"
status: "ready"
rank: 20
tags: ["packaging"]
blocked_by: []
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-06T19:41:24Z"
---
## Requirements

The suite was only run on Linux by the agent. The CI matrix includes macOS and Windows; watch the first run, especially the background server test (pid liveness uses OpenProcess on Windows, D15) and git path handling in changelog.

## [claude] 2026-09-06 19:41 UTC
First CI run after merging #2: Linux green on 3.9-3.13; macOS 4 failures, Windows 5. Root causes: \b in git --grep (BSD ERE), 5s daemon start timeout, unresolved temp paths in tests, backslashes in two printed paths, exec-bit assertion on Windows, CRLF template written by a test. Fixed in code (grep pattern, 20s timeout, posix path messages) and tests.
