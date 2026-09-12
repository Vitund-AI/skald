---
title: "Security policy and the flow for patching an earlier release"
status: "review"
rank: 20
tags: ["docs", "security"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-12T19:54:14Z"
updated_at: "2026-09-12T19:54:33Z"
---
## Requirements

- [x] SECURITY.md: how to report (GitHub private vulnerability reporting), what to expect, supported versions (the latest release; an earlier line at the maintainer's discretion), what is in and out of scope given Skald runs as the user on the user's machine, what happens after a fix (advisory, changelog, yank)
- [x] docs/git-and-ci.md: patching an earlier release, fix forward first, then a maintenance branch cut from the tag, cherry-pick, changelog and version on the branch, tag on the branch, advisory, yank; tags are never deleted or moved once published; yank rather than delete on PyPI
- [x] D63; CHANGELOG; README links the policy

## [claude] 2026-09-12 19:54 UTC · result
SECURITY.md: private vulnerability reporting link, three-day acknowledgement, seven-day assessment, fourteen-day aim for fixes that cross a trust line, supported-versions table (latest; earlier lines at discretion), scope in terms of what Skald is responsible for (board token and requests, path handling, MCP and CLI on story input, the package) and what the user's own machine covers, and the after-a-fix steps (advisory, changelog, yank not delete, tags never moved). git-and-ci.md 'Patching an earlier release': fix forward first, branch from the tag on demand, cherry-pick, version and changelog by hand on the branch, tag on the branch (the publish workflow keys on the tag), advisory and a changelog line on dev, the branch is not merged back; the two standing rules on tags and yanking. D63. README links the policy. CHANGELOG.
