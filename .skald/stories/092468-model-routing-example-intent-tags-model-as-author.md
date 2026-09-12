---
title: "Model routing example: intent tags, model as author, an executive loop over subagents"
status: "done"
rank: 30
tags: ["docs", "examples"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-12T03:22:00Z"
updated_at: "2026-09-12T05:25:15Z"
---
## Requirements

A user asked for cards to carry the model intended for the work and the model that did it, to learn which shape of problem suits which model. That is an application of tags and note authors, not a new field, and token counts stay out of the core (the harness knows them; Skald cannot observe them).

- [x] examples/model-routing/: README explaining the convention (effort: or model: tag for intent, --as NAME with the model for actuals), Claude Code subagent definitions pinned to models and effort levels, an executive skill that loops skald next --tag and dispatches, and a report script that joins intended tag with the authors of the notes that finished each story
- [x] the AGENTS template says: a story carrying an intent tag you do not match is not yours to claim
- [x] docs/working-with-agents.md section pointing at the example; README mentions examples; CHANGELOG; a DECISIONS entry on why model and cost are conventions, not fields

## [claude] 2026-09-12 03:27 UTC · result
examples/model-routing/: README with the convention (effort: tag for intent, --as MODEL for actuals, no token field; a cost note if a harness wants it), three subagents for .claude/agents pinned to opus/sonnet/haiku that claim under their own names and bounce mis-tagged work back to ready, an executive skill that loops skald next --tag per tier and dispatches, and report.py joining intended tier with note authors, days, and times sent back to ready from git history via skald activity. examples/README.md index. Contract: a story tagged with an intent you do not match is not yours to claim. docs/working-with-agents.md section, README docs row, CHANGELOG, D61. test_repo compiles every example script and runs the report against this repository. 153 tests pass.
