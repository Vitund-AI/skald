---
title: "Run local agent sessions from the board: launch Claude Code (or any agent CLI) on a story in a terminal streamed to the browser"
status: "idea"
rank: 90
tags: ["area:board", "epic:integrations", "roadmap"]
blocked_by: []
created_at: "2026-10-04T02:42:38Z"
updated_at: "2026-10-04T02:42:47Z"
---
## Requirements

Today the Claude button on a story (f9e295, `claude_code_link`) opens
claude.ai/code with the repository and a prompt prefilled. When an agent
CLI is installed locally, the board could instead start it on the user's
machine, in that story's checkout, and stream its terminal into the page.
Several sessions open at once, one per story, gives the board a cockpit
for parallel agents, which is the use Skald is built for.

## Sketch

- **Launch:** a "Run locally" action on a card starts a configured agent
  command (`claude` by default; any CLI via settings) in a pseudo-terminal
  in the story's checkout, with a prompt such as "Work on story <id>; start
  with `skald resume <id>` and follow .skald/AGENTS.md" and
  `SKALD_AUTHOR` set.
- **Transport, standard library only:** output goes over the existing
  server-sent-events stream (or a per-session one), and keystrokes and
  resizes go over POST. On localhost the latency is fine, and it avoids
  writing WebSocket framing on top of http.server. The terminal emulator
  in the page is xterm.js, loaded from a CDN like Tailwind and marked.
- **Sessions on the board:** a card with a live session shows a badge. A
  sessions panel lists them, switches between them, and can close or kill
  one. The board already shows each worktree's working tree, so a session's
  edits appear live.
- **Parallel without collisions:** offer to start each session in a fresh
  git worktree. Skald already tracks claims across worktrees.

## Hard parts

- **Security, the main one.** The board stops being "reads and writes story
  files" and becomes "runs programs on this machine". Any auth bypass,
  CSRF, or DNS-rebinding hole becomes remote code execution. Minimum:
  - off by default, behind a machine-local feature flag (D66);
  - refused outright when the server is bound to anything but loopback
    (`--host 0.0.0.0`);
  - launches only commands configured on the machine, never a command line
    sent from the browser;
  - an Origin check and a CSRF token on the session endpoints;
  - SECURITY.md scope updated.
  This needs a DECISIONS entry before any code.
- **Windows.** `pty` is POSIX-only, ConPTY has no standard-library binding,
  and pywinpty would break the zero-dependency rule. Options: POSIX-only
  with a clear message on Windows, or an optional extra (`skald-kanban[terminal]`).
- **Lifecycle.** Should sessions outlive a browser tab (yes), a
  `skald server restart` (only with a host process), or a reboot (no)? A
  tmux-backed mode would make sessions survivable and attachable from a
  real terminal (`tmux attach`), with Skald not owning the processes.
- **Positioning.** Tools such as Vibe Kanban already pair a board with
  per-task agent sessions in worktrees. Skald's distinction is the files-
  in-git backlog, the contract, and the cross-repo board. This feature
  would move Skald toward being an agent runner, which is a product
  decision as well as a feature.

## Not now

This is post-1.0. It changes the server's security posture, so it should
land after the 1.0 compatibility and API-docs work (0a2011, c9e05f).

## [claude] 2026-10-04 02:42 UTC · question
Q1: Product direction: should Skald run agents, or only coordinate them? Running them is the bigger change and needs its own decision. If yes, the next questions are Windows (POSIX-only, or an optional pywinpty extra) and lifecycle (Skald owns the processes, or sessions run in tmux so they survive restarts and can be attached from a terminal).
