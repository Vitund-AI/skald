---
title: "Agent presence: know which stories have a live agent session (Claude Code hooks, skald mcp, CLI activity)"
status: "idea"
rank: 100
tags: ["area:board", "epic:integrations", "roadmap"]
blocked_by: []
created_at: "2026-11-10T00:25:23Z"
updated_at: "2026-11-11T02:00:18Z"
---
## Requirements

Skald cannot tell today whether an agent is working on a story right now.
A claim and an assignee say who took it, not whether that session is still
alive. Several features need the difference: delivering a human's answer
while the agent is active (06d503), alerting the user when an agent is
waiting on them (f2c74c), and any later "wake the agent" work (a73397).

Agents mostly drive Skald through the CLI, not `skald mcp` (Claude
included), so presence cannot rest on the MCP process alone. Three sources,
strongest first:

1. **Session hooks (Claude Code).** `skald hooks claude` already installs a
   SessionStart hook (`skald context`) and a Stop hook (`skald check`). The
   hook input carries the session id. SessionStart registers the session,
   with the agent name, checkout and the Claude process (the hook's parent).
   A SessionEnd hook removes it. That gives real start and end for
   Claude, with no polling. Confirm the event names and the hook input
   fields against the Claude Code docs.
2. **The `skald mcp` process,** for agents that do use MCP: it registers on
   start and removes the record on exit, and its pid is the liveness check.
3. **CLI activity, for everyone else.** Each `skald` command run with an
   author (`--as` or `SKALD_AUTHOR`) refreshes "last seen" on that author's
   record, and records which story it touched. Without a process to
   watch, this can only say "codex seen on 2fa664 4 minutes ago", never
   "active". The board shows it that way.

- Records live under the user config home (`config_home()/sessions/`),
  one file per session: source, agent, project root and checkout, story,
  started, last seen, state (`active`, `waiting` once f2c74c sets it).
  Machine state, like locks: never committed, never in front matter.
- The story follows claim, resume, note and move, and clears when the story
  leaves the active columns.
- A record with a known process counts while that process is alive. A
  record without one fades to "seen N minutes ago" and expires after a
  configurable idle time. The next writer removes dead records.
- `skald status`, `skald context` and the board show it ("claude active on
  6af629 since 10:02"); `/api/sessions` returns them for this project.
- Same machine only, and the docs say so: a board served from another
  machine (the Pi) sees no sessions.

## Acceptance

- [ ] With `skald hooks claude --install`, a Claude Code session is registered at start and removed at end; a crashed session's record is ignored once its process is gone.
- [ ] `skald mcp` registers and removes its own session the same way.
- [ ] Any `skald` command run with an author refreshes that author's last-seen time and story; the board shows such sessions as "seen N min ago", not active.
- [ ] `skald status`, `skald context` and the board show which stories have a live or recent agent; `/api/sessions` lists them.
- [ ] Docs say presence is local to the machine and never committed; SPEC, AGENTS template and CHANGELOG updated; DECISIONS entry for the design.
