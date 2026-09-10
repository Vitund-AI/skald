---
title: "Render workflow commits as github-actions[bot], not a real user's noreply address"
status: "review"
rank: 300
tags: ["git", "packaging"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-09T23:04:27Z"
updated_at: "2026-09-09T23:05:41Z"
---
## Requirements

The workflow written by skald hooks github --install commits the rendered board as skald <skald@users.noreply.github.com>. GitHub maps USERNAME@users.noreply.github.com to the account with that username, so an unrelated GitHub user named skald is credited as a contributor on every repository that installs the workflow. Commit as github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>, the identity GitHub attributes to the Actions bot.

## Changelog

The workflow written by `skald hooks github --install` commits the rendered board as `github-actions[bot]`. It used to commit as `skald@users.noreply.github.com`, an address GitHub attributes to the unrelated account named `skald`; re-run the install to update an existing workflow.

## Acceptance
- [x] The template in cli.py and the committed .github/workflows/skald.yml use the Actions bot identity
- [x] CHANGELOG entry; troubleshooting note on how to fix an installed workflow

## [claude] 2026-09-09 23:05 UTC · result
Both the template in cli.py and the committed .github/workflows/skald.yml now commit as github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>. Test asserts the identity and the absence of the old address. CHANGELOG Fixed entry and a troubleshooting note added. The three existing render commits on main keep their attribution unless history is rewritten.
