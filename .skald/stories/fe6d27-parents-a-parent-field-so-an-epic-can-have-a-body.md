---
title: "Parents: a parent field so an epic can have a body and children"
status: "review"
rank: 100
tags: ["cli", "core"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T05:09:38Z"
updated_at: "2026-09-10T05:45:49Z"
---
## Requirements

D28 chose epic: as a tag so epics needed no field and no body. On design-record backlogs the epic is the thing with the body, and its pieces ship separately; hand-maintained tables of pieces with commit hashes are what trailers exist to replace. From the design-record feature request (item 5), staged: this story is the field and the CLI; the board, epics merge, and commits union follow once children exist in practice.

- Optional frontmatter field parent (local id). new --parent <id> (copies the parent's facet tags unless --no-inherit); set parent=<id>, parent=- clears. format stays 1; unknown fields are preserved by 0.2.x.
- check: dangling parent and parent cycles are problems; cross-project parents rejected at set time.
- rm refuses while children exist, like blocked_by.
- ls --parent <id> lists children; ls shows a children marker on parents.
- resume <child> prints the parent's title and its ## Requirements above the child's own.
- Moving a parent into a terminal column with non-terminal children warns; archive and release warn too. Advisory. next is unchanged.
- MCP: skald_new gains parent; skald_set accepts it.
- Docs: SPEC 4.2, 4.4, 6; stories.md Epics: tag or parent; AGENTS template step 6 (discovered work that belongs to the story you are on becomes a child); cli.md; CHANGELOG; DECISIONS revising D28.

## Acceptance
- [x] Field round-trip and canonical order; inherit tags; cycle and dangling detection; rm refusal
- [x] ls --parent and marker; resume shows the parent's requirements
- [x] Terminal-with-open-children warning; MCP; docs synced

## [claude] 2026-09-10 05:45 UTC · result
parent field (canonical position after assignee, validated as a local id, omitted when empty). create(parent=, inherit=) copies the parent's facet tags; update(parent=) resolves locally, rejects self, cross-project, and cycles, parent=- clears. children(); story_dict children {total, done} on parents; check reports dangling parents and parent cycles; rm refuses while children exist; moving a parent to a terminal column with open children warns and release.plan warns too. CLI: new --parent/--no-inherit, set parent=, ls --parent, markers in ls, resume prints the parent's title and requirements. MCP new/set take parent; completion offers ids for --parent. Board, epics merge, and commits union are the second story (da2a34). Docs: SPEC 4.2 table, 4.4, 6; stories.md Epics: a tag, or a parent; AGENTS step 6 and copies; cli.md; CHANGELOG; D58. 140 tests pass.
