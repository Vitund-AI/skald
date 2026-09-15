---
title: "Open story in Claude Code from the card detail view"
status: "review"
rank: 10
tags: ["area:board", "epic:feature-flags"]
blocked_by: ["716fe0"]
assignee: "claude"
created_at: "2026-09-14T23:47:04Z"
updated_at: "2026-09-15T01:57:33Z"
---
## Requirements

An "Open in Claude Code" action on the card **detail modal** (not on the
column cards, to keep the board uncluttered) that opens the story as a Claude
Code web session, with the repo preselected and a prompt prefilled.

Deep-link (confirmed against code.claude.com/docs):

```
https://claude.ai/code?repositories=<owner>/<repo>&prompt=<url-encoded>
```

- `repositories` (alias `repo`) preselects the GitHub repo by `owner/repo`.
- `prompt` (alias `q`) prefills the composer; it is NOT auto-submitted, so the
  user reviews before running — good safety posture.

The prompt stays short and lets the cloud session self-serve context from the
checkout, rather than stuffing the body into the URL:

> Pick up Skald story `<id>` — "<title>". Run `skald show <id>` for the full
> card, claim it (`skald claim <id> --as claude`), and work it following
> `.skald/AGENTS.md`.

## Scope

- `gitutil.py`: `github_slug(repo) -> "owner/repo" | None`, parsing the origin
  remote in both `git@github.com:owner/repo(.git)` and
  `https://github.com/owner/repo(.git)` forms (and ssh:// / trailing slash).
  None when there is no GitHub origin.
- Server: include `repo_slug` in the board/story payload for a project.
- Board detail modal: when `repo_slug` is present AND the `claude_code_link`
  feature flag (story 716fe0) resolves true for this project, render the
  button linking to the deep link with the URL-encoded prompt. Hidden when no
  GitHub remote or the flag is off. Opens in a new tab; rel="noopener".
- Register `claude_code_link` in `FEATURE_DEFAULTS` (default true) — harmless,
  since the button only appears when a GitHub remote exists.

## Dependencies

Needs the feature-flag layer (716fe0) for the gating flag. The settings modal
(0341fc) is NOT required — the flag defaults on and is hand-editable / settable
via `skald config` — but the two ship well together.

## Acceptance
- [x] github_slug parses ssh, https, ssh://, and trailing-.git / slash forms; None otherwise
- [x] repo_slug exposed in the board payload
- [x] detail modal shows "Open in Claude Code" only when slug present and flag on
- [x] deep link has repositories + url-encoded prompt referencing the story; new tab, noopener
- [x] prompt does not embed the full body; instructs `skald show` + AGENTS.md
- [x] unit tests for github_slug; server/board coverage for the gated button
- [x] docs/board.md documents the action and the flag
- [x] python3 -m unittest green, ruff clean

## Changelog

The board card detail view can open a story directly in Claude Code on the
web, with the repository preselected and a prompt prefilled, when the project
has a GitHub remote. Toggle it with the `claude_code_link` setting.

## [claude] 2026-09-15 01:57 UTC · handoff
Built the Open in Claude Code action. gitutil.github_slug(repo) parses owner/repo from a GitHub origin (git@, https, ssh://, user@, trailing .git or slash; None for non-github or no origin). Server: repo_slug in the board payload (editable and read-only), via _repo_slug. Board: an accent link in the detail modal action row, shown only when repo_slug is set and the claude_code_link flag resolves on (hidden on new-story and when off); it opens claude.ai/code?repositories=<slug>&prompt=<encoded> in a new tab (rel=noopener). The prompt is short — story id + title, then skald show / claim / .skald/AGENTS.md — never the body; claude.ai does not auto-submit it. Verified in a live browser: button shows with a github origin + flag on, URL well-formed (slash preserved), hides after toggling the flag off. Tests: test_gitutil (form matrix) + TestRepoSlug (board payload); 178 total, ruff clean. Docs: board.md story-dialog + Settings, SPEC 8.
