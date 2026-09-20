---
title: "Add skald export --format json|csv for portability and analytics"
status: "review"
rank: 40
tags: ["roadmap"]
blocked_by: []
assignee: "agent"
created_at: "2026-09-20T00:59:14Z"
updated_at: "2026-09-20T01:19:04Z"
---
## Requirements

The inverse of skald import: a clean, single-file dump of the whole backlog for analytics or migration to Jira/Linear, so users adopt Skald knowing they are not locked in.

Framing: the stories are ALREADY plain Markdown in git (the ultimate escape hatch), and skald ls --json emits per-story JSON. What is missing is a flattened, analytics-friendly single-file export of ALL stories (optionally including archived) with a stable, documented column/field set: id, title, status, role, rank, assignee, tags (and split-out facet columns like epic/area/release), blocked_by, created_at, updated_at, released, plus derived flags (blocked, stale, open-question count) where cheap.

- skald export --format json|jsonl|csv [--archived] [--out PATH|-]; deterministic ordering; UTF-8; csv quoting via the stdlib csv module.
- json: an array (or {stories:[...]}) mirroring the fields; jsonl: one JSON object per line (no wrapper), so a large backlog streams and pipes straight into jq / line-oriented data tools and appends cleanly; csv: one row per story, facets as their own columns so a PM can pivot in Excel.
- Docs: git-and-ci.md or a portability section; a line in the README's 'not locked in' pitch. Tests: round-trippable field set, csv escaping, jsonl is one object per line, --archived inclusion.
- (Title still reads json|csv; scope is json|jsonl|csv — the body is authoritative.)

Reuse store.story_dict / load_all; keep it read-only. Standard library only.
