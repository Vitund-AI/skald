---
title: "Dependency graph: Mermaid in render, skald graph, SVG on the board"
status: "done"
rank: 210
tags: ["docs", "ui"]
blocked_by: []
assignee: "claude"
created_at: "2026-09-06T19:01:43Z"
updated_at: "2026-09-10T00:56:04Z"
---
## Requirements

Only stories with dependencies appear. Mermaid block in the rendered snapshot (GitHub draws it), skald graph --format mermaid|dot|json, and a layered inline-SVG graph toggle on the board with click-to-open.

## Changelog

The dependency graph is drawn three ways: a Mermaid block in the rendered snapshot that GitHub draws, `skald graph --format mermaid|dot|json`, and a layered SVG on the board (`g`) with click-to-open. Only stories with a dependency appear.

## [claude] 2026-09-06 19:12 UTC
Implemented: graph.py builds nodes and edges with cycle detection; skald graph emits Mermaid, DOT, or JSON; render embeds a Mermaid block (collapsed above 25 nodes); the board has a Graph toggle (g) drawing a layered inline SVG with click-to-open, verified in Chromium (D37).
