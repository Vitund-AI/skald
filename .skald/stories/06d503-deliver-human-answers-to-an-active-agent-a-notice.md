---
title: "Deliver human answers to an active agent: a notice on its next skald tool call"
status: "idea"
rank: 110
tags: ["epic:integrations", "roadmap"]
blocked_by: ["2fa664"]
created_at: "2026-11-10T00:25:23Z"
updated_at: "2026-11-10T00:25:23Z"
---
## Requirements

When a person answers an agent's question (`skald answer`, or the board),
the answer goes into the story file. The agent sees it only if it happens to
run `skald resume` again. An agent still working should hear about it
promptly.

- The MCP server tracks, per session, the notes it has already shown the
  agent for the stories it is on. When an answer, or a human note addressed
  to the agent, lands on one of those stories, the next result of any
  `skald_*` tool call carries a short notice: "New answer to Q1 on a73397
  from jon: <first line>. Run skald_resume a73397 for the rest."
- Each notice is shown once per session.
- Works for any MCP client and needs no agent-specific mechanism. It reads
  the story files, so an answer made from the board or another checkout is
  seen after the next file read, with no extra channel.
- Claude Code: `skald hooks claude` can also add the notice to the agent's
  context between tool calls or turns. Confirm which hook events allow
  added context before relying on one.
- Limitation, documented: an agent that has ended its turn to wait for the
  human does not make tool calls, so nothing reads the notice until its next
  turn starts. Waking an idle agent is out of scope (see a73397, and f2c74c
  for alerting the person instead).

## Acceptance
- [ ] After an answer to an open question on a story the session is on, the next `skald_*` tool result carries a notice naming the story, the question and the answer's first line, exactly once.
- [ ] Answers made from the board or another checkout are noticed too.
- [ ] Optional Claude Code hook surfaces the same notice, if a suitable hook event exists; otherwise the story says why not.
- [ ] SPEC, AGENTS template, MCP docs and CHANGELOG updated.
