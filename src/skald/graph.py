"""Dependency graphs: Mermaid for GitHub, DOT for everything else, JSON for the board."""
from __future__ import annotations

import json
from typing import Optional

from .store import Story, split_ref


def build_graph(store, stories: list[Story], include_isolated: bool = False) -> dict:
    """Nodes and edges for the dependency graph of ``stories``.

    Only stories with at least one edge appear unless ``include_isolated``.
    Cross-project targets become nodes of their own, marked ``external``.
    """
    idx = {s.id: s for s in stories}
    cfg = store.config
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    for s in stories:
        for ref in s.blocked_by:
            project, sid = split_ref(ref)
            local = project is None or project == store.name
            key = sid if local else ref
            target = idx.get(sid) if local else None
            if local:
                state = target.status if target else "missing"
                if key not in nodes:
                    nodes[key] = {"id": key, "title": target.title if target else "(missing)", "status": state,
                                  "role": cfg.role(state) or "unknown", "external": False, "archived": bool(target and target.archived)}
            else:
                other = store.workspace.open(project) if getattr(store, "workspace", None) else None
                t = other.get_or_none(sid) if other else None
                state = t.status if t else "unavailable"
                role = other.config.role(t.status) if (other and t) else "unknown"
                if key not in nodes:
                    nodes[key] = {"id": key, "title": t.title if t else f"(in {project})", "status": state,
                                  "role": role or "unknown", "external": True, "archived": bool(t and t.archived)}
            if s.id not in nodes:
                nodes[s.id] = {"id": s.id, "title": s.title, "status": s.status, "role": cfg.role(s.status) or "unknown",
                               "external": False, "archived": s.archived}
            terminal = nodes[key]["role"] in ("done", "closed")
            edges.append({"from": key, "to": s.id, "satisfied": terminal, "external": not local,
                          "missing": state in ("missing", "unavailable")})
    if include_isolated:
        for s in stories:
            nodes.setdefault(s.id, {"id": s.id, "title": s.title, "status": s.status, "role": cfg.role(s.status) or "unknown",
                                    "external": False, "archived": s.archived})
    # cycles: an edge whose target can reach its source
    adj: dict[str, list[str]] = {}
    for e in edges:
        adj.setdefault(e["from"], []).append(e["to"])

    def reaches(src: str, dst: str, seen: set) -> bool:
        if src == dst:
            return True
        for nxt in adj.get(src, []):
            if nxt not in seen:
                seen.add(nxt)
                if reaches(nxt, dst, seen):
                    return True
        return False

    for e in edges:
        e["cycle"] = reaches(e["to"], e["from"], set())
    order = sorted(nodes.values(), key=lambda n: (n["external"], n["id"]))
    return {"project": store.name, "nodes": order, "edges": edges}


def _short(title: str, limit: int = 40) -> str:
    return title if len(title) <= limit else title[: limit - 1] + "…"


def _mermaid_id(key: str) -> str:
    return "n_" + key.replace(":", "__").replace("-", "_")


def to_mermaid(graph: dict) -> str:
    lines = ["flowchart LR"]
    for n in graph["nodes"]:
        label = f"{n['id']}<br/>{_short(n['title']).replace(chr(34), '&quot;')}"
        shape = f'[/"{label}"/]' if n["external"] else f'["{label}"]'
        lines.append(f"    {_mermaid_id(n['id'])}{shape}")
    for e in graph["edges"]:
        arrow = "-.->" if e["external"] else "-->"
        if e["cycle"]:
            arrow = "==>"
        lines.append(f"    {_mermaid_id(e['from'])} {arrow} {_mermaid_id(e['to'])}")
    styles = {
        "backlog": "fill:#f1f5f9,stroke:#94a3b8,color:#1e293b",
        "ready": "fill:#dbeafe,stroke:#60a5fa,color:#1e293b",
        "active": "fill:#fef3c7,stroke:#f59e0b,color:#1e293b",
        "done": "fill:#d1fae5,stroke:#34d399,color:#475569",
        "closed": "fill:#e5e7eb,stroke:#9ca3af,color:#6b7280",
        "unknown": "fill:#fee2e2,stroke:#ef4444,color:#7f1d1d",
    }
    used = {n["role"] for n in graph["nodes"]}
    for role, style in styles.items():
        if role in used:
            lines.append(f"    classDef {role} {style}")
    for role in used:
        members = ",".join(_mermaid_id(n["id"]) for n in graph["nodes"] if n["role"] == role)
        if members:
            lines.append(f"    class {members} {role}")
    return "\n".join(lines) + "\n"


def to_dot(graph: dict) -> str:
    colours = {"backlog": "#f1f5f9", "ready": "#dbeafe", "active": "#fef3c7", "done": "#d1fae5", "closed": "#e5e7eb", "unknown": "#fee2e2"}
    lines = [f'digraph "{graph["project"]}" {{', "    rankdir=LR;", '    node [shape=box, style="rounded,filled", fontname="Helvetica"];']
    for n in graph["nodes"]:
        label = f"{n['id']}\\n{_short(n['title'])}".replace('"', '\\"')
        extra = ', style="rounded,filled,dashed"' if n["external"] else ""
        lines.append(f'    "{n["id"]}" [label="{label}", fillcolor="{colours.get(n["role"], "#fff")}"{extra}];')
    for e in graph["edges"]:
        attrs = []
        if e["external"]:
            attrs.append("style=dashed")
        if e["cycle"]:
            attrs.append('color="#ef4444"')
        if not e["satisfied"]:
            attrs.append("penwidth=1.5")
        lines.append(f'    "{e["from"]}" -> "{e["to"]}"' + (f' [{", ".join(attrs)}]' if attrs else "") + ";")
    lines.append("}")
    return "\n".join(lines) + "\n"


def to_json(graph: dict) -> str:
    return json.dumps(graph, indent=2)


def render_as(graph: dict, fmt: str) -> str:
    if fmt == "mermaid":
        return to_mermaid(graph)
    if fmt == "dot":
        return to_dot(graph)
    if fmt == "json":
        return to_json(graph)
    raise ValueError(f"unknown graph format {fmt!r}")
