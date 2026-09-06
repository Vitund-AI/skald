"""``skald render``: a committed, point-in-time snapshot of the board.

Markdown by default, because GitHub renders it in place and relative links
to story files work there. The output is deterministic and carries a
content hash instead of a timestamp so that re-rendering an unchanged
backlog produces no diff and ``check`` can tell when it is stale.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
from pathlib import Path
from typing import Optional

from .store import Store, Story, facets as compute_facets

MARKER_RE = re.compile(r"<!--\s*skald-render\s+([0-9a-f]{16})\s*-->")
DEFAULT_PATH = ".skald/README.md"
DEFAULT_HTML_PATH = ".skald/board.html"
FORMATS = ("md", "html")


def content_hash(store: Store, stories: list[Story]) -> str:
    """Hash of everything the snapshot shows, so unchanged backlogs render identically."""
    h = hashlib.sha1()
    h.update(json.dumps([c.to_dict() for c in store.config.columns], sort_keys=True).encode())
    for s in sorted(stories, key=lambda x: x.id):
        d = s.to_dict()
        payload = [s.id, d["title"], d["status"], d["rank"], d["tags"], d["blocked_by"], d.get("assignee", ""),
                   d["checklist"], s.archived]
        h.update(json.dumps(payload, sort_keys=True).encode())
        h.update(b";")
    return h.hexdigest()[:16]


def read_marker(path: Path) -> Optional[str]:
    """The hash embedded in an existing rendered file, or None."""
    try:
        head = path.read_text(encoding="utf-8")[:4096]
    except OSError:
        return None
    m = MARKER_RE.search(head)
    return m.group(1) if m else None


def _bar(done: int, total: int, width: int = 10) -> str:
    if not total:
        return "▱" * width
    filled = int(round(width * done / total))
    return "▰" * filled + "▱" * (width - filled)


def _rel_link(story: Story, out_dir: Path) -> str:
    try:
        rel = os.path.relpath(story.path, out_dir)
    except ValueError:
        rel = str(story.path)
    return Path(rel).as_posix()


def _md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


class Rendering:
    """Everything both formats need, computed once."""

    def __init__(self, store: Store, out_path: Path, include_archived: bool = False):
        self.store = store
        self.out_path = Path(out_path)
        stories, self.warnings = store.load_all(include_archived=include_archived)
        self.stories = stories
        self.idx = {s.id: s for s in stories}
        self.hash = content_hash(store, stories)
        self.facets = compute_facets(stories, store.config)
        self.columns = list(store.config.columns)
        known = {c.key for c in self.columns}
        self.orphans = [s for s in stories if s.status not in known]
        self.archived = [s for s in stories if s.archived]

    def in_column(self, key: str) -> list[Story]:
        return [s for s in self.stories if s.status == key and not s.archived]

    def open_count(self) -> int:
        return sum(1 for s in self.stories if not s.archived and not self.store.config.is_terminal(s.status))


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------


def render_markdown(store: Store, out_path: Path, include_archived: bool = False) -> str:
    r = Rendering(store, out_path, include_archived)
    cfg = store.config
    out_dir = r.out_path.parent
    lines = [f"<!-- skald-render {r.hash} -->", f"# {cfg.name} backlog", ""]
    counts = " · ".join(f"{c.label} {len(r.in_column(c.key))}" for c in r.columns)
    lines.append(f"**{r.open_count()} open** · {counts}")
    lines.append("")
    lines.append("Rendered by [Skald](https://github.com/Vitund-AI/skald) from the story files in this directory. "
                 "Regenerate with `skald render`.")
    lines.append("")

    epics = r.facets.get("epic")
    if epics:
        lines += ["## Epics", "", "| Epic | Progress | Done | Open |", "| --- | --- | ---: | ---: |"]
        for name, b in epics.items():
            pct = int(round(100 * b["done"] / b["total"])) if b["total"] else 0
            lines.append(f"| `epic:{_md_cell(name)}` | {_bar(b['done'], b['total'])} {pct}% | {b['done']} | {b['open']} |")
        lines.append("")

    def table(stories: list[Story]) -> list[str]:
        rows = ["| ID | Title | Tags | Assignee | Blocked by | Progress |", "| --- | --- | --- | --- | --- | --- |"]
        for s in stories:
            unmet = store.unmet(s, r.idx)
            blocked = ("🔒 " if unmet else "") + ", ".join(f"`{b}`" for b in s.blocked_by) if s.blocked_by else ""
            tags = " ".join(f"`{t}`" for t in s.tags)
            done, total = s.to_dict()["checklist"].values()
            progress = f"{done}/{total}" if total else ""
            link = f"[{s.id}]({_rel_link(s, out_dir)})"
            rows.append(f"| {link} | {_md_cell(s.title)} | {tags} | {_md_cell(s.assignee)} | {blocked} | {progress} |")
        return rows

    for c in r.columns:
        stories = r.in_column(c.key)
        heading = f"{c.label} ({len(stories)}{'/' + str(c.limit) if c.limit else ''})"
        if cfg.is_terminal(c.key):
            lines += [f"<details><summary><strong>{html.escape(heading, quote=False)}</strong></summary>", ""]
            lines += table(stories) if stories else ["_none_"]
            lines += ["", "</details>", ""]
        else:
            lines += [f"## {heading}", ""]
            lines += table(stories) if stories else ["_none_"]
            lines.append("")
    if r.orphans:
        lines += ["## Unknown status", ""] + table(r.orphans) + [""]
    if include_archived and r.archived:
        lines += [f"<details><summary><strong>Archived ({len(r.archived)})</strong></summary>", ""]
        lines += table(r.archived) + ["", "</details>", ""]
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------

_CSS = """
body{font:14px/1.4 system-ui,sans-serif;margin:0;background:#f1f5f9;color:#1e293b}
header{padding:12px 16px;background:#fff;border-bottom:1px solid #e2e8f0}
h1{font-size:18px;margin:0 0 4px}.muted{color:#64748b;font-size:12px}
.board{display:flex;gap:12px;padding:12px;overflow-x:auto;align-items:flex-start}
.col{background:#e2e8f0;border-radius:8px;min-width:260px;max-width:260px;flex:0 0 auto}
.col h2{font-size:13px;margin:0;padding:8px 12px;color:#475569;display:flex;justify-content:space-between}
.col.terminal{opacity:.8}.cards{padding:0 8px 8px;display:flex;flex-direction:column;gap:8px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:8px 10px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.card.blocked{border-left:4px solid #ef4444}.title{font-weight:500}
.tag{display:inline-block;background:#f1f5f9;color:#475569;border-radius:999px;padding:1px 8px;font-size:11px;margin:4px 4px 0 0}
.foot{display:flex;justify-content:space-between;font-family:ui-monospace,monospace;font-size:11px;color:#94a3b8;margin-top:6px}
.epics{padding:8px 16px;display:flex;gap:16px;flex-wrap:wrap}.epic{font-size:12px}
.bar{display:inline-block;width:90px;height:6px;background:#e2e8f0;border-radius:3px;overflow:hidden;vertical-align:middle;margin:0 6px}
.bar span{display:block;height:100%;background:#10b981}
a{color:inherit;text-decoration:none}a:hover{text-decoration:underline}
"""


def render_html(store: Store, out_path: Path, include_archived: bool = False) -> str:
    r = Rendering(store, out_path, include_archived)
    cfg = store.config
    out_dir = r.out_path.parent
    e = html.escape
    parts = [f"<!doctype html>\n<!-- skald-render {r.hash} -->\n<html lang=\"en\"><head><meta charset=\"utf-8\">",
             f"<title>{e(cfg.name)} backlog</title><style>{_CSS}</style></head><body>",
             f"<header><h1>{e(cfg.name)} backlog</h1><div class=\"muted\">{r.open_count()} open · rendered by Skald, regenerate with <code>skald render</code></div>"]
    epics = r.facets.get("epic")
    if epics:
        parts.append("<div class=\"epics\">")
        for name, b in epics.items():
            pct = int(round(100 * b["done"] / b["total"])) if b["total"] else 0
            parts.append(f"<span class=\"epic\">epic:{e(name)}<span class=\"bar\"><span style=\"width:{pct}%\"></span></span>{b['done']}/{b['total']}</span>")
        parts.append("</div>")
    parts.append("</header><div class=\"board\">")
    cols = [(c.label, c.key, c.limit, cfg.is_terminal(c.key), r.in_column(c.key)) for c in r.columns]
    if r.orphans:
        cols.append(("Unknown status", None, None, False, r.orphans))
    if include_archived and r.archived:
        cols.append(("Archived", None, None, True, r.archived))
    for label, key, limit, terminal, stories in cols:
        count = f"{len(stories)}/{limit}" if limit else str(len(stories))
        parts.append(f"<section class=\"col{' terminal' if terminal else ''}\"><h2><span>{e(label)}</span><span>{count}</span></h2><div class=\"cards\">")
        for s in stories:
            unmet = store.unmet(s, r.idx)
            done, total = s.to_dict()["checklist"].values()
            tags = "".join(f"<span class=\"tag\">{e(t)}</span>" for t in s.tags)
            meta = []
            if unmet:
                meta.append("🔒 " + e(", ".join(unmet)))
            if total:
                meta.append(f"{done}/{total}")
            if s.assignee:
                meta.append("@" + e(s.assignee))
            parts.append(f"<a class=\"card{' blocked' if unmet else ''}\" href=\"{e(_rel_link(s, out_dir))}\">"
                         f"<div class=\"title\">{e(s.title)}</div>{tags}"
                         f"<div class=\"foot\"><span>{s.id}</span><span>{' · '.join(meta)}</span></div></a>")
        parts.append("</div></section>")
    parts.append("</div></body></html>\n")
    return "".join(parts)


def render(store: Store, fmt: str, out_path: Path, include_archived: bool = False) -> str:
    if fmt == "html":
        return render_html(store, out_path, include_archived)
    if fmt == "md":
        return render_markdown(store, out_path, include_archived)
    raise ValueError(f"unknown format {fmt!r}")


# --------------------------------------------------------------------------
# Configuration helpers
# --------------------------------------------------------------------------


def render_settings(store: Store) -> Optional[dict]:
    """The project's ``render`` setting from config.json, normalised, or None."""
    raw = store.config.extra.get("render")
    if not raw:
        return None
    if isinstance(raw, str):
        raw = {"path": raw}
    if not isinstance(raw, dict):
        return None
    fmt = raw.get("format") or ("html" if str(raw.get("path", "")).endswith(".html") else "md")
    path = raw.get("path") or (DEFAULT_HTML_PATH if fmt == "html" else DEFAULT_PATH)
    return {"path": path, "format": fmt if fmt in FORMATS else "md", "archived": bool(raw.get("archived", False))}


def stale_message(store: Store, repo_root: Optional[Path]) -> Optional[str]:
    """A warning if the configured (or default) rendered file exists and is out of date."""
    settings = render_settings(store)
    base = repo_root or store.dir.parent
    candidates = [settings["path"]] if settings else [DEFAULT_PATH]
    for rel in candidates:
        path = base / rel
        marker = read_marker(path)
        if marker is None:
            continue
        stories, _ = store.load_all(include_archived=bool(settings and settings["archived"]))
        if marker != content_hash(store, stories):
            return f"{rel} is out of date; run `skald render`"
    return None
