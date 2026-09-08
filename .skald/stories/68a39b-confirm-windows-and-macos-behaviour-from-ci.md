---
title: "Confirm Windows and macOS behaviour from CI"
status: "review"
rank: 190
tags: ["packaging"]
blocked_by: []
created_at: "2026-09-06T07:04:42Z"
updated_at: "2026-09-08T17:24:21Z"
---
## Requirements

The suite was only run on Linux by the agent. The CI matrix includes macOS and Windows; watch the first run, especially the background server test (pid liveness uses OpenProcess on Windows, D15) and git path handling in changelog.

## [claude] 2026-09-06 19:41 UTC
First CI run after merging #2: Linux green on 3.9-3.13; macOS 4 failures, Windows 5. Root causes: \b in git --grep (BSD ERE), 5s daemon start timeout, unresolved temp paths in tests, backslashes in two printed paths, exec-bit assertion on Windows, CRLF template written by a test. Fixed in code (grep pattern, 20s timeout, posix path messages) and tests.

## [claude] 2026-09-06 20:54 UTC · result
Windows and macOS unittest jobs pass on the test workflow (run 34059184121 on d0be454), alongside Linux 3.9 to 3.13. Fixes needed: BSD ERE has no \b (git --grep), posix-form paths in messages, LF template fixtures, resolved temp paths, and skipping the exec-bit and XDG assertions on Windows. The last macOS failure was HTTPServer.server_bind calling socket.getfqdn, which stalls 30s+ on macOS runners; SkaldServer now binds without the lookup (D39). Merged in PR #3.
