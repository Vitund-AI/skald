---
title: "Docs sweep for checkouts: README bullets and index rows, agent contract, Help panel legend, git-and-ci"
status: "done"
rank: 360
tags: ["docs"]
blocked_by: []
assignee: "claude"
released: "0.2.0"
created_at: "2026-09-10T00:25:30Z"
updated_at: "2026-09-10T00:56:31Z"
---
## Requirements

The checkouts feature landed with its own pages, but the surfaces that summarise the board and multi-project features still describe only branches.

## Changelog

The README, docs index, agent contract, board Help panel, and git guide now describe working trees of several checkouts alongside branches.

## Acceptance
- [x] README board bullet and Multiple projects row mention working trees of several checkouts
- [x] docs/README.md rows likewise
- [x] AGENTS template says claims are seen in other checkouts as well as other branches; .skald/AGENTS.md and the skill copy match
- [x] Help panel badge legend and git-and-ci Other branches section mention checkouts

## [claude] 2026-09-10 00:26 UTC · result
README board bullet and Multiple projects row, docs/README.md rows, AGENTS template (orientation and pick-work steps say claims are seen in other checkouts before commit) with .skald/AGENTS.md and the skill copy updated, Help panel badge legend, git-and-ci Other branches section pointing at working-tree entries for uncommitted state. 127 tests pass.
