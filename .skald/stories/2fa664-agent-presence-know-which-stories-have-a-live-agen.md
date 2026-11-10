---
title: "Agent presence: know which stories have a live agent session, from the skald mcp process"
status: "idea"
rank: 100
tags: ["area:board", "epic:integrations", "roadmap"]
blocked_by: []
created_at: "2026-11-10T00:25:23Z"
updated_at: "2026-11-10T00:25:23Z"
---
## Requirements

Skald cannot tell today whether an agent is working on a story right now.
A claim and an assignee say who took it, not whether that session is still
alive. Several features need the difference: delivering a human's answer
while the agent is active (06d503), alerting the user
when an agent is waiting on them (f2c74c), and any later "wake the agent" work
(a73397).

Every agent that uses Skald over MCP runs its own `skald mcp` process, and
that process lives exactly as long as the agent session. That makes it a
presence signal that works for any MCP client, not only Claude.

- On start, `skald mcp` writes a presence record under the user config
  home (`config_home()/sessions/<pid>.json`): pid, agent name (`--as` /
  `SKALD_AUTHOR`), project root and checkout, start time, and a heartbeat
  time. It removes the record on a clean exit.
- The record follows the story the session is on: set by `skald_claim` and
  `skald_resume`, updated by note and move calls, cleared when the story
  leaves the active columns.
- Liveness: a record counts only while its pid is alive (and, to survive
  pid reuse, its heartbeat is recent). Dead records are ignored, and the
  next writer removes them.
- `skald status` / `skald context` and the board show it: "claude active on
  6af629 since 10:02". The board badges the card and offers a filter.
  `/api/sessions` returns the live records for this project.
- Same machine only, and said so in the docs: a board served from another
  machine (the Pi) sees no sessions.
- Nothing is committed: presence is machine state, like locks, never story
  front matter.

## Acceptance
- [ ] `skald mcp` writes a presence record on start, keeps it current, and removes it on exit; a killed process's record is ignored and cleaned up.
- [ ] The record names the story the session is working on and follows claim, resume, note and move.
- [ ] `skald status`, `skald context` and the board show which stories have a live agent session; `/api/sessions` lists them.
- [ ] Docs say presence is local to the machine and never committed; SPEC, AGENTS template and CHANGELOG updated; DECISIONS entry for the design.
