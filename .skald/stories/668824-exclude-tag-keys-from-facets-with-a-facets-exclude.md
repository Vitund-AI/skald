---
title: "Exclude tag keys from facets with a facets.exclude config key"
status: "done"
rank: 20
tags: ["area:config", "release:0.9.0"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-29T01:17:09Z"
updated_at: "2026-09-29T17:20:51Z"
---
## Requirements

Any `key:value` tag becomes a facet today, so machine tags such as `gh:12`
(one value per story) crowd the board's facet filters, the "Swimlanes by…"
list, the rendered facet section, and `skald facets`. Add a project
`config.json` key that switches a tag key out of the facet surfaces:

```json
"facets": { "exclude": ["gh"] }
```

- An excluded key is still a tag: it stays in the story file, shows as a
  chip on the card, and `skald ls --tag gh:12` finds it. It is dropped only
  from `store.facets()` and so from every display surface that reads it
  (board filters and swimlanes, the rendered README, `skald facets` /
  `skald epics`).
- Exclusion never switches behaviour off. `release:` gating and `lane:`
  limits (`facet_limits`) parse tags with `split_facet` directly and are
  unaffected. (Epic progress in the render and `skald epics` is a facet view,
  so excluding `epic` hides it there; that is the point of excluding.)
- `facets` is an object so an `include` allowlist can be added later without
  a second top-level key. No `include` now (an allowlist silently drops new
  convention keys such as `effort:`).
- Validate like `facet_limits`: an object; `exclude` a list of keys matching
  KEY_RE; a key in both `exclude` and `facet_limits` is an error.

## Acceptance
- [x] `facets.exclude` parsed and validated in config.py (bad shape, bad key, overlap with facet_limits all raise ConfigError)
- [x] `store.facets()` omits excluded keys; tags themselves untouched, `ls --tag` still matches
- [x] release: gating and lane: limits unchanged when release is excluded / lane is limited (test)
- [x] docs: stories.md config reference, conventions.md, SPEC config section; DECISIONS entry; CHANGELOG
- [x] python3 -m unittest green, ruff clean, skald docs --check

## Changelog

A new `facets.exclude` list in `config.json` keeps chosen tag keys out of the
facet filters, swimlanes, the rendered board, and `skald facets`, so
machine tags such as `gh:12` stay searchable tags without cluttering the
board. Excluding a key never changes what `release:` or `lane:`
tags do.

## [claude] 2026-09-29 01:20 UTC · handoff
Done. config.py parses facets.exclude into ProjectConfig.facet_exclude (object with only 'exclude'; list of KEY_RE keys; unknown inner keys and overlap with facet_limits raise ConfigError). store.facets() skips excluded keys, so the board filters/swimlanes, render facet+epic sections, and skald facets/epics all drop them; tags, --tag matching, release: gating, and facet_limits lanes are untouched; export keeps them. Tests: tests/test_store.py TestFacets.test_facets_exclude_hides_keys_but_keeps_tags_and_meaning, tests/test_cli.py TestFacetCommands.test_facets_exclude_keeps_tag_queries. Docs: SPEC config list, docs/conventions.md new section, docs/board.md pointer, CHANGELOG, DECISIONS D75. Verified: unittest 200 OK, ruff clean, docs --check.
