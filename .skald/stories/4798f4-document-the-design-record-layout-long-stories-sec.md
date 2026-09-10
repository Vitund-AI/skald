---
title: "Document the design-record layout: long stories, sections the tools understand, a template"
status: "review"
rank: 70
tags: ["docs"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T05:09:37Z"
updated_at: "2026-09-10T05:25:10Z"
---
## Requirements

Add to docs/stories.md a section Long stories and design records with the recommended layout: ## Requirements (what resume prints), ## Acceptance (gates moves), ## Design, ## Residuals (each a candidate child), ## References (what audit checks), ## Changelog (feeds release); question, decision, handoff, and audit notes carry the history so the sections stay stable. Show the skeleton as a .skald/templates/design.md example created with --template design. No change to init. From the design-record feature request (item 4).

## Acceptance
- [x] stories.md section and template example
- [x] README docs table row mentions design records

## [claude] 2026-09-10 05:25 UTC · result
stories.md gains Long stories and design records with the recommended layout, which sections which tool reads, and that history lives in notes; README and docs index rows mention it; this repo carries .skald/templates/design.md as the skeleton (skald new --template design).
