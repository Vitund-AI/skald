---
title: "Release 1.0.0: Production/Stable classifier, a 1.x support policy, examples off the internals"
status: "plan"
rank: 10
tags: ["area:release", "release:1.0.0"]
blocked_by: ["0a2011", "80c968", "c9e05f"]
created_at: "2026-10-04T02:42:21Z"
updated_at: "2026-10-04T02:42:21Z"
---
## Requirements

The release itself, once the compatibility promise (0a2011), the
concurrency fix (80c968), and the API docs (c9e05f) are in.

- pyproject.toml: `Development Status :: 4 - Beta` -> `5 - Production/Stable`.
- SECURITY.md: replace "Skald is pre-1.0 ..." with the 1.x support policy
  (fixes land in the latest 1.x; an earlier line is patched from its tag on
  demand, as D63 already says).
- examples/model-routing/report.py imports `skald.registry` and
  `skald.store`, which 0a2011 declares internal. Move it to `skald ls
  --json` / `skald activity --json`, or label it as depending on internals.
- Optional: a 1.0.0rc1 first. There are no open issues, which says little
  either way about outside use.
- Before tagging: run examples/github-issues/sync.py --dry-run once
  against a real repository (it has only ever run against fixtures).
- `scripts/release.sh 1.0.0`.

## Acceptance
- [ ] classifier and SECURITY.md updated
- [ ] model-routing example no longer imports internals, or says so
- [ ] github-issues sync dry-run against a real repo, result noted here
- [ ] released as 1.0.0 (optionally after an rc)
