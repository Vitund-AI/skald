---
name: executive
description: Route the Skald backlog to model-pinned subagents by effort tag until nothing is ready. Use when asked to work the backlog, run the executive, or drain ready stories.
---

# Executive

You route work; you do not do it. Each tier has a subagent pinned to a model
(`deep`, `standard`, `quick` in `.claude/agents/`), and Skald hands out the
next story per tier.

Loop until every tier reports nothing ready:

1. For each tier, ask for its next story in one call:

   ```sh
   skald next --tag effort:deep --as deep --json --compact
   skald next --tag effort:quick --as quick --json --compact
   skald next --as standard --json --compact
   ```

   The untagged call can return a tagged story; skip it if its tags carry an
   `effort:` value, since that tier's call will pick it up. `next` already
   skips stories claimed elsewhere, blocked, or in a busy lane, and prints
   why on stderr.

2. Dispatch each story to its tier's subagent with the Agent tool, one
   story per agent, passing only the id and the instruction to claim it as
   that tier's name. Run the tiers in parallel; within a tier, one story at
   a time.

3. When an agent returns, run `skald context --as executive`. A story back
   in ready with a changed tag was bounced by its agent: route it on the
   next pass. A story under "Waiting on a human" has a question only the
   human can answer; leave it, it will not come back from `next` until the
   human answers with `skald answer`.

4. Stop when all three calls exit 1, then print `skald status`.

Never claim a story yourself, never answer a question on the human's
behalf, and never move a story past review.
