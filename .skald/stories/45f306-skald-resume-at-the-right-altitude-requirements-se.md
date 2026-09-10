---
title: "skald resume at the right altitude: requirements section only, table of contents, --section and --full"
status: "done"
rank: 40
tags: ["agents", "cli"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T05:09:37Z"
updated_at: "2026-09-10T18:04:03Z"
---
## Requirements

requirements_of returns everything above the first note heading, so resume on a 550-line design record prints all of it. A heading, not a length limit, should decide what resume prints, so the author of the body controls the cut and the rule is visible in the file. From the design-record feature request (item 3).

- When the body has a ## Requirements heading, requirements_of returns that section only, up to the next ## heading or the first note heading. Bodies without the heading keep today's behaviour.
- sections_of(body): the H2 headings outside notes with their line counts.
- resume prints a table of contents after the requirements: Also in this story: ## Design (120 lines) · ..., with the --section and --full hints.
- --full prints the whole body before the notes summary; --section NAME prints one section, matched case-insensitively by prefix.
- Compact JSON gains sections: [{heading, lines}]; requirements follows the new rule. MCP skald_resume gains full and section.
- Docs: SPEC 4.3, stories.md Sections the tools understand gains ## Requirements, AGENTS template step 3, cli.md, CHANGELOG, DECISIONS.

## Acceptance
- [x] requirements_of with and without the heading; heading followed directly by a note
- [x] resume prints the contents line; --section prefix match; --full
- [x] MCP resume accepts full and section
- [x] Docs synced

## [claude] 2026-09-10 05:12 UTC · result
prelude_of (everything before the notes) is the old behaviour under a new name; requirements_of returns the ## Requirements section when present; sections_of and section_of back the map and --section; --full prints the prelude. release reads Changelog from the prelude. MCP skald_resume takes section and full and returns sections. Tests in store, cli, mcp. Docs: SPEC 4.3, stories.md, AGENTS template step 3 and copies, cli.md, CHANGELOG, D53. 128 tests pass.
