---
title: "skald audit: check a story's paths, line references, and commit hashes against the tree, and note it"
status: "ready"
rank: 60
tags: ["agents", "cli"]
blocked_by: []
created_at: "2026-09-10T05:09:37Z"
updated_at: "2026-09-10T05:09:38Z"
---
## Requirements

Design records cite file:line references and commit hashes that drift within days. The checkable half of a premise audit is mechanical. From the design-record feature request (item 2), trimmed: no identifier grep (slow on large trees and never a verdict), and no audit_days setting until the note has been used.

- skald audit <id> [--json] [--no-note] [--as NAME]: extract from the body (not notes) paths with an extension, path:NNN and path:NNN-MMM line references, and whole-word 7-40 hex commit hashes; check existence, line count, and git cat-file -e.
- Report referenced files changed since the newest audit note (else created_at) via git log --since --name-only.
- Append a --kind audit note with the compact summary unless --no-note. The tool lists what it could check; the agent judges the premises.
- resume header: last audited DATE (Nd ago); N referenced files changed since, or never audited.
- New module src/skald/audit.py with the extraction in one place; MCP skald_audit.
- Docs: SPEC 6 and 4.3 (audit kind); working-with-agents Keeping a design record true; AGENTS template step 3 (run audit when the story cites files or commits); cli.md; CHANGELOG; DECISIONS (the tool checks claims, the agent checks premises).

## Acceptance
- [ ] Extraction unit-tested on a fixture body
- [ ] Temp repo: a deleted file, a file shorter than a cited line, a bogus hash, a file changed after a backdated audit note
- [ ] resume header line; MCP tool; docs synced
