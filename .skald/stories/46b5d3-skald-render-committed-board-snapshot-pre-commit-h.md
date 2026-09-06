---
title: "skald render: committed board snapshot, pre-commit hook, GitHub Action"
status: "in_progress"
rank: 20
tags: ["cli", "docs"]
blocked_by: ["cbb58e"]
assignee: "claude"
created_at: "2026-09-06T17:42:24Z"
updated_at: "2026-09-06T17:49:47Z"
---
## Requirements

Write a Markdown (default) or HTML snapshot of the backlog that GitHub renders in place, so browsing any commit shows the board as of that commit.

- [ ] skald render [--format md|html] [--out PATH] [--all] [--stage]; default .skald/README.md so the .skald folder shows the board on GitHub
- [ ] Deterministic output: no timestamp, an embedded content hash; links to story files are relative
- [ ] Terminal columns collapsed in details blocks; epic progress table from facets
- [ ] skald check warns when the snapshot is out of date
- [ ] skald commit and the board commit button re-render first when render is enabled in config.json
- [ ] skald hooks git --install: pre-commit hook running check and render --stage, never clobbering an existing hook
- [ ] skald hooks github --install: workflow running check on PRs and committing a fresh render on the default branch
