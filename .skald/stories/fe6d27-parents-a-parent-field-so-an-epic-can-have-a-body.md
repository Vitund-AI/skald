---
title: "Parents: a parent field so an epic can have a body and children"
status: "ready"
rank: 70
tags: ["cli", "core"]
blocked_by: []
created_at: "2026-09-10T05:09:38Z"
updated_at: "2026-09-10T05:09:38Z"
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
- [ ] Field round-trip and canonical order; inherit tags; cycle and dangling detection; rm refusal
- [ ] ls --parent and marker; resume shows the parent's requirements
- [ ] Terminal-with-open-children warning; MCP; docs synced
