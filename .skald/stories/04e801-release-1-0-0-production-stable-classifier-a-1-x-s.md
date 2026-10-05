---
title: "Release 1.0.0: Production/Stable classifier, a 1.x support policy, examples off the internals"
status: "done"
rank: 40
tags: ["area:release", "release:1.0.0"]
blocked_by: ["0a2011", "80c968", "c9e05f"]
assignee: "claude"
created_at: "2026-10-04T02:42:21Z"
updated_at: "2026-10-05T21:42:50Z"
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
- [x] classifier and SECURITY.md updated
- [x] model-routing example no longer imports internals, or says so
- [x] github-issues sync dry-run against a real repo, result noted here
- [x] released as 1.0.0 (optionally after an rc)

## [claude] 2026-10-05 19:17 UTC · handoff
Prepared everything but the release itself. pyproject classifier -> 5 - Production/Stable. SECURITY.md: 1.x support policy (fixes ship in the latest 1.x; upgrading within 1.x is safe by the Compatibility promise); D63 addendum. examples/model-routing/report.py now reads only through the CLI's --json (ls, show, columns, status, activity) and the stable note-heading format; output identical to the old version on this repo (123 rows, field for field). GitHub sync real-data run: this repo has no issues (64 items, all PRs), and gh here only has gh api, so I fetched the 64 PRs via the REST API in gh issue list's shape (63 comments, bodies up to ~5 KB) and ran sync --from-json. It found a real bug: github-actions[bot] comment authors were rejected (brackets) and the run aborted mid-import. Fixed: bot logins become 'name (bot)'; one issue failing is reported and the rest import (exit 1); closed issues imported with --state all land in the first done column so they are not drift. After the fix: run 1 created 64, 0 failed, 0 drift; run 2 created 0, 64 already imported, 0 drift; skald check ok. Test added for all three. Remaining: scripts/release.sh 1.0.0 on the maintainer's machine (needs the GitHub CLI).

## [claude] 2026-10-05 21:42 UTC · decision
Accepted to done by the maintainer before running scripts/release.sh 1.0.0, so the release sweeps it with 0a2011, 80c968 and c9e05f; the final acceptance item is completed by that release run.
