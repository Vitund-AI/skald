---
title: "Optional enforced/guarded column transitions (workflow rules)"
status: "idea"
rank: 30
tags: ["roadmap"]
blocked_by: []
created_at: "2026-09-17T06:04:20Z"
updated_at: "2026-09-17T06:04:20Z"
---
## Requirements

Parked idea, captured from the icebox/hold discussion. Skald deliberately does NOT enforce column transitions today: any move is legal (drag anywhere, skald move to any status), and we warn rather than block (open questions on ready, unchecked acceptance on done, open children on done). Keep it that way for now — this is not an enterprise tool.

Future ask users may raise: constrain which transitions are allowed, so the tool doesn't *facilitate* a risky move. The motivating case is the Icebox/hold column: reviving parked work should land in idea/plan, not straight into ready, so a stale plan is re-groomed before execution.

Two flavours, lightest first (prefer the lighter unless users clearly need the block):
1. Soft: a first-class 'hold' column role plus a WARNING (not a block) when a card moves from a hold column straight to a ready/active/done column — 'revived from hold; its plan may be stale, consider re-grooming'. Mirrors the existing warn-don't-block pattern in store.update. No transition engine.
2. Hard: an optional transition graph in config.json (allowed from->to per column/role), enforced in store.update, off by default. This is the enterprise-workflow path: heaviest, least Skald-like, and bypassable in two moves, so only if real demand appears.

Non-goals: tracking a card's previous status (the revive-to-grooming rule makes it moot); blocking moves by default. Decision context in this session's design thread; see also the Icebox column convention.
