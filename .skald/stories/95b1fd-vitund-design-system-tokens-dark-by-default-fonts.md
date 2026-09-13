---
title: "Vitund design system: tokens, dark by default, fonts, a theme override file"
status: "review"
rank: 50
tags: ["board"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-13T18:25:53Z"
updated_at: "2026-09-13T18:38:12Z"
---
## Requirements

- [x] the board's tokens carry the Vitund palette: the surface ladder (page, column, card, hover step up by lightness), indigo accent, semantic success/warning/danger/info with tint and text variants, quiet borders, radii 4/8/12, no card shadows; light theme for parity
- [x] every raw Tailwind palette class routes through a semantic token, so the whole board is themable from one block
- [x] Inter and JetBrains Mono from Google Fonts with the system stacks as fallback; dark is the default theme, the toggle still offers light and auto
- [x] GET /theme.css serves SKALD_HOME/theme.css when present (empty otherwise) and the page loads it after its defaults
- [x] docs/board.md theme section, board screenshots retaken, CHANGELOG, a DECISIONS entry

## [agent] 2026-09-13 18:38 UTC · result
Tokens on :root (dark) and :root[data-theme=light] from the design system's colors_and_type.css: canvas/column/surface/chip/hover ladder, line and line-strong, ink/muted/faint, accent and success/warning/danger/info each with hover or text and tint variants, plus the graph's role fills. Tailwind config maps them to colour names, sets Inter and JetBrains Mono, radii 4/8/12, and shadows to none; every raw palette class (amber, violet, red, emerald, sky, blue) now routes through a token and the dark: variants are gone. Dark is the default in the bootstrap; the toggle cycles dark, light, auto. Google Fonts link with system fallbacks. GET /theme.css serves SKALD_HOME/theme.css when it exists and an empty stylesheet otherwise, linked after the page's own styles; server test covers both. docs/board.md Theme section with the token table and an example override, SPEC section 8, CHANGELOG, D64. capture.py now sets the theme through localStorage and can serve fonts from disk; README shows board-dark.png and swaps to light through <picture>; the offline asset copies are gitignored.
