---
title: "Board: an unsent note survives a tag, status or claim change in the story dialog"
status: "review"
rank: 20
tags: ["area:board"]
blocked_by: []
assignee: "claude"
created_at: "2026-11-12T23:10:04Z"
updated_at: "2026-11-12T23:10:05Z"
---
## Requirements

Reported by a user: open a story, start typing a note in Append note, then
click the release tag chip and change it before sending. The dialog
refreshes with the new tag, and the half-written note is gone.

Cause: `openModal` re-renders the dialog after every quick edit (tag chip,
status select, Claim) and always cleared `#m-note`. It also dropped the
question selected for an answer.

- Keep unsent note text per story (project:id) in page memory, saved on
  input and restored whenever that story's dialog renders: after a quick
  edit, and after going to another story and back.
- Sending the note (Append note or Answer) clears that story's draft.
- A refresh of the same story keeps the question being answered while it
  is still open.
- Page memory only: a reload drops the draft (stated in the docs).

## Acceptance
- [x] A note typed before a tag, status or claim change is still in the box afterwards.
- [x] Another story's dialog does not show it; coming back to the story does.
- [x] Sending clears the draft; the answer target survives a same-story refresh.
- [x] docs/board.md and CHANGELOG updated.

## [claude] 2026-11-12 23:10 UTC · handoff
Done in src/skald/web/index.html: state.noteDrafts keyed project:id, kept by an input listener (keepNoteDraft), restored in openModal instead of clearing, deleted in addNote on success; state.answering survives a same-story refresh when the question is still open. Checked in Chromium with Playwright on a scratch project: note survives a release-tag edit and a status change, is absent on another story, returns on coming back, clears on Answer Q1, and the decision note landed in the file.
