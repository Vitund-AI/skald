---
title: "Release script: let through main commits that change no file"
status: "review"
rank: 10
tags: ["area:release"]
blocked_by: []
assignee: "claude"
created_at: "2026-11-17T05:26:37Z"
updated_at: "2026-11-17T05:26:38Z"
---
## Requirements

The 1.3.3 release stopped at the new preflight (2ef4ed). It said `main` had
commits that `dev` lacked, but the only one was 8d5dd88, the merge of the
1.3.2 release pull request. That commit changes no file relative to `dev`,
so it could not make the pull request to `main` conflict.

- Refuse only when merging `origin/main` into `dev` would change `dev`'s
  files, or would conflict. Check with `git merge-tree --write-tree` against
  `HEAD^{tree}`. An older git without `--write-tree` (before 2.38) refuses
  as before.
- When only history differs, say so and carry on. Step 6 merges `main`
  back.

## Acceptance
- [x] A `main` that holds only a merge commit with dev's tree passes the preflight with a note.
- [x] A `main` with a real change (a render commit) still refuses.
- [x] Checked against this repository's history: 8d5dd88 passes, c2c236b (1.3.2's render commit) refuses.
- [x] Docs and CHANGELOG updated.

## [claude] 2026-11-17 05:26 UTC · handoff
Done. scripts/release.sh preflight: when HEAD..origin/main is not empty, compare git merge-tree --write-tree HEAD origin/main with HEAD^{tree}; equal means history only (proceed with a note), else or on conflict/old git refuse. tests/test_repo.py: a no-ff merge of dev on main passes; the board.txt change still refuses. Against real history: dev c12426a + main 8d5dd88 passes; dev ef9cdce + main c2c236b refuses. shellcheck clean.
