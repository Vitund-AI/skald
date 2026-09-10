---
title: "Branch dropdown: say worktree or clone on working-tree entries, mark branches that have one as committed only"
status: "review"
rank: 320
tags: ["ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T00:14:03Z"
updated_at: "2026-09-10T00:16:34Z"
---
## Requirements

A select shows optgroup labels only while open, so a closed control reading 'agent-two · skald-agent-two' looks like a branch, and the same branch name appears again in the read-only group with nothing saying why.

- Working-tree entries lead with the word worktree or clone, then the directory, then the branch: 'worktree skald-agent-two · agent-two · 1 uncommitted'; the primary ends with '· primary'.
- A read-only branch that a working tree is on reads 'agent-two · committed only'.
- The control's tooltip describes the current selection: the working tree's path and branch, or the read-only branch.
- Docs: board.md wording.

## Acceptance
- [x] Option text carries the kind and directory for working trees and 'committed only' for their branches
- [x] Tooltip follows the selection
- [x] board.md updated

## [claude] 2026-09-10 00:16 UTC · result
Working-tree options now read 'worktree DIR · BRANCH [· primary] [· N uncommitted]' or 'clone ...' (directory name, with parent when two share one); a read-only branch that a working tree is on reads '· committed only'; the control's tooltip describes the current choice. Verified in a browser against a clone plus worktree. Docs: board.md, multi-project.md (worktrees are re-scanned every 30s, no command needed in them), SPEC 8, CHANGELOG.
