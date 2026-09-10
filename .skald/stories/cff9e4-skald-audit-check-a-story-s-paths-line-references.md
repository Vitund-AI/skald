---
title: "skald audit: check a story's paths, line references, and commit hashes against the tree, and note it"
status: "done"
rank: 90
tags: ["agents", "cli"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T05:09:37Z"
updated_at: "2026-09-10T18:04:04Z"
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
- [x] Extraction unit-tested on a fixture body
- [x] Temp repo: a deleted file, a file shorter than a cited line, a bogus hash, a file changed after a backdated audit note
- [x] resume header line; MCP tool; docs synced

## [claude] 2026-09-10 05:40 UTC · result
src/skald/audit.py: extract (paths with a directory, bare files with a line ref, path:N and N-M, 7-40 hex hashes with a letter and a digit; URLs and story ids excluded), resolve_path (root, else a unique basename match), run_audit (existence, line count, git cat-file -e, changed since the newest audit note else created_at via git log --since --name-only), summary_lines, status_line. CLI: skald audit [--notes] [--no-note] [--as] [--json], appends an audit note by default; resume header shows last audited / never audited and how many referenced files changed since. MCP skald_audit. Identifier grepping and audit_days left out on purpose (D57). Tests: extraction fixture; temp repo with a deleted file, a file shorter than a cited line, a bogus hash, and a change after a backdated audit note; MCP. Docs: SPEC 4.3 and 6, working-with-agents Keeping a design record true, AGENTS step 3 and copies, cli.md, CHANGELOG, D57. 137 tests pass.
