---
title: "Example: re-runnable one-way sync from GitHub issues"
status: "ready"
rank: 20
tags: ["examples", "release:0.9.0", "roadmap"]
blocked_by: ["668824"]
created_at: "2026-09-12T20:39:49Z"
updated_at: "2026-09-29T01:17:16Z"
---
## Requirements

Under `examples/github-issues/`: a standard-library script that syncs a
repository's GitHub issues into the backlog, one way and read-only, and is
safe to run again and again.

- Fetch with `gh issue list --json number,title,body,labels,createdAt,url,state,comments`
  (open issues by default; `--state all` for closed too), or read the same
  JSON from a file (`--from-json`) so it is testable without `gh`.
- For each issue with no story tagged `gh:<number>` (archived stories
  included, so shipped work is not re-imported): `skald new` with the title,
  the body plus a link back to the issue, labels as tags, `gh:<number>`, and
  `--created-at` from the issue; each comment becomes a dated
  `skald note --at` by its author.
- Never edit a story it created earlier. Instead report drift: an issue
  closed on GitHub whose story is not done, a story done whose issue is
  still open, an issue retitled since import.
- `--dry-run` shows what would be created and the drift, changing nothing.
- A README: setup, what carries over and what does not, add `"gh"` to
  `facets.exclude` (668824), and why this is one-way (D60; the README's
  comparison table).

## Why

The comparison table says Skald does not sync with hosted trackers, and by
D60 a migration is a step a person runs, so this belongs beside model
routing as an example, not in the core. Making it re-runnable turns a
one-time migration into a way to keep pulling new issues in.

## Acceptance
- [ ] a re-run creates nothing for issues already imported (tag match, archived included)
- [ ] labels become tags, comments become dated notes, created_at follows the issue
- [ ] drift report covers closed-issue/open-story, done-story/open-issue, and retitles
- [ ] --dry-run changes nothing; --from-json works without gh
- [ ] tests over a fixture JSON; README; examples/README.md lists it
- [ ] python3 -m unittest green, ruff clean

## Changelog

A new example, `examples/github-issues`, pulls a repository's GitHub issues
into the backlog as stories tagged `gh:<number>`, with labels as tags and
comments as notes. It is safe to re-run: issues already imported are
skipped, and it reports issues and stories that have drifted apart instead
of overwriting either side.

## [claude] 2026-09-29 01:17 UTC · decision
Rescoped with the maintainer from a one-shot import to a re-runnable, read-only, one-way sync. Each imported story carries a gh:<number> tag; a re-run skips issues that already have a story (archived included), so the board never duplicates. Stories already imported are not edited; the script reports drift instead (e.g. issue closed on GitHub, story still open) and leaves the fix to a person. Two-way sync is out of scope: conflicts, a lossy status map, comment echo, and write access to someone's tracker make it a product decision, and the README positions Skald as not syncing. The one safe write-back (close the issue when its story ships) is its own idea story. Stories are created through the CLI (skald new --created-at, skald note --at), not skald import, because import is a folder migration with no notion of already-imported. The README tells the adopter to add "gh" to facets.exclude (668824) so per-issue tags stay out of the facet filters.
