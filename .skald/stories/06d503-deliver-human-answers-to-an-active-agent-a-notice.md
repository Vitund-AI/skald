---
title: "Deliver human answers to an active agent: a notice on its next skald tool call"
status: "idea"
rank: 110
tags: ["epic:integrations", "roadmap"]
blocked_by: ["2fa664"]
created_at: "2026-11-10T00:25:23Z"
updated_at: "2026-11-11T02:00:18Z"
---
## Requirements

When a person answers an agent's question (`skald answer`, or the board),
the answer goes into the story file. The agent sees it only if it happens to
run `skald resume` again. An agent still working should hear about it
promptly.

Agents mostly use the CLI, so the notice has to ride on CLI output as well
as MCP results:

- Using the session records from 2fa664, Skald knows which notes a session
  has already been shown for the stories it is on. When an answer, or a
  human note addressed to the agent, lands on one of those stories, the
  agent's next `skald` command (CLI, on stderr) or `skald_*` tool call (MCP)
  carries a short notice: "New answer to Q1 on a73397 from jon: <first
  line>. Run skald resume a73397 for the rest."
- Each notice is shown once per session. Without a session id (a plain CLI
  run), it is once per author and checkout.
- It reads the story files, so an answer made from the board or another
  checkout is seen too, with no extra channel.
- Claude Code: an agent may not run a `skald` command for a while. A hook
  that runs between tool calls or before each prompt can run `skald inbox`
  and add any notice to the agent's context. Confirm which hook events
  allow added context before relying on one.
- Limitation, documented: an agent that has ended its turn to wait for the
  human makes no calls, so nothing reads the notice until its next turn
  starts. Waking an idle agent is out of scope (see a73397, and f2c74c
  for alerting the person instead).

## Acceptance

- [ ] After an answer to an open question on a story the agent is on, the agent's next `skald` CLI command (stderr) or MCP tool call carries a notice naming the story, the question and the answer's first line, exactly once.
- [ ] Answers made from the board or another checkout are noticed too.
- [ ] `skald inbox` prints pending notices; an optional Claude Code hook adds them to the agent's context if a suitable hook event exists, otherwise the story says why not.
- [ ] SPEC, AGENTS template, CLI and MCP docs, and CHANGELOG updated.
