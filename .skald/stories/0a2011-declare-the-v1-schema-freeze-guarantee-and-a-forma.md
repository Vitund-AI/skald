---
title: "Declare the v1 schema-freeze guarantee and a format-migration contract (skald migrate)"
status: "idea"
rank: 60
tags: ["area:docs", "roadmap"]
blocked_by: []
created_at: "2026-09-20T00:58:52Z"
updated_at: "2026-09-20T00:58:52Z"
---
## Requirements

v1 means the data contract is stable. config.json already carries a format integer (FORMAT=1) and refuses a newer format with 'upgrade skald-kanban' (config.py). Missing: an explicit freeze statement and a migration promise.

- The v1 guarantee (docs): state in SPEC/README that the story file format — Markdown body + JSON-literal frontmatter, the filename-as-id rule, config.json shape — is frozen for the v1.x line; additive, backward-compatible changes only.
- The migration commitment (docs): promise that any format bump (v2.x) ships an automatic, lossless 'skald migrate' that upgrades a repo in place and is idempotent, so historical backlogs are never orphaned. Note the forward-guard already protects an older skald from a newer repo.
- Optional near-term anchor: a 'skald migrate' command that at FORMAT 1 is a no-op — validates and reports 'already at the current format' — so the contract has a real entry point and CI can exercise it before format 2 exists.

Mostly docs/policy; the command stub is small. Confirm the current format guard wording in config.py before writing.
