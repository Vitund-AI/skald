---
title: "Wire Skald into Aider (context on launch; skald hooks aider)"
status: "idea"
rank: 50
tags: ["epic:integrations", "roadmap"]
blocked_by: []
created_at: "2026-09-20T00:58:43Z"
updated_at: "2026-09-20T00:58:43Z"
---
## Requirements

Capture the terminal-agent market: Aider is the dominant OSS terminal coding agent. Goal: an Aider user gets Skald's story context and contract the way skald hooks claude gives Claude Code its SessionStart/Stop hooks and skill.

Caveat to research first: Aider has NO SessionStart/Stop hook system like Claude Code. Its real extension points are its config (.aider.conf.yml), read-only context files (CONVENTIONS.md / the read: list / the /read command), and shell wrappers. So skald hooks aider would most likely: (a) add .skald/AGENTS.md (and maybe skald context output) to Aider's read files/CONVENTIONS so every session carries the contract; and/or (b) print/inject skald status on launch via a small wrapper. Confirm Aider's current mechanisms before designing.

- Follow the existing hooks pattern (installer prints the artifact without --install; refuses to overwrite a file it did not write; see cmd for hooks claude/git/github).
- Docs: a section alongside the Claude Code hooks; conventions doc.

Idea, not ready: needs a short spike on Aider's extension surface to choose the mechanism before it is schedulable.
