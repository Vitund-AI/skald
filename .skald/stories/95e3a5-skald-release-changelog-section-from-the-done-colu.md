---
title: "skald release: changelog section from the done column, then archive with a version stamp"
status: "done"
rank: 300
tags: ["cli", "git"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-09T21:40:55Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

skald release VERSION reads every story in a done or closed column, writes a section for them into CHANGELOG.md (or --changelog PATH), stamps each with released: VERSION in its frontmatter, archives them, and commits with a Skald-Story trailer per story. --dry-run prints the section and changes nothing; --no-commit leaves the changes staged.

Changelog lines come from an optional ## Changelog section in the story body, written for users; the title is the fallback. Closed stories are listed under Not doing. If the changelog's first section is marked unreleased it becomes this version and the generated list is appended under ### Stories so hand-written notes survive; otherwise a new section goes in above the first.

Skald does not bump version files or create tags; that stays with the project's own release process. ls --release VERSION lists what shipped in a version.

## Changelog

skald release VERSION turns the done column into a changelog section and archives those stories with the version they shipped in. Stories can carry a ## Changelog section written for users; ls --release VERSION shows what went out.

## Acceptance
- [x] release --dry-run prints the section without touching files
- [x] release writes the changelog, stamps released, archives, and commits with trailers
- [x] An unreleased first section is renamed and the list appended under Stories
- [x] Closed stories appear under Not doing, never as changes
- [x] ls --release VERSION lists the archived stories of that version
- [x] Contract tells agents to write a ## Changelog section for user-visible changes

## [claude] 2026-09-09 21:43 UTC · result
release.py: plan (done and closed stories, validation), changelog_text (## Changelog section joined into one paragraph, notes excluded, title fallback), merge_changelog (unreleased first section renamed and list appended under ### Stories; otherwise new section above the first; missing file created), apply (write, mark_released, archive). CLI commits .skald, the changelog, and the render with a Skald-Story trailer per story; --dry-run and --no-commit. Store gained the released known field and mark_released; ls --release VERSION; completion offers past versions. Contract step 7 asks for a ## Changelog section on user-visible changes. Dry run on this repository lists the 15 done stories for 0.2.0. Seven tests.
