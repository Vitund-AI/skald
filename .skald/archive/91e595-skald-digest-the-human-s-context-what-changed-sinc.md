---
title: "skald digest: the human's context, what changed since you last looked"
status: "done"
rank: 30
tags: ["roadmap"]
blocked_by: []
assignee: "claude"
released: "0.7.0"
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-14T15:24:52Z"
---
## Requirements

The agent gets one block on session start; the human gets the board and nothing else. `skald digest [--since 1d|REF]` assembles the morning check-in: stories moved, notes written, questions asked, grouped by story, newest first, from git history (`activity` has the events) and the notes (`resume` reads them). Bounded like `context`: a cap per section and a pointer to the full command.

## Why

Every review this week came from a human reading story files by hand to find out what an agent did overnight. No new data is needed; the two sources exist.

## [agent] 2026-09-13 22:51 UTC · result
skald digest [--since 1d|REF] [--until REF] [--limit N] [--json]. _digest_since parses a duration (1d/6h/30m/2w -> a git --since approxidate) or treats the value as a ref; gitutil.commits_touching gained since_is_date to pass --since=<expr>. _digest_data folds the same diff_states events activity uses into one record per story (created, net status move first-from->last-to, notes added, body edited, archived, deleted), orders by most recent event, then reads the current story for the latest note (handoff or newest) and open questions. Output: 'Since <label>: N stories changed', then per story the id/title/status, created/moved/archived/deleted, note count with the latest note's kind+stamp+first line, and up to two open questions with a pointer for the rest; --limit caps the stories with '... and M more: skald activity --since <since>'. --json returns {since, until, stories}. It is the human counterpart to activity's per-event log: no new data, git history plus the notes. Docs: SPEC command table, docs/git-and-ci.md, docs/cli.md regenerated, CHANGELOG Unreleased. tests/test_digest.py covers since parsing, the grouped output, JSON, the cap pointer, and an empty range. Suite 160 green, ruff clean.
