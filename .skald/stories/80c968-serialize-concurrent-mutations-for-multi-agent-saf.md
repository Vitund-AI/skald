---
title: "Serialize concurrent mutations for multi-agent safety (advisory file lock)"
status: "idea"
rank: 70
tags: ["area:store", "roadmap"]
blocked_by: []
created_at: "2026-09-20T00:59:03Z"
updated_at: "2026-09-20T00:59:03Z"
---
## Requirements

Harden for many sub-agents mutating one repo at once. IMPORTANT framing: atomic_write already writes via a temp file + os.replace + fsync (util.py), so a reader never sees a partial file and concurrent writes do NOT corrupt a story file. The real gap is the read-modify-write race: two 'skald claim' or 'skald move' (or two 'skald new') running in the same millisecond each read state, compute, then write — last writer wins, so one change is lost, a story could be double-claimed, or two new stories could collide on rank. This is a lost-update / TOCTOU problem, not file corruption.

- Serialize mutating operations with an advisory lock around the read-modify-write critical section: a per-store lock file taken with fcntl.flock on Unix and msvcrt.locking on Windows (both stdlib), released promptly; readers stay lock-free.
- Scope: claim, move/update, new, rank changes, archive — the store methods that read then write. Keep it a short critical section; never hold across a git call.
- Consider a small stress test spawning N concurrent claims/moves and asserting no lost update and one owner per story.

Design note: keep it minimal and cross-platform; a busy repo must not deadlock (timeout + clear error). Standard library only.
