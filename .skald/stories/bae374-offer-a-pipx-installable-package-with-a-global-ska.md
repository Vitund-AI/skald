---
title: "Offer a pipx-installable package with a global skald command"
status: "backlog"
rank: 40
tags: ["packaging"]
blocked_by: ["9a1da4"]
created_at: "2026-09-06T02:16:15Z"
updated_at: "2026-09-06T02:16:15Z"
---
## Requirements

Keep the single-file vendored copy as canonical, but also publish the same file so `pipx install skald` gives a global `skald` and `git-skald` entry point. The global copy must resolve the data directory through the git root, which already works.
