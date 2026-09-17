---
title: "Edit tags as chips in the card modal: inline key/value quick-edit in view mode, chip editor in the edit form"
status: "review"
rank: 30
tags: ["area:board"]
blocked_by: []
assignee: "agent"
created_at: "2026-09-17T01:24:53Z"
updated_at: "2026-09-17T01:25:58Z"
---
## Requirements

The comma-separated key:value string was the weakest part of the edit form.

- View mode: tag chips become clickable; clicking one opens a small key/value editor (empty key = plain tag, key = key:value facet), '+ tag' adds one, each change written immediately with a tags PATCH (same weight as the status quick-move).
- Edit pane: replace the comma input with removable chips (× to remove, click to edit) plus a persistent key/value add row; staged in state.editTags and saved with the form. A tag typed in the add row but not yet Added is folded in on Save so it is never dropped.
- Client-only; no API change (tags PATCH already existed). Standard library only.
