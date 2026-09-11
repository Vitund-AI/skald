---
title: "Import review 0.4.0: links across roots, git-added dates, path tags, mapping validation"
status: "done"
rank: 50
tags: ["import"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-10T21:33:38Z"
updated_at: "2026-09-11T04:56:19Z"
---
## Requirements

From the adopting repository's 0.4.0 review, findings 1-5.

- [x] rewrite-links always visits the stories directory, not only ROOT; links inside imported stories resolve against the record's origin
- [x] references resolve against every ancestor of the referencing file up to ROOT, and against the project root even outside ROOT
- [x] created_at falls back to the first git commit that added the source (git-added), then now; regex remains the override; 'error' keeps the strict behaviour
- [x] tag rules can match on 'path' (relative to the project root); 'skald import --tag KEY:VALUE' adds fixed tags per run
- [x] the mapping is validated before any file is read: regexes compile, $N templates fit the group count, 'on', 'status', note kinds and rule shapes are checked, with messages naming the rule
- [x] tests for each; docs/importing.md, cli.md, CHANGELOG, D60 addendum

## [claude] 2026-09-10 21:39 UTC · result
importer.py: validate_mapping (regexes, $N against group counts, on, status against columns, note kinds and shapes, created_at fallback) runs before any file is read and the CLI prints each problem as FILE: rule: message. git_added(source) reads the author date of the commit that added the file, following renames, as the default created_at fallback; 'now' and 'error' are the alternatives, and Plan.created_from tells the dry run which applied. _subject gains 'path' (under the project root) and plan_text takes extra_tags for --tag. rewrite_links walks ROOT plus the stories directory, resolves each token against the referencing file's ancestors up to ROOT and the project root, and for an imported story its origin's ancestors first. Tests: links across roots with ROOT=docs (bare sibling name inside a story, bucket-relative from another bucket, repository-relative from docs/), git-added date and path tags and --tag, mapping validation unit and CLI. Docs: importing.md, SPEC 6 row, cli.md, CHANGELOG, D60 addendum. 150 tests pass.
