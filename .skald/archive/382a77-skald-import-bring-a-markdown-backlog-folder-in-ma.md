---
title: "skald import: bring a Markdown backlog folder in, mapping-driven, reproducibly"
status: "done"
rank: 40
tags: ["cli", "docs"]
blocked_by: []
assignee: "claude"
released: "0.4.0"
created_at: "2026-09-10T18:49:53Z"
updated_at: "2026-09-10T20:18:46Z"
---
## Requirements

Every repository with a backlog/ folder faces the same migration. A one-off script solves it once; a command with a mapping file and a dry run solves it for the next adopter and makes the migration reviewable in a pull request. The first corpus (184 open design records) is measured and its mapping is written, so the command can be built now and used for the pilot. From the design-record request (item 7) and the 0.3.0 adoption review.

- skald import PATH... [--map FILE] [--status COL] [--dry-run] [--rm] [--rewrite-links ROOT] [--as NAME]
- Title from the first H1, which is dropped; else the filename. The rest of the body is kept byte for byte apart from stripped lines and extracted note blocks; wrapped under ## Requirements unless that heading is present.
- --map FILE (JSON, so the standard library reads it): created_at regex with a group; status rules (regex on filename/relpath/body, first match wins, default); tags rules with $1 substitution; notes rules: block (start regex, until regex, date_group, kind) and section (heading regex, per bullet, kind); strip regexes; exclude globs.
- Extracted blocks become backdated notes in their original order (note --at); sections per bullet become notes of the given kind stamped at created_at.
- --rewrite-links ROOT rewrites references to each imported path across ROOT to the new story path, relative to the referencing file, and prints counts per file; intra-backlog links in the new stories are rewritten too.
- --rm deletes the source in the same operation so one commit carries removal and creation and git's rename detection keeps history.
- --dry-run prints, per file, the frontmatter it would write, the notes with stamps, the tags, and the link rewrite count, then a summary; nothing is written.
- No MCP tool: a migration is a set-up step a human runs from a shell, and MCP stays for runtime operations.
- Docs: docs/importing.md linked from the README table and getting-started; SPEC 6; cli.md; CHANGELOG; DECISIONS.

## Changelog

`skald import` brings an existing folder of Markdown records into the backlog, driven by a JSON mapping file: titles, creation dates, statuses, tags, and dated notes are extracted by rules you write, bodies are kept byte for byte, links across the repository can be rewritten to the new story files, and a dry run shows exactly what would happen.

## Acceptance
- [x] Fixture folder with records exercising every mapping rule
- [x] --dry-run writes nothing; --rm plus a commit keeps history under git log --follow; link rewriting in a sibling file and in an imported story
- [x] Docs: importing.md, README row, getting-started, SPEC, cli.md, CHANGELOG, DECISIONS

## [claude] 2026-09-10 18:54 UTC · result
src/skald/importer.py: load_mapping, plan_text (H1 title, created_at regex, status rules first-match with default, tag rules with $1, block and section note rules, strip, requirements wrap unless present, gaps collapsed), collect with ** globs in exclude, rewrite_links (Markdown links and bare paths resolved against the referencing file, ROOT, and, for a moved record, its original directory). CLI: skald import PATH... --map --status --rewrite-links --rm --dry-run --as; any problem aborts before writing; create gained wrap=False. Tests: fixture corpus with every rule, dry run writes nothing, --rm plus a commit keeps history under git log --follow, links rewritten in a sibling file and inside an imported story, problems abort, --status override. Docs: docs/importing.md, README and docs index rows, getting-started, SPEC 6, cli.md, CHANGELOG, D60. No MCP tool by decision. 147 tests pass.
