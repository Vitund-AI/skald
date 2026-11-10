---
title: "Browser notification when a Claude Code session is waiting for the user"
status: "idea"
rank: 120
tags: ["area:board", "epic:integrations", "roadmap"]
blocked_by: ["2fa664"]
created_at: "2026-11-10T00:25:24Z"
updated_at: "2026-11-10T00:25:24Z"
---
## Requirements

Claude Code can stop and wait for the person: it asks a question
(AskUserQuestion), needs permission for a tool, or ends its turn and sits
idle at the prompt. With several agents running, the person may not notice
for a long time. The board is often open in a browser tab anyway. It could
show a browser notification: "claude is waiting for you on 6af629".

- Detection, Claude-specific: Claude Code hooks fire at these moments. The
  Notification event fires on permission prompts and on idle-waiting, Stop
  fires when a turn ends, and PreToolUse can match AskUserQuestion. Confirm
  the exact event names and payloads against the Claude Code docs before
  building. `skald hooks claude --install` adds a hook that runs a small
  `skald` command recording "waiting" (with the reason and the question
  text when there is one) on the session's presence record. The next tool
  call, or the next prompt, clears it.
- Board: the server pushes presence changes on its existing event stream.
  When a session goes to waiting, the page shows a badge on the card and
  fires a Notification ("claude is waiting on 6af629: <question>").
  Clicking it focuses the board on the story.
- Permission: the board asks for notification permission only from a
  user gesture (a "Notify me when an agent is waiting" toggle), remembered
  per browser.
- Secure context: browsers allow notifications only on localhost or
  HTTPS. A board on the LAN over plain HTTP cannot send them; the toggle
  says so and points at `--tls-cert`/`--tls-key` (D81).
- Other agents: nothing to detect with. The record format is
  agent-neutral, so another agent with a hook mechanism can set it too.

## Acceptance
- [ ] `skald hooks claude --install` adds the waiting hook(s); a Claude Code session waiting on a question, a permission, or idle at the prompt shows as waiting, and goes back to active when it resumes.
- [ ] The board badges waiting cards and, once the user turns it on, fires a browser notification that opens the story when clicked.
- [ ] On plain HTTP off localhost, the toggle explains that notifications need HTTPS.
- [ ] Docs (Claude integration page, SPEC, CHANGELOG) updated; DECISIONS entry.
