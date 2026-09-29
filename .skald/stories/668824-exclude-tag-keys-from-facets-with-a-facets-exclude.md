---
title: "Exclude tag keys from facets with a facets.exclude config key"
status: "ready"
rank: 10
tags: ["area:config", "release:0.9.0"]
blocked_by: []
created_at: "2026-09-29T01:17:09Z"
updated_at: "2026-09-29T01:17:09Z"
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
- Exclusion never switches meaning off. `release:` gating, `lane:` limits
  (`facet_limits`), and `epic:` progress parse tags with `split_facet`
  directly and are unaffected.
- `facets` is an object so an `include` allowlist can be added later without
  a second top-level key. No `include` now (an allowlist silently drops new
  convention keys such as `effort:`).
- Validate like `facet_limits`: an object; `exclude` a list of keys matching
  KEY_RE; a key in both `exclude` and `facet_limits` is an error.

## Acceptance
- [ ] `facets.exclude` parsed and validated in config.py (bad shape, bad key, overlap with facet_limits all raise ConfigError)
- [ ] `store.facets()` omits excluded keys; tags themselves untouched, `ls --tag` still matches
- [ ] release:/lane:/epic: behaviour unchanged when their key is excluded (test)
- [ ] docs: stories.md config reference, conventions.md, SPEC config section; DECISIONS entry; CHANGELOG
- [ ] python3 -m unittest green, ruff clean, skald docs --check

## Changelog

A new `facets.exclude` list in `config.json` keeps chosen tag keys out of the
facet filters, swimlanes, the rendered board, and `skald facets`, so
machine tags such as `gh:12` stay searchable tags without cluttering the
board. Excluding a key never changes what `release:`, `lane:`, or `epic:`
tags do.
