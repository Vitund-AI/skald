---
title: "skald render: committed board snapshot, pre-commit hook, GitHub Action"
status: "done"
rank: 120
tags: ["cli", "docs"]
blocked_by: ["cbb58e"]
assignee: "claude"
created_at: "2026-09-06T17:42:24Z"
updated_at: "2026-09-10T00:56:04Z"
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

## Changelog

`skald render` writes a Markdown or HTML snapshot of the board, by default `.skald/README.md`, so GitHub shows the backlog in place at any commit. `skald render --enable` re-renders on commit, `skald hooks git --install` adds a pre-commit hook, and `skald hooks github --install` writes a workflow that checks the backlog and refreshes the snapshot.

## [claude] 2026-09-06 17:53 UTC
Implemented. skald render writes Markdown (default, .skald/README.md so GitHub shows the board in the folder view) or HTML with a content hash instead of a timestamp (D29, D30); ids link to story files; terminal columns collapsed; epic progress table from facets. check warns when stale; commit and the board button re-render when enabled in config.json, staging the file even outside .skald/. hooks git --install writes a pre-commit hook and refuses to clobber a foreign one; hooks github --install writes a workflow that checks on PRs and commits a fresh render on the default branch. Enabled on this repo.
