---
title: "Example: one-way import from GitHub issues"
status: "idea"
rank: 70
tags: ["examples", "roadmap"]
blocked_by: []
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-12T20:39:49Z"
---
## Requirements

Under examples/: a script that runs `gh issue list --json` for a repository, writes one Markdown record per issue (title, body, labels, created date, comments as dated blocks), and a mapping file for `skald import` that turns labels into tags and comments into notes. A README says what carries over and what does not.

## Why

The comparison table says Skald does not sync with hosted trackers, and by D60 a migration is a one-time step a person runs, so this belongs beside model routing as an example, not in the core.
