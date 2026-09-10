---
title: "Install from GitHub until the first PyPI release"
status: "done"
rank: 270
tags: ["docs", "packaging"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-08T01:16:16Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

PyPI publishing waits for more dogfooding. README, the agent contract, the skill, SPEC, CHANGELOG, and the generated GitHub workflow install from git+https://github.com/Vitund-AI/skald.git instead. The distribution name stays skald-kanban so the switch to PyPI later is a one-line change (INSTALL_SPEC in cli.py).

## Changelog

Skald is not on PyPI yet. The README, contract, skill, and generated workflow install from `git+https://github.com/Vitund-AI/skald.git`; the distribution is named `skald-kanban`, the command is `skald`.
