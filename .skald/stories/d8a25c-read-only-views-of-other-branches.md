---
title: "Read-only views of other branches"
status: "review"
rank: 70
tags: ["core", "ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T17:42:24Z"
updated_at: "2026-09-08T17:24:21Z"
---
## Requirements

Read .skald/ from any branch without touching the working tree, using git for-each-ref, ls-tree, and cat-file --batch. The checked-out branch stays the truth; other branches are read-only overlays and dependencies never resolve across branches.

- [ ] gitutil: list branches (local and remote), batch-read blobs at a ref
- [ ] Store.snapshot(ref): parse stories and config from git objects
- [ ] skald branches: per-branch story counts and how many differ from the working tree
- [ ] skald ls --branch REF and skald show <id> --branch REF
- [ ] API: GET .../branches and GET .../board?ref=REF (read-only), cached by commit sha
- [ ] Board: branch dropdown, read-only banner, badge for stories that exist only elsewhere

## [claude] 2026-09-06 17:46 UTC
Implemented. gitutil.branches and cat_file_batch read git objects; Store.snapshot(ref) returns a read-only Snapshot that duck-types the store's read side; branch_diff compares by id. CLI: branches, ls --branch, ls --all-branches, show --branch. API: GET .../branches and ?ref= on board and story, cached by commit sha. Board: branch dropdown, +N elsewhere badge, read-only banner with disabled editing. Verified in Chromium. See D27.
