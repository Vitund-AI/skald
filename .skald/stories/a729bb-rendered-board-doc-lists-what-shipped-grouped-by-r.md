---
title: "Rendered board doc lists what shipped, grouped by release"
status: "done"
rank: 110
tags: ["roadmap"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-13T23:08:40Z"
updated_at: "2026-09-14T05:42:10Z"
---
## Requirements

`skald render` adds a Releases section to `.skald/README.md`.

- A `## Releases` section: one collapsed `<details>` per version, newest-first, listing the stories that shipped in it (archived, `released` set, done-role; won't-do excluded).
- Reuse the `<details>` and table code the Archived section already uses; link each id to its story file where practical.
- Complementary to CHANGELOG.md, which stays the curated prose; this section is the mechanical, always-in-sync index. Prefer linking to the CHANGELOG over restating it.
- Shares the `store.releases()` helper with the board Releases view (18c326).
- Bounded so the doc does not bloat: collapsed details; consider capping or grouping older versions behind a summary.

## Why

The rendered doc is the in-repo, always-current snapshot that shows up in the repository and on GitHub without the server running. A release index there makes shipped history browsable wherever the repo is read.

## [agent] 2026-09-14 05:42 UTC · result
render_markdown adds a '## Releases' section after Unknown status when store.releases() is non-empty: one collapsed <details> per version newest first, the shipped stories in the same table the Archived section uses, ids linking to the archived files. Omitted when nothing has shipped. store.releases() (shared with the board view) groups archived, released, done-role stories by version via _version_key (numeric-aware sort), excluding won't-do (closed role). SPEC section 10b, CHANGELOG; render test covers the section appearing with only the done story and absent before any release. Suite 170 green.
