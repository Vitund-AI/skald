---
title: "Machine-local feature-flag config layer"
status: "review"
rank: 10
tags: ["area:config", "epic:feature-flags"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-14T23:46:30Z"
updated_at: "2026-09-14T23:54:08Z"
---
## Requirements

Extend the machine-local user config (SKALD_HOME/config.json, never committed)
from flat settings to support feature flags with a global default and a
per-project override. This is the foundation the settings modal (see the
blocked-by chain) and the "Open in Claude Code" link build on.

Design (agreed with the maintainer, machine-local only for v1 — no committed
project default, no fourth resolution layer):

Config shape:

```json
{
  "author": "jon",
  "push": false,
  "features": { "claude_code_link": true },
  "projects": { "skald": { "features": { "claude_code_link": false } } }
}
```

Resolution, most specific wins:
`projects[name].features[flag]` -> `features[flag]` -> built-in default.

Keyed by project **name** (not path): the registry already keys by name, and a
preference should follow the project across worktrees and clones.

A catalog declares each flag once, so the modal and CLI are generic:

```python
FEATURE_DEFAULTS = {
    "claude_code_link": {
        "label": "Open in Claude Code",
        "help": "Show a deep-link on the card detail view that opens the story as a Claude Code web session.",
        "default": True,
    },
}
```

## Scope

- `registry.py` `UserConfig`: add `features` (global) and `projects.<name>.features`
  (per-project) storage, a `FEATURE_DEFAULTS` catalog, and resolution
  `feature(name, project=None) -> bool` plus `features(project=None) -> dict`
  (resolved) and a way to read/set/unset a flag at either scope.
- Keep the existing flat prefs (author/push/port/host/stale_days) working
  unchanged; tolerate hand-edited/legacy config (missing blocks -> defaults).
- CLI: `skald config` learns feature flags and a `--project NAME` scope, e.g.
  `skald config features.claude_code_link true` and the same with `--project`.
  Unset returns to inherit. Completion offers flag names and true/false.
- Validation: unknown flag name is an error listing known flags; values are
  booleans; per-project block validates project-name shape.

## Out of scope

- No server endpoints or UI (story: settings modal + API).
- No consumer of any flag yet (story: Open in Claude Code button).
- No committed project-level default in .skald/config.json (deferred by decision).

## Acceptance
- [x] UserConfig stores and resolves a flag at built-in / global / per-project scope
- [x] resolution precedence is per-project > global > built-in, keyed by project name
- [x] legacy/flat config.json still loads; existing prefs unchanged
- [x] `skald config` reads/sets/unsets flags globally and with --project, completion updated
- [x] unit tests cover resolution, precedence, coercion of hand-edited values, CLI
- [x] SPEC.md documents the feature-flag layer; DECISIONS.md entry for machine-local-only
- [x] python3 -m unittest green, ruff clean

## [claude] 2026-09-14 23:54 UTC · handoff
Built the machine-local feature-flag layer. UserConfig (registry.py) gains a FEATURE_DEFAULTS catalog and feature()/features()/set_feature()/unset_feature()/feature_catalog(), resolving per-project > global > built-in default, keyed by project name; a coerce_bool() reads hand-edited values tolerantly and empty blocks are pruned on unset. skald config learns features.<name> keys with -p NAME scoping and --unset; completion offers the keys and true/false. SPEC 2.3 documents the layer, DECISIONS D66 records machine-local-only. Verified: 173 tests (added UserConfig resolution/coercion units, CLI, and completion cases), ruff clean, skald check ok. No consumer yet (that is f9e295); no committed project default by decision.
