---
title: "Install from GitHub until the first PyPI release"
status: "review"
rank: 240
tags: ["docs", "packaging"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-08T01:16:16Z"
updated_at: "2026-09-08T17:24:21Z"
---
## Requirements

PyPI publishing waits for more dogfooding. README, the agent contract, the skill, SPEC, CHANGELOG, and the generated GitHub workflow install from git+https://github.com/Vitund-AI/skald.git instead. The distribution name stays skald-kanban so the switch to PyPI later is a one-line change (INSTALL_SPEC in cli.py).
