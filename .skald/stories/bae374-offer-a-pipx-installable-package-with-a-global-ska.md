---
title: "Offer a pipx-installable package with a global skald command"
status: "done"
rank: 140
tags: ["packaging"]
blocked_by: ["9a1da4"]
created_at: "2026-09-06T02:16:15Z"
updated_at: "2026-09-08T17:24:16Z"
---
## Requirements

Keep the single-file vendored copy as canonical, but also publish the same file so `pipx install skald` gives a global `skald` and `git-skald` entry point. The global copy must resolve the data directory through the git root, which already works.

## [claude] 2026-09-06 07:04 UTC
Implemented: src/ layout, pyproject.toml, distribution name skald-kanban (skald is taken on PyPI, D7), console scripts skald and git-skald, publish workflow with PyPI trusted publishing on v* tags. Vendoring removed (D6).
