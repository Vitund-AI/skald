---
title: "CodeQL findings: workflow token permissions, template name traversal, question reference regex"
status: "done"
rank: 40
tags: ["security"]
blocked_by: []
assignee: "claude"
released: "v0.5.1"
created_at: "2026-09-12T18:12:36Z"
updated_at: "2026-09-12T18:23:20Z"
---
## Requirements

CodeQL's first run on main reported three findings.

- [x] every workflow, and the one skald hooks github writes, sets permissions: contents: read at the top; jobs that write keep their own block
- [x] a template name is a plain slug; a name with a path separator or dots is refused, so --template cannot read a Markdown file outside .skald/templates/
- [x] the question reference parser has no ambiguous whitespace run (the old \s*q?\s* was quadratic on a long run of spaces)
- [x] tests; CHANGELOG

## [claude] 2026-09-12 18:13 UTC · result
Workflow-level permissions: contents: read in test.yml, publish.yml, skald.yml, and the template skald hooks github writes (the publish, diff, and render jobs keep their own write blocks); the generated-workflow test asserts it. TEMPLATE_NAME_RE restricts --template to a slug so the path is always .skald/templates/<name>.md; a CLI test tries ../../secret and gets the message. parse_question_ref removes whitespace first and matches ^q?(\d+)$, so there is no ambiguous \s* run; 200k spaces parse in a millisecond; tests cover the accepted forms and the rejected ones. CHANGELOG under Fixed.
