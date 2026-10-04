---
title: "Serialize concurrent mutations for multi-agent safety (advisory file lock)"
status: "review"
rank: 10
tags: ["area:store", "release:1.0.0", "roadmap"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-20T00:59:03Z"
updated_at: "2026-10-04T03:11:29Z"
---
## Requirements

Harden for many sub-agents mutating one repo at once. IMPORTANT framing: atomic_write already writes via a temp file + os.replace + fsync (util.py), so a reader never sees a partial file and concurrent writes do NOT corrupt a story file. The real gap is the read-modify-write race: two 'skald claim' or 'skald move' (or two 'skald new') running in the same millisecond each read state, compute, then write — last writer wins, so one change is lost, a story could be double-claimed, or two new stories could collide on rank. This is a lost-update / TOCTOU problem, not file corruption.

- Serialize mutating operations with an advisory lock around the read-modify-write critical section: a per-store lock file taken with fcntl.flock on Unix and msvcrt.locking on Windows (both stdlib), released promptly; readers stay lock-free.
- Scope: claim, move/update, new, rank changes, archive — the store methods that read then write. Keep it a short critical section; never hold across a git call.
- Consider a small stress test spawning N concurrent claims/moves and asserting no lost update and one owner per story.

Design note: keep it minimal and cross-platform; a busy repo must not deadlock (timeout + clear error). Standard library only.

## Acceptance
- [x] a per-project advisory lock (fcntl.flock / msvcrt.locking, stdlib) wraps the read-modify-write of claim, move/update, new, rank, archive, note, and answer; readers stay lock-free
- [x] the critical section never spans a git call; a held lock times out with a clear error, never a deadlock
- [x] a stress test runs N concurrent claims/moves/news in subprocesses and asserts no lost update, one owner per story, unique ids and ranks
- [x] works on Linux, macOS, and Windows in CI
- [x] DECISIONS entry; CHANGELOG
- [x] python3 -m unittest green, ruff clean

## Changelog

Concurrent `skald` commands in one checkout no longer overwrite each
other: two agents claiming, moving, or creating stories at the same moment
now take turns, so a story cannot be claimed twice and no change is lost.

## [claude] 2026-10-04 03:11 UTC · handoff
Done. New src/skald/lock.py: project_lock(skald_dir) = per-path threading.RLock (re-entrant, serialises the server's threads) + an OS file lock (fcntl.flock / msvcrt.locking) on <config home>/locks/<sha of .skald path>.lock, outside the repo; released by the OS if a process dies; timeout SKALD_LOCK_TIMEOUT (30s) -> LockTimeoutError (HTTP 503). store.py: @_mutates on create, update, claim, reorder, answer, append_note, write_body, delete, mark_released, archive; new Store.edit_tags / edit_blockers so skald tag/block (CLI and MCP) read and write inside the lock instead of reading in the front end. No locked method calls git. Board PATCH still sends whole values (stale-board last-writer-wins, documented). tests/test_lock.py races 8 real processes released together: tags all kept, exactly one claimant finds the story free, distinct ranks/ids on concurrent new; plus threads in one process, re-entrancy, lock outside the repo, timeout across processes. Verified the tests catch the bug: with the lock disabled 4-5 of 5 fail per run; with it, 8/8 runs pass. Docs: SPEC 4.7 + module list + 2.3 locks/, troubleshooting, working-with-agents, DECISIONS D76, CHANGELOG. unittest 206 OK, ruff clean, docs --check.
