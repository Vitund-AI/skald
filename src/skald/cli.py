"""The ``skald`` command (also reachable as ``git skald``)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from . import __version__, gitutil
from .config import ProjectConfig, slugify_name
from .errors import GitError, NotFoundError, SkaldError
from .registry import Registry, UserConfig, Workspace, find_skald_dir
from .store import Store, Story, serialise_story, split_ref
from .util import read_text

OLD_ALIAS = "!python3 .skald/skald.py"


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------


def cli_identity(explicit: Optional[str] = None) -> str:
    """Who is acting from the command line. Agents are the default caller."""
    if explicit and explicit.strip():
        return explicit.strip()
    env = os.environ.get("SKALD_AUTHOR", "").strip()
    return env or "agent"


def human_identity(user: UserConfig, repo: Optional[Path]) -> str:
    """Who is acting from the board: env, then user config, then git, then 'human'."""
    env = os.environ.get("SKALD_AUTHOR", "").strip()
    if env:
        return env
    configured = (user.get("author") or "").strip()
    if configured:
        return configured
    if repo:
        name = gitutil.user_name(repo)
        if name:
            return name
    return "human"


# --------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------


def _warn(warnings) -> None:
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)


def _notice(lines) -> None:
    for line in lines:
        print(f"NOTE: {line}", file=sys.stderr)


def _print_table(rows: list[list[str]], headers: list[str]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row[:-1]):
            widths[i] = max(widths[i], len(cell))
    fmt = "  ".join("{:<%d}" % w for w in widths[:-1]) + "  {}"
    print(fmt.format(*headers))
    for row in rows:
        print(fmt.format(*row))


def _story_rows(store: Store, stories: list[Story], idx, qualify: bool = False) -> list[list[str]]:
    rows = []
    for s in stories:
        unmet = store.unmet(s, idx)
        sid = f"{store.name}:{s.id}" if qualify else s.id
        rows.append([sid, s.status, str(s.rank), ",".join(unmet) or "-", s.assignee or "-", ",".join(s.tags) or "-", s.title])
    return rows


STORY_HEADERS = ["ID", "STATUS", "RANK", "BLOCKED", "ASSIGNEE", "TAGS", "TITLE"]


def _read_text_arg(value: Optional[str]) -> str:
    if value == "-":
        return sys.stdin.read()
    return value or ""


def _parse_plus_minus(args: list[str], what: str) -> tuple[list[str], list[str]]:
    add, remove = [], []
    for a in args:
        if a.startswith("+") and len(a) > 1:
            add.append(a[1:])
        elif a.startswith("-") and len(a) > 1:
            remove.append(a[1:])
        else:
            raise SkaldError(f"expected +{what} or -{what}, got '{a}'")
    if not add and not remove:
        raise SkaldError(f"nothing to do: give at least one +{what} or -{what}")
    return add, remove


def _repo_of(store: Store) -> Optional[Path]:
    return gitutil.root(store.dir)


def _skald_rel(store: Store, repo: Path) -> str:
    return str(store.dir.relative_to(repo)) if store.dir.is_relative_to(repo) else str(store.dir)


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="skald", description="Kanban lite for coding agents.")
    p.add_argument("--version", action="version", version=f"skald {__version__}")
    p.add_argument("-p", "--project", metavar="NAME", help="act on a registered project instead of the current directory")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    init = sub.add_parser("init", help="create .skald/ here (or register an existing one)")
    init.add_argument("--name", help="project name (default: the directory name)")

    ls = sub.add_parser("ls", help="list stories")
    ls.add_argument("--status", metavar="COLUMN")
    ls.add_argument("--tag")
    ls.add_argument("--assignee")
    ls.add_argument("--unblocked", action="store_true", help="only stories with no unmet dependencies")
    ls.add_argument("--all", action="store_true", help="include done and closed stories")
    ls.add_argument("--archived", action="store_true", help="include archived stories")
    ls.add_argument("--all-projects", action="store_true", help="every registered project")
    ls.add_argument("--branch", metavar="REF", help="read stories from a git ref instead of the working tree")
    ls.add_argument("--all-branches", action="store_true", help="stories that exist only on, or differ on, other branches")
    ls.add_argument("--json", action="store_true")
    ls.add_argument("--compact", action="store_true", help="with --json: only the fields an agent needs")

    nx = sub.add_parser("next", help="the story to pick up next")
    nx.add_argument("--as", dest="author", help="skip stories assigned to someone else")
    nx.add_argument("--all-projects", action="store_true")
    nx.add_argument("--json", action="store_true")
    nx.add_argument("--compact", action="store_true")

    cx = sub.add_parser("context", help="one orientation block for an agent: mine, next, blockers, uncommitted")
    cx.add_argument("--as", dest="author", help="whose assignments to show (default: agent)")
    cx.add_argument("--json", action="store_true")

    rs = sub.add_parser("resume", help="requirements, checklist state, dependencies, and the latest handoff for a story")
    rs.add_argument("id")
    rs.add_argument("--json", action="store_true")

    sh = sub.add_parser("show", help="print a story file")
    sh.add_argument("id")
    sh.add_argument("--branch", metavar="REF", help="read the story from a git ref")
    sh.add_argument("--json", action="store_true")

    br = sub.add_parser("branches", help="story counts per branch and how they differ from the working tree")
    br.add_argument("--json", action="store_true")

    new = sub.add_parser("new", help="create a story")
    new.add_argument("title")
    new.add_argument("--status", metavar="COLUMN")
    new.add_argument("--tags", default="", help="comma-separated")
    new.add_argument("--blocked-by", default="", help="comma-separated ids, or project:id")
    new.add_argument("--body", default="", help="requirements text, or - to read stdin")
    new.add_argument("--template", help="a template from .skald/templates/")
    new.add_argument("--assignee", default="")
    new.add_argument("--json", action="store_true")

    mv = sub.add_parser("mv", help="change a story's status")
    mv.add_argument("id")
    mv.add_argument("status", metavar="COLUMN")

    cl = sub.add_parser("claim", help="assign a story to yourself and start it")
    cl.add_argument("id")
    cl.add_argument("--as", dest="author")

    st = sub.add_parser("set", help="set title=..., rank=N, or assignee=NAME")
    st.add_argument("id")
    st.add_argument("assignments", nargs="+", metavar="key=value")

    sub.add_parser("tag", help="tag <id> +tag -tag ...")
    sub.add_parser("block", help="block <id> +id -id ... (project:id for other projects)")

    note = sub.add_parser("note", help="append a note to a story")
    note.add_argument("id")
    note.add_argument("text", help="note text, or - to read stdin")
    note.add_argument("--as", dest="author", help="author label (default: agent)")
    note.add_argument("--kind", help="handoff, decision, blocker, or any short word; shown in the heading")

    rm = sub.add_parser("rm", help="delete a story")
    rm.add_argument("id")
    rm.add_argument("--force", action="store_true")

    lg = sub.add_parser("log", help="git history of a story")
    lg.add_argument("id")
    lg.add_argument("--json", action="store_true")

    ar = sub.add_parser("archive", help="move done and closed stories to .skald/archive/")
    ar.add_argument("--dry-run", action="store_true")
    ua = sub.add_parser("unarchive", help="move a story back out of the archive")
    ua.add_argument("id")

    ck = sub.add_parser("check", help="validate every story file")
    ck.add_argument("--json", action="store_true")
    ck.add_argument("--hook", action="store_true", help="also fail on uncommitted story changes (for agent stop hooks)")

    stt = sub.add_parser("status", help="project summary: branch, counts, uncommitted story changes")
    stt.add_argument("--json", action="store_true")

    cm = sub.add_parser("commit", help="commit everything under .skald/ with Skald-Story trailers")
    cm.add_argument("-m", "--message")
    cm.add_argument("--push", action="store_true")
    cm.add_argument("--no-trailers", action="store_true")

    cmts = sub.add_parser("commits", help="commits that reference a story (Skald-Story trailer or [id])")
    cmts.add_argument("id")
    cmts.add_argument("--all-branches", action="store_true")
    cmts.add_argument("--json", action="store_true")

    df = sub.add_parser("diff", help="backlog changes between two git refs")
    df.add_argument("--since", required=True, metavar="REF")
    df.add_argument("--until", default=None, metavar="REF", help="default: the working tree")
    df.add_argument("--markdown", action="store_true")
    df.add_argument("--json", action="store_true")

    act = sub.add_parser("activity", help="every backlog event in git history, oldest first")
    act.add_argument("--since", metavar="REF", help="default: 20 commits back")
    act.add_argument("--until", default="HEAD", metavar="REF")
    act.add_argument("--json", action="store_true")

    chg = sub.add_parser("changelog", help="stories completed between two git refs")
    chg.add_argument("--since", required=True, metavar="REF")
    chg.add_argument("--until", default="HEAD", metavar="REF")
    chg.add_argument("--json", action="store_true")

    sub.add_parser("columns", help="list this project's columns").add_argument("--json", action="store_true")
    fc = sub.add_parser("facets", help="key:value tags with progress, e.g. epic:auth")
    fc.add_argument("key", nargs="?", help="only this facet key")
    fc.add_argument("--all-projects", action="store_true")
    fc.add_argument("--json", action="store_true")
    ep = sub.add_parser("epics", help="shorthand for: facets epic")
    ep.add_argument("--all-projects", action="store_true")
    ep.add_argument("--json", action="store_true")
    sub.add_parser("templates", help="list story templates in .skald/templates/")

    pr = sub.add_parser("projects", help="list projects registered on this machine")
    pr.add_argument("--json", action="store_true")
    prs = pr.add_subparsers(dest="projects_cmd")
    prm = prs.add_parser("rm", help="forget a project (files are untouched)")
    prm.add_argument("name")

    cf = sub.add_parser("config", help="get or set a user setting")
    cf.add_argument("key", nargs="?")
    cf.add_argument("value", nargs="?")
    cf.add_argument("--unset", action="store_true")

    hk = sub.add_parser("hooks", help="print or install hooks: claude (agent), git (pre-commit), github (workflow)")
    hk.add_argument("target", choices=["claude", "git", "github"])
    hk.add_argument("--install", action="store_true", help="write the hook instead of printing it")
    hk.add_argument("--strict", action="store_true", help="claude: stop hook also fails on uncommitted story changes")

    rd = sub.add_parser("render", help="write a Markdown or HTML snapshot of the board to commit")
    rd.add_argument("--format", choices=["md", "html"], help="default: from config.json, else md")
    rd.add_argument("--out", metavar="PATH", help="default: from config.json, else .skald/README.md")
    rd.add_argument("--archived", action="store_true", help="include archived stories")
    rd.add_argument("--stage", action="store_true", help="git add the output afterwards")
    rd.add_argument("--stdout", action="store_true", help="print instead of writing")
    rd.add_argument("--enable", action="store_true", help="also record the path in config.json so commit and hooks re-render automatically")

    sv = sub.add_parser("serve", help="run the board in the foreground")
    sv.add_argument("--host")
    sv.add_argument("--port", type=int)
    sv.add_argument("--open", action="store_true")

    srv = sub.add_parser("server", help="manage the background board server")
    srvs = srv.add_subparsers(dest="server_cmd")
    ss = srvs.add_parser("start")
    ss.add_argument("--host")
    ss.add_argument("--port", type=int)
    srvs.add_parser("stop")
    srvs.add_parser("status")

    sub.add_parser("open", help="start the server if needed and open the board for this project")
    sub.add_parser("mcp", help="serve the store as MCP tools over stdio (for agents without a shell)")

    return p


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def cmd_init(ws: Workspace, args) -> int:
    cwd = Path.cwd().resolve()
    repo = gitutil.root(cwd)
    existing = find_skald_dir(cwd)
    if existing is not None:
        skald_dir = existing
    else:
        skald_dir = (repo or cwd) / ".skald"
    created = not (skald_dir / "stories").is_dir()
    (skald_dir / "stories").mkdir(parents=True, exist_ok=True)
    keep = skald_dir / "stories" / ".gitkeep"
    if not keep.exists():
        keep.write_text("")
    lines = [f"{'created' if created else 'found'} {skald_dir}"]

    cfg_path = skald_dir / "config.json"
    if cfg_path.exists():
        config = ProjectConfig.load(cfg_path)
        if args.name and args.name != config.name:
            config.name = slugify_name(args.name)
            config.save(cfg_path)
            lines.append(f"renamed project to '{config.name}' in {cfg_path.name}")
        else:
            lines.append(f"kept {cfg_path.name} (project '{config.name}')")
    else:
        name = slugify_name(args.name) if args.name else slugify_name(skald_dir.parent.name)
        config = ProjectConfig(name)
        config.save(cfg_path)
        lines.append(f"wrote {cfg_path.name} (project '{name}', columns: {config.describe()})")

    agents = skald_dir / "AGENTS.md"
    if agents.exists():
        lines.append("kept existing AGENTS.md")
    else:
        agents.write_text(agents_template(), encoding="utf-8")
        lines.append("wrote AGENTS.md")

    legacy = skald_dir / "skald.py"
    if legacy.exists():
        legacy.unlink()
        lines.append("removed vendored skald.py from the 0.1 layout (the package replaces it)")
    if repo:
        alias = gitutil.get_alias(repo, "skald")
        if alias == OLD_ALIAS:
            gitutil.unset_alias(repo, "skald")
            lines.append("removed the 0.1 git alias; `git skald` now uses the installed git-skald command")

    notice = ws.registry.register(config.name, skald_dir)
    lines.append(notice or f"project '{config.name}' already registered")
    lines.append("")
    lines.append("Add this line to your repository's CLAUDE.md or AGENTS.md:")
    lines.append("  This repository tracks work with Skald. Read .skald/AGENTS.md before starting any task.")
    lines.append("Then commit .skald/ and run `skald open` to see the board.")
    for line in lines:
        print(line)
    return 0


def _filtered(store: Store, args, stories, idx):
    rows = stories
    if args.status:
        rows = [s for s in rows if s.status == args.status]
    elif not args.all:
        rows = [s for s in rows if not store.config.is_terminal(s.status)]
    if args.tag:
        tag = args.tag.strip().lower()
        rows = [s for s in rows if tag in s.tags]
    if getattr(args, "assignee", None):
        rows = [s for s in rows if s.assignee == args.assignee]
    if args.unblocked:
        rows = [s for s in rows if not store.unmet(s, idx)]
    return rows


def cmd_ls(ws: Workspace, args, store: Optional[Store]) -> int:
    if args.all_projects:
        stores, warnings = ws.open_all()
        _warn(warnings)
    else:
        stores = [store]
    rows, dicts = [], []
    for st in stores:
        stories, load_warnings = st.load_all(include_archived=args.archived)
        _warn(load_warnings)
        idx = {s.id: s for s in stories}
        sel = _filtered(st, args, stories, idx)
        rows.extend(_story_rows(st, sel, idx, qualify=args.all_projects))
        dicts.extend(st.story_dict(s, idx, ws.user.get("stale_days"), compact=args.compact) for s in sel)
    if args.json:
        print(json.dumps(dicts, indent=2))
    else:
        _print_table(rows, STORY_HEADERS)
    return 0


def cmd_next(ws: Workspace, args, store: Optional[Store]) -> int:
    author = cli_identity(args.author)
    stores = ws.open_all()[0] if args.all_projects else [store]
    stale_days = ws.user.get("stale_days")
    for st in stores:
        notes: list[str] = []
        s = st.next_story(for_author=author, stale_days=stale_days, elsewhere=st.claims_elsewhere(), warnings=notes)
        _warn(notes)
        if s:
            if args.json:
                print(json.dumps(st.story_dict(s, compact=args.compact), indent=2))
            else:
                _print_table(_story_rows(st, [s], None, qualify=args.all_projects), STORY_HEADERS)
            return 0
    print("no ready, unblocked stories", file=sys.stderr)
    return 1


def cmd_branches(store: Store, args) -> int:
    repo = _repo_of(store)
    if repo is None:
        raise GitError(f"{store.dir} is not inside a git repository")
    current = gitutil.branch(repo)
    rows, dicts = [], []
    for b in gitutil.branches(repo):
        snap = store.snapshot(b["name"])
        diff = store.branch_diff(snap)
        is_current = b["name"] == current
        d = {
            "name": b["name"], "sha": b["sha"][:7], "remote": b["remote"], "current": is_current,
            "stories": len(snap.load_all(include_archived=True)[0]),
            "only_there": [x.id for x in diff["only_there"]],
            "only_here": [x.id for x in diff["only_here"]],
            "differ": [x.id for x, _ in diff["differ"]],
        }
        dicts.append(d)
        rows.append(["*" if is_current else "", b["name"], str(d["stories"]), str(len(d["only_there"])),
                     str(len(d["only_here"])), str(len(d["differ"]))])
    if args.json:
        print(json.dumps(dicts, indent=2))
    else:
        _print_table(rows, ["", "BRANCH", "STORIES", "ONLY THERE", "ONLY HERE", "DIFFER"])
        print("(* = checked out; counts compare each branch with the working tree)")
    return 0


def cmd_ls_branches(ws: Workspace, store: Store, args) -> int:
    repo = _repo_of(store)
    if repo is None:
        raise GitError(f"{store.dir} is not inside a git repository")
    current = gitutil.branch(repo)
    rows, dicts = [], []
    for b in gitutil.branches(repo):
        if b["name"] == current:
            continue
        snap = store.snapshot(b["name"])
        diff = store.branch_diff(snap)
        for s in diff["only_there"]:
            rows.append([b["name"], s.id, s.status, "-", s.title])
            d = snap.story_dict(s)
            d["here"] = None
            dicts.append(d)
        for here, there in diff["differ"]:
            rows.append([b["name"], there.id, there.status, here.status, there.title])
            d = snap.story_dict(there)
            d["here"] = here.status
            dicts.append(d)
    if args.json:
        print(json.dumps(dicts, indent=2))
    elif rows:
        _print_table(rows, ["BRANCH", "ID", "STATUS", "HERE", "TITLE"])
    else:
        print("no stories differ from the working tree on any other branch")
    return 0


def _note_line(n: Optional[dict]) -> str:
    if not n:
        return ""
    first = n["text"].strip().splitlines()[0] if n["text"].strip() else ""
    kind = f" ({n['kind']})" if n["kind"] != "note" else ""
    return f"{n['stamp']} [{n['author']}]{kind} {first}"


def build_context(ws: Workspace, store: Store, author: str) -> dict:
    stories, load_warnings = store.load_all()
    idx = {s.id: s for s in stories}
    repo, uncommitted = _uncommitted(store)
    mine = [s for s in stories if s.assignee == author and not store.config.is_terminal(s.status)]
    elsewhere = store.claims_elsewhere()
    stale_days = ws.user.get("stale_days")
    next_notes: list[str] = []
    nxt = store.next_story(for_author=author, stale_days=stale_days, elsewhere=elsewhere, warnings=next_notes)
    ready_blocked = [s for s in stories if store.config.role(s.status) == "ready" and store.unmet(s, idx)]
    from .store import _is_stale

    stale_claims = [s for s in stories if s.assignee and s.assignee != author
                    and store.config.role(s.status) == "active" and _is_stale(s, stale_days)]

    def entry(s: Story) -> dict:
        d = store.story_dict(s, idx, ws.user.get("stale_days"), compact=True)
        last = s.last_note()
        d["last_note"] = _note_line(last)
        handoff = s.last_note("handoff")
        d["has_handoff"] = handoff is not None
        return d

    return {
        "project": store.name,
        "branch": gitutil.branch(repo) if repo else None,
        "author": author,
        "mine": [entry(s) for s in mine],
        "next": entry(nxt) if nxt else None,
        "ready_blocked": [{"id": s.id, "title": s.title, "unmet": store.unmet(s, idx)} for s in ready_blocked],
        "stale_claims": [{"id": s.id, "title": s.title, "assignee": s.assignee, "status": s.status, "updated_at": s.updated_at}
                         for s in stale_claims],
        "claimed_elsewhere": elsewhere,
        "uncommitted": [c["path"] for c in uncommitted],
        "warnings": load_warnings + next_notes,
    }


def cmd_context(ws: Workspace, store: Store, args) -> int:
    author = cli_identity(args.author)
    ctx = build_context(ws, store, author)
    if args.json:
        print(json.dumps(ctx, indent=2))
        return 0
    print(f"project {ctx['project']}" + (f" · branch {ctx['branch']}" if ctx["branch"] else "") + f" · acting as {author}")
    if ctx["mine"]:
        print(f"\nAssigned to {author}:")
        for d in ctx["mine"]:
            cl = f"  checklist {d['checklist']['done']}/{d['checklist']['total']}" if d["checklist"]["total"] else ""
            ac = f"  acceptance {d['acceptance']['done']}/{d['acceptance']['total']}" if d.get("acceptance") else ""
            flags = ("  BLOCKED" if d["blocked"] else "") + ("  stale" if d.get("stale") else "")
            print(f"  {d['id']}  {d['status']:<12} {d['title']}{cl}{ac}{flags}")
            if d["last_note"]:
                print(f"          last note: {d['last_note']}")
            if d["has_handoff"]:
                print(f"          run: skald resume {d['id']}")
    else:
        print(f"\nNothing assigned to {author}.")
    if ctx["next"]:
        n = ctx["next"]
        print(f"\nNext: {n['id']}  {n['title']}   (skald claim {n['id']} --as {author})")
    else:
        print("\nNext: nothing ready and unblocked.")
    if ctx["ready_blocked"]:
        print("\nReady but blocked:")
        for b in ctx["ready_blocked"]:
            print(f"  {b['id']}  {b['title']}  waiting on {', '.join(b['unmet'])}")
    if ctx["stale_claims"]:
        print(f"\nStale claims (no update for {ws.user.get('stale_days')}+ days; take over with skald claim <id>):")
        for c in ctx["stale_claims"]:
            print(f"  {c['id']}  {c['status']:<12} {c['title']}  ({c['assignee']}, {c['updated_at'][:10]})")
    if ctx["claimed_elsewhere"]:
        print("\nClaimed on other branches:")
        for sid, claims in ctx["claimed_elsewhere"].items():
            print(f"  {sid}  " + "; ".join(f"{c['assignee']} on {c['branch']} ({c['status']})" for c in claims))
    if ctx["uncommitted"]:
        print(f"\nUncommitted story files: {len(ctx['uncommitted'])} (commit them with your code)")
    _warn(ctx["warnings"])
    return 0


def cmd_resume(ws: Workspace, store: Store, args) -> int:
    from .store import requirements_of

    story = store.get(args.id)
    idx = store.index()
    d = store.story_dict(story, idx, ws.user.get("stale_days"), compact=True)
    notes = story.notes()
    handoff = story.last_note("handoff")
    latest = handoff or (notes[-1] if notes else None)
    d["requirements"] = requirements_of(story.body)
    d["deps"] = [x.to_dict() for x in store.dep_states(story, idx)]
    d["latest"] = latest
    d["note_count"] = len(notes)
    d["decisions"] = [n for n in notes if n["kind"] == "decision"]
    d["blockers"] = [n for n in notes if n["kind"] == "blocker"]
    if args.json:
        print(json.dumps(d, indent=2))
        return 0
    print(f"{story.id}  {story.title}")
    print(f"status {story.status}" + (f" · assignee {story.assignee}" if story.assignee else "")
          + (f" · checklist {d['checklist']['done']}/{d['checklist']['total']}" if d["checklist"]["total"] else "")
          + (f" · acceptance {d['acceptance']['done']}/{d['acceptance']['total']}" if d.get("acceptance") else ""))
    if d["deps"]:
        print("depends on: " + ", ".join(f"{x['ref']} ({x['state']}{'' if x['satisfied'] else ', unmet'})" for x in d["deps"]))
    print("\n" + d["requirements"].strip() + "\n")
    if d["decisions"]:
        print("Decisions:")
        for n in d["decisions"]:
            print(f"  - {n['stamp']} [{n['author']}] {n['text'].strip().splitlines()[0]}")
        print()
    if latest:
        label = "Latest handoff" if handoff else "Latest note"
        others = len(notes) - 1
        print(f"{label} ({latest['stamp']}, {latest['author']}){f', {others} earlier note(s) in the file' if others > 0 else ''}:")
        print(latest["text"].rstrip())
    else:
        print("No notes yet.")
    return 0


def cmd_show(ws: Workspace, args, store: Store) -> int:
    if getattr(args, "branch", None):
        store = store.snapshot(args.branch)
    story = store.get(args.id)
    if args.json:
        d = store.story_dict(story, None, ws.user.get("stale_days"))
        d["body"] = story.body
        d["body_sha256"] = store.body_sha(story)
        print(json.dumps(d, indent=2))
    else:
        sys.stdout.write(serialise_story(story.fields, story.body))
    return 0


def cmd_new(ws: Workspace, args, store: Store) -> int:
    tags = [t for t in args.tags.split(",") if t.strip()]
    blockers = [b for b in args.blocked_by.split(",") if b.strip()]
    body = _read_text_arg(args.body)
    story, warnings = store.create(args.title, args.status, tags, blockers, body, args.assignee, args.template)
    _warn(warnings)
    if args.json:
        print(json.dumps(store.story_dict(story), indent=2))
    else:
        print(story.id)
    return 0


def cmd_tag_block(store: Store, argv: list[str]) -> int:
    if len(argv) < 2:
        raise SkaldError(f"usage: skald {argv[0]} <id> +item -item ...")
    ref, rest = argv[1], argv[2:]
    story = store.get(ref)
    if argv[0] == "tag":
        add, remove = _parse_plus_minus(rest, "tag")
        from .store import normalise_tags

        tags = set(story.tags) | set(normalise_tags(add))
        tags -= set(normalise_tags(remove))
        story, warnings = store.update(story.id, tags=sorted(tags))
        _warn(warnings)
        print(f"{story.id} tags: {', '.join(story.tags) or '-'}")
    else:
        add, remove = _parse_plus_minus(rest, "id")
        current = set(story.blocked_by)
        for r in remove:
            project, sid = split_ref(r.lower())
            if project is None or project == store.name:
                current.discard(store.resolve(sid))
            else:
                current.discard(r.lower())
        story, warnings = store.update(story.id, blocked_by=sorted(current | set(a.lower() for a in add)))
        _warn(warnings)
        print(f"{story.id} blocked_by: {', '.join(story.blocked_by) or '-'}")
    return 0


def cmd_set(store: Store, args) -> int:
    kwargs = {}
    for a in args.assignments:
        if "=" not in a:
            raise SkaldError(f"expected key=value, got '{a}'")
        key, value = a.split("=", 1)
        key = key.strip()
        if key == "title":
            kwargs["title"] = value
        elif key == "rank":
            try:
                kwargs["rank"] = int(value)
            except ValueError:
                raise SkaldError(f"rank must be an integer, got '{value}'") from None
        elif key == "assignee":
            kwargs["assignee"] = value
        else:
            raise SkaldError(f"cannot set '{key}' (use mv, tag, or block for status, tags, blocked_by)")
    story, warnings = store.update(args.id, **kwargs)
    _warn(warnings)
    print(f"updated {story.id}")
    return 0


def cmd_log(store: Store, args) -> int:
    story = store.get(args.id)
    repo = _repo_of(store)
    if repo is None:
        raise GitError(f"{store.dir} is not inside a git repository")
    entries = gitutil.log_file(repo, story.path)
    if args.json:
        print(json.dumps(entries, indent=2))
    else:
        if not entries:
            print(f"{story.id} has no commits yet")
        for e in entries:
            print(f"{e['sha']}  {e['date'][:16].replace('T', ' ')}  {e['author']:<20}  {e['subject']}")
    return 0


def _uncommitted(store: Store) -> tuple[Optional[Path], list[dict]]:
    repo = _repo_of(store)
    if repo is None:
        return None, []
    try:
        return repo, gitutil.changes(repo, _skald_rel(store, repo))
    except GitError:
        return repo, []


def cmd_check(store: Store, args) -> int:
    from . import render as rnd

    problems, warnings = store.check()
    stale = rnd.stale_message(store, _repo_of(store))
    if stale:
        warnings.append(stale)
    uncommitted = []
    if args.hook:
        _, uncommitted = _uncommitted(store)
    if args.json:
        print(json.dumps({"ok": not problems and not uncommitted, "problems": problems, "warnings": warnings,
                          "uncommitted": [c["path"] for c in uncommitted]}, indent=2))
    else:
        for w in warnings:
            print(f"WARNING: {w}", file=sys.stderr)
        for pr in problems:
            print(f"PROBLEM: {pr}")
        if uncommitted:
            print(f"PROBLEM: {len(uncommitted)} uncommitted story file(s) under .skald/: "
                  + ", ".join(c["path"] for c in uncommitted[:5])
                  + (" ..." if len(uncommitted) > 5 else "")
                  + ". Commit them together with the code they describe.")
        if not problems and not uncommitted:
            print("ok")
    return 2 if (problems or uncommitted) else 0


def cmd_status(ws: Workspace, store: Store, args) -> int:
    repo, uncommitted = _uncommitted(store)
    stories, load_warnings = store.load_all()
    idx = {s.id: s for s in stories}
    counts = {c.key: 0 for c in store.config.columns}
    unknown = 0
    for s in stories:
        if s.status in counts:
            counts[s.status] += 1
        else:
            unknown += 1
    ready = [s for s in stories if store.config.role(s.status) == "ready" and not store.unmet(s, idx)]
    info = {
        "project": store.name,
        "path": str(store.dir),
        "branch": gitutil.branch(repo) if repo else None,
        "counts": counts,
        "unknown_status": unknown,
        "ready_unblocked": len(ready),
        "uncommitted": [c["path"] for c in uncommitted],
        "warnings": load_warnings,
    }
    if args.json:
        print(json.dumps(info, indent=2))
        return 0
    print(f"project:  {store.name}  ({store.dir})")
    if info["branch"]:
        print(f"branch:   {info['branch']}")
    print("columns:  " + "  ".join(f"{k}={v}" for k, v in counts.items()) + (f"  unknown={unknown}" if unknown else ""))
    print(f"ready and unblocked: {len(ready)}")
    if uncommitted:
        print(f"uncommitted story changes: {len(uncommitted)} file(s) under .skald/")
    else:
        print("uncommitted story changes: none")
    _warn(load_warnings)
    return 0


def story_ids_in(changes: list[dict]) -> list[str]:
    from .store import id_from_filename

    ids = set()
    for c in changes:
        parts = c["path"].replace("\\", "/").split("/")
        if len(parts) >= 2 and parts[-2] in ("stories", "archive"):
            sid = id_from_filename(parts[-1])
            if sid:
                ids.add(sid)
    return sorted(ids)


def with_trailers(message: str, ids: list[str]) -> str:
    missing = [i for i in ids if f"{gitutil.TRAILER}: {i}" not in message]
    if not missing:
        return message
    return message.rstrip("\n") + "\n\n" + "\n".join(f"{gitutil.TRAILER}: {i}" for i in missing) + "\n"


def cmd_commits(store: Store, args) -> int:
    story = store.get(args.id)
    repo = _repo_of(store)
    if repo is None:
        raise GitError(f"{store.dir} is not inside a git repository")
    entries = gitutil.commits_for(repo, story.id, all_branches=args.all_branches)
    if args.json:
        print(json.dumps(entries, indent=2))
        return 0
    if not entries:
        print(f"no commits reference {story.id} (add a '{gitutil.TRAILER}: {story.id}' trailer or [{story.id}] to commit messages)")
        return 0
    for e in entries:
        print(f"{e['sha']}  {e['date'][:16].replace('T', ' ')}  {e['author']:<20}  {e['subject']}")
    return 0


def _describe_change(c: dict) -> list[str]:
    bits = []
    for k, (x, y) in c["fields"].items():
        if k == "archived":
            bits.append("archived" if y else "unarchived")
        elif k in ("tags", "blocked_by"):
            bits.append(f"{k} {', '.join(x) or '-'} -> {', '.join(y) or '-'}")
        else:
            bits.append(f"{k} {x or '-'} -> {y or '-'}")
    if c["notes_added"]:
        bits.append(f"+{c['notes_added']} note(s)")
    if c["body_changed"]:
        bits.append("body edited")
    return bits


def cmd_diff(store: Store, args) -> int:
    from .store import diff_states

    repo = _repo_of(store)
    if repo is None:
        raise GitError(f"{store.dir} is not inside a git repository")
    base = store.snapshot(args.since)
    head = store.snapshot(args.until) if args.until else store
    d = diff_states(base, head)
    until_label = args.until or "working tree"
    if args.json:
        out = {
            "since": args.since, "until": until_label,
            "added": [s.to_dict(compact=True) for s in d["added"]],
            "removed": [s.to_dict(compact=True) for s in d["removed"]],
            "changed": [{"id": c["story"].id, "title": c["story"].title,
                         "fields": {k: list(v) for k, v in c["fields"].items()},
                         "notes_added": c["notes_added"], "body_changed": c["body_changed"]} for c in d["changed"]],
        }
        print(json.dumps(out, indent=2))
        return 0
    total = len(d["added"]) + len(d["removed"]) + len(d["changed"])
    if args.markdown:
        print("<!-- skald-diff -->")
        print(f"## Backlog changes ({args.since} → {until_label})\n")
        if not total:
            print("No story changes.")
            return 0
        if d["added"]:
            print("**New**\n")
            for s in d["added"]:
                print(f"- `{s.id}` {s.title} ({s.status})")
            print()
        if d["changed"]:
            print("**Changed**\n")
            for c in d["changed"]:
                print(f"- `{c['story'].id}` {c['story'].title}: {'; '.join(_describe_change(c))}")
            print()
        if d["removed"]:
            print("**Removed**\n")
            for s in d["removed"]:
                print(f"- `{s.id}` {s.title}")
            print()
        return 0
    if not total:
        print(f"no story changes between {args.since} and {until_label}")
        return 0
    for s in d["added"]:
        print(f"+ {s.id}  {s.status:<12} {s.title}")
    for c in d["changed"]:
        print(f"~ {c['story'].id}  {c['story'].title}: {'; '.join(_describe_change(c))}")
    for s in d["removed"]:
        print(f"- {s.id}  {s.title}")
    return 0


def cmd_activity(store: Store, args) -> int:
    from .store import diff_states

    repo = _repo_of(store)
    if repo is None:
        raise GitError(f"{store.dir} is not inside a git repository")
    since = args.since
    if since is None:
        since = f"{args.until}~20" if gitutil.rev_parse(repo, f"{args.until}~20") else None
    rel = _skald_rel(store, repo)
    commits = gitutil.commits_touching(repo, since, args.until, rel)
    events = []
    for c in commits:
        parent = gitutil.parent_of(repo, c["full"])
        head = store.snapshot(c["full"])
        base = store.snapshot(parent) if parent else None
        d = diff_states(base, head)
        for s in d["added"]:
            events.append({**c, "id": s.id, "title": s.title, "event": f"created ({s.status})"})
        for ch in d["changed"]:
            for bit in _describe_change(ch):
                events.append({**c, "id": ch["story"].id, "title": ch["story"].title, "event": bit})
        for s in d["removed"]:
            events.append({**c, "id": s.id, "title": s.title, "event": "deleted"})
    if args.json:
        print(json.dumps([{k: v for k, v in e.items() if k != "full"} for e in events], indent=2))
        return 0
    if not events:
        print("no backlog activity in that range")
        return 0
    last = None
    for e in events:
        if e["sha"] != last:
            print(f"{e['sha']}  {e['date'][:16].replace('T', ' ')}  {e['author']}  {e['subject']}")
            last = e["sha"]
        print(f"    {e['id']}  {e['event']}  ({e['title']})")
    return 0


def cmd_commit(ws: Workspace, store: Store, args) -> int:
    repo = _repo_of(store)
    if repo is None:
        raise GitError(f"{store.dir} is not inside a git repository")
    rel = _skald_rel(store, repo)
    rendered = auto_render(store, repo)
    paths = [rel] + ([rendered] if rendered and not rendered.startswith(rel + "/") else [])
    changes = [c for p in paths for c in gitutil.changes(repo, p)]
    if not changes:
        print("nothing to commit under .skald/")
        return 0
    message = args.message or f"skald: update {len(changes)} story file(s)"
    if not args.no_trailers:
        message = with_trailers(message, story_ids_in(changes))
    sha = gitutil.commit_path(repo, paths, message)
    print(f"committed {sha}: {message}")
    if args.push or ws.user.get("push"):
        out = gitutil.push(repo)
        print(out or "pushed")
    return 0


def _parse_at(repo: Path, ref: str, rel: str):
    from .store import parse_story_text

    text = gitutil.show(repo, ref, rel)
    if text is None:
        return None
    try:
        fields, _ = parse_story_text(text, rel)
    except SkaldError:
        return None
    return fields


def cmd_changelog(store: Store, args) -> int:
    repo = _repo_of(store)
    if repo is None:
        raise GitError(f"{store.dir} is not inside a git repository")
    for ref in (args.since, args.until):
        if gitutil.rev_parse(repo, ref) is None:
            raise GitError(f"unknown git ref '{ref}'")
    rel = _skald_rel(store, repo)
    paths = set(gitutil.ls_tree(repo, args.until, f"{rel}/stories")) | set(gitutil.ls_tree(repo, args.until, f"{rel}/archive"))
    done = []
    for path in sorted(paths):
        now = _parse_at(repo, args.until, path)
        if not now or not store.config.is_terminal(now["status"]):
            continue
        sid = Path(path).name[:6]
        before = None
        for candidate in (path, path.replace(f"{rel}/archive/", f"{rel}/stories/"), path.replace(f"{rel}/stories/", f"{rel}/archive/")):
            before = _parse_at(repo, args.since, candidate)
            if before:
                break
        if before and store.config.is_terminal(before["status"]):
            continue
        done.append({"id": sid, "title": now["title"], "status": now["status"], "tags": now.get("tags", [])})
    if args.json:
        print(json.dumps(done, indent=2))
        return 0
    print(f"## Completed between {args.since} and {args.until}\n")
    if not done:
        print("(nothing)")
    for d in done:
        tags = f" [{', '.join(d['tags'])}]" if d["tags"] else ""
        closed = " (closed)" if store.config.is_closed(d["status"]) else ""
        print(f"- {d['title']} ({d['id']}){tags}{closed}")
    return 0


def cmd_projects(ws: Workspace, args) -> int:
    if args.projects_cmd == "rm":
        ws.registry.remove(args.name)
        print(f"forgot project '{args.name}' (files untouched)")
        return 0
    entries = ws.registry.entries()
    if args.json:
        print(json.dumps(entries, indent=2))
        return 0
    if not entries:
        print("no projects registered; run `skald init` inside a repository")
        return 0
    rows = [[e["name"], "ok" if e["exists"] else "missing", e["path"]] for e in entries]
    _print_table(rows, ["NAME", "STATE", "PATH"])
    return 0


def cmd_config(ws: Workspace, args) -> int:
    user = ws.user
    if args.key is None:
        for k, v in user.all().items():
            print(f"{k} = {json.dumps(v)}")
        print(f"(stored in {user.path})")
        return 0
    if args.unset:
        user.unset(args.key)
        print(f"unset {args.key}")
        return 0
    if args.value is None:
        print(json.dumps(user.get(args.key)))
        return 0
    user.set(args.key, args.value)
    print(f"{args.key} = {json.dumps(user.get(args.key))}")
    return 0


def cmd_facets(ws: Workspace, store: Optional[Store], args, key: Optional[str]) -> int:
    from .store import facets as compute_facets

    stores = ws.open_all()[0] if args.all_projects else [store]
    merged: dict = {}
    for st in stores:
        stories, _ = st.load_all(include_archived=True)
        for k, values in compute_facets(stories, st.config).items():
            if key and k != key:
                continue
            for v, b in values.items():
                m = merged.setdefault(k, {}).setdefault(v, {"total": 0, "done": 0, "open": 0, "ids": []})
                m["total"] += b["total"]
                m["done"] += b["done"]
                m["open"] += b["open"]
                m["ids"].extend(f"{st.name}:{i}" if args.all_projects else i for i in b["ids"])
    if args.json:
        print(json.dumps(merged, indent=2))
        return 0
    if not merged:
        print(f"no {key + ' ' if key else ''}facet tags; tag stories like {key or 'epic'}:name to create one")
        return 0
    rows = []
    for k in sorted(merged):
        for v in sorted(merged[k]):
            b = merged[k][v]
            pct = int(round(100 * b["done"] / b["total"])) if b["total"] else 0
            rows.append([k, v, str(b["total"]), str(b["done"]), str(b["open"]), f"{pct}%"])
    _print_table(rows, ["KEY", "VALUE", "TOTAL", "DONE", "OPEN", "PROGRESS"])
    return 0


def cmd_columns(store: Store, args) -> int:
    if args.json:
        print(json.dumps([c.to_dict() for c in store.config.columns], indent=2))
        return 0
    rows = [[c.key, c.label, c.role, str(c.limit) if c.limit else "-"] for c in store.config.columns]
    _print_table(rows, ["KEY", "LABEL", "ROLE", "LIMIT"])
    return 0


def claude_hooks(strict: bool) -> dict:
    stop = "skald check --hook" if strict else "skald check"
    return {
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "skald status && skald ls"}]}],
            "Stop": [{"hooks": [{"type": "command", "command": stop}]}],
        }
    }


def do_render(store: Store, fmt: Optional[str] = None, out: Optional[str] = None, archived: Optional[bool] = None,
              repo: Optional[Path] = None) -> tuple[Path, str]:
    """Render to the resolved path. Returns (absolute path, text). Does not write when out is '-'."""
    from . import render as rnd

    settings = rnd.render_settings(store) or {}
    fmt = fmt or settings.get("format") or "md"
    rel = out or settings.get("path") or (rnd.DEFAULT_HTML_PATH if fmt == "html" else rnd.DEFAULT_PATH)
    base = repo or _repo_of(store) or store.dir.parent
    path = (base / rel).resolve() if not Path(rel).is_absolute() else Path(rel)
    include_archived = settings.get("archived", False) if archived is None else archived
    text = rnd.render(store, fmt, path, include_archived)
    return path, text


def auto_render(store: Store, repo: Path) -> Optional[str]:
    """If config.json enables rendering, re-render and return the repo-relative path written."""
    from . import render as rnd
    from .util import atomic_write

    settings = rnd.render_settings(store)
    if not settings:
        return None
    path, text = do_render(store, repo=repo)
    atomic_write(path, text)
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return str(path)


def cmd_render(store: Store, args) -> int:
    from . import render as rnd
    from .util import atomic_write

    repo = _repo_of(store)
    path, text = do_render(store, args.format, args.out, True if args.archived else None, repo)
    if args.stdout:
        sys.stdout.write(text)
        return 0
    atomic_write(path, text)
    base = repo or store.dir.parent
    try:
        rel = path.relative_to(base).as_posix()
    except ValueError:
        rel = str(path)
    print(f"rendered {rel}")
    if args.enable:
        fmt = args.format or (rnd.render_settings(store) or {}).get("format") or ("html" if rel.endswith(".html") else "md")
        store.config.extra["render"] = {"path": rel, "format": fmt, **({"archived": True} if args.archived else {})}
        store.config.save(store.dir / "config.json")
        print(f"enabled automatic rendering in {store.dir.name}/config.json (commit re-renders {rel})")
    if args.stage:
        if repo is None:
            raise GitError("--stage needs a git repository")
        gitutil.stage(repo, rel)
        print(f"staged {rel}")
    return 0


PRE_COMMIT_HOOK = """#!/bin/sh
# Installed by `skald hooks git --install`. Validates the backlog and refreshes
# the rendered board before every commit. Remove this file to uninstall.
skald check || exit 1
skald render --stage
"""


def github_workflow(default_branch: str, render_path: str) -> str:
    return f"""name: skald

# Written by `skald hooks github --install`. Validates the backlog on every
# push and pull request, and keeps the rendered board fresh on {default_branch}.

on:
  push:
    branches: [{default_branch}]
  pull_request:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install skald-kanban
      - run: skald check

  diff:
    if: github.event_name == 'pull_request'
    needs: check
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install skald-kanban
      - name: Describe backlog changes in this pull request
        run: skald diff --since "origin/${{{{ github.base_ref }}}}" --until HEAD --markdown > skald-diff.md
      - name: Post or update the comment
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('skald-diff.md', 'utf8');
            const {{ owner, repo }} = context.repo;
            const issue_number = context.issue.number;
            const comments = await github.rest.issues.listComments({{ owner, repo, issue_number, per_page: 100 }});
            const mine = comments.data.find(c => c.body && c.body.startsWith('<!-- skald-diff -->'));
            if (mine) await github.rest.issues.updateComment({{ owner, repo, comment_id: mine.id, body }});
            else await github.rest.issues.createComment({{ owner, repo, issue_number, body }});

  render:
    if: github.event_name == 'push'
    needs: check
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install skald-kanban
      - run: skald render --out {render_path}
      - name: Commit the rendered board if it changed
        run: |
          if ! git diff --quiet -- {render_path}; then
            git config user.name "skald"
            git config user.email "skald@users.noreply.github.com"
            git add -- {render_path}
            git commit -m "skald: refresh rendered board [skip ci]"
            git push
          fi
"""


def cmd_hooks_git(store: Store, args) -> int:
    from . import render as rnd

    repo = _repo_of(store)
    if repo is None:
        raise GitError(f"{store.dir} is not inside a git repository")
    if not args.install:
        print(PRE_COMMIT_HOOK, end="")
        print(f"\nWrite this to {gitutil.hooks_dir(repo) / 'pre-commit'} and make it executable, or rerun with --install.", file=sys.stderr)
        return 0
    hook = gitutil.hooks_dir(repo) / "pre-commit"
    if hook.exists() and "skald" not in hook.read_text(encoding="utf-8", errors="replace"):
        print(f"{hook} already exists and is not Skald's; add these lines to it yourself:", file=sys.stderr)
        print("  skald check || exit 1\n  skald render --stage", file=sys.stderr)
        return 1
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(PRE_COMMIT_HOOK, encoding="utf-8")
    hook.chmod(0o755)
    print(f"installed {hook}")
    if not rnd.render_settings(store):
        store.config.extra["render"] = {"path": rnd.DEFAULT_PATH, "format": "md"}
        store.config.save(store.dir / "config.json")
        print(f"enabled automatic rendering of {rnd.DEFAULT_PATH} in config.json; commit config.json")
    return 0


def cmd_hooks_github(store: Store, args) -> int:
    from . import render as rnd

    repo = _repo_of(store) or store.dir.parent
    settings = rnd.render_settings(store) or {}
    text = github_workflow(gitutil.default_branch(repo) if _repo_of(store) else "main", settings.get("path", rnd.DEFAULT_PATH))
    if not args.install:
        print(text, end="")
        print("\nWrite this to .github/workflows/skald.yml, or rerun with --install.", file=sys.stderr)
        return 0
    path = repo / ".github" / "workflows" / "skald.yml"
    if path.exists():
        print(f"{path} already exists; not overwriting. Printed version:", file=sys.stderr)
        print(text, end="")
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path.relative_to(repo)}")
    if not settings:
        store.config.extra["render"] = {"path": rnd.DEFAULT_PATH, "format": "md"}
        store.config.save(store.dir / "config.json")
        print(f"enabled automatic rendering of {rnd.DEFAULT_PATH} in config.json; commit config.json")
    return 0


def cmd_hooks(store: Store, args) -> int:
    if args.target == "git":
        return cmd_hooks_git(store, args)
    if args.target == "github":
        return cmd_hooks_github(store, args)
    snippet = claude_hooks(args.strict)
    if not args.install:
        print(json.dumps(snippet, indent=2))
        print("\nMerge this into .claude/settings.json, or rerun with --install.", file=sys.stderr)
        return 0
    repo = _repo_of(store) or store.dir.parent
    path = repo / ".claude" / "settings.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            raise SkaldError(f"{path} is not valid JSON ({e})") from None
    hooks = data.setdefault("hooks", {})
    for event, entries in snippet["hooks"].items():
        existing = hooks.setdefault(event, [])
        for entry in entries:
            cmd = entry["hooks"][0]["command"]
            already = any(h.get("command", "").startswith("skald ") for e in existing for h in e.get("hooks", []))
            if already:
                for e in existing:
                    for h in e.get("hooks", []):
                        if h.get("command", "").startswith("skald "):
                            h["command"] = cmd
            else:
                existing.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"installed Skald hooks into {path}")
    return 0


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------

PROJECT_COMMANDS = {
    "ls", "next", "show", "new", "mv", "claim", "set", "tag", "block", "note", "rm", "log",
    "archive", "unarchive", "check", "status", "commit", "changelog", "columns", "templates",
    "hooks", "open", "branches", "facets", "epics", "render", "context", "resume",
    "commits", "diff", "activity",
}


def run(argv: list[str], ws: Optional[Workspace] = None) -> int:
    ws = ws or Workspace()

    # `tag` and `block` take +x/-y arguments that argparse would treat as options.
    if argv and argv[0] in ("tag", "block"):
        store = ws.current()
        _notice(ws.notices)
        return cmd_tag_block(store, argv)
    if len(argv) >= 3 and argv[0] in ("-p", "--project") and argv[2] in ("tag", "block"):
        store = ws.current(argv[1])
        return cmd_tag_block(store, argv[2:])

    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    if args.command == "init":
        return cmd_init(ws, args)
    if args.command == "projects":
        return cmd_projects(ws, args)
    if args.command == "config":
        return cmd_config(ws, args)
    if args.command == "mcp":
        from .mcp import McpServer

        return McpServer(ws).serve()
    if args.command in ("serve", "server", "open"):
        from . import server as srv

        if args.command == "serve":
            return srv.cmd_serve(ws, args)
        if args.command == "open":
            store = ws.current(args.project)
            _notice(ws.notices)
            return srv.cmd_open(ws, store)
        return srv.cmd_server(ws, args)

    store = None
    if args.command in ("ls", "next", "facets", "epics") and getattr(args, "all_projects", False):
        try:
            store = ws.current(args.project)
        except NotFoundError:
            pass
    elif args.command in PROJECT_COMMANDS:
        store = ws.current(args.project)
    _notice(ws.notices)

    if args.command == "ls":
        if args.all_branches:
            return cmd_ls_branches(ws, store, args)
        if args.branch:
            store = store.snapshot(args.branch)
        return cmd_ls(ws, args, store)
    if args.command == "branches":
        return cmd_branches(store, args)
    if args.command == "context":
        return cmd_context(ws, store, args)
    if args.command == "resume":
        return cmd_resume(ws, store, args)
    if args.command == "next":
        return cmd_next(ws, args, store)
    if args.command == "show":
        return cmd_show(ws, args, store)
    if args.command == "new":
        return cmd_new(ws, args, store)
    if args.command == "mv":
        story, warnings = store.update(args.id, status=args.status)
        _warn(warnings)
        print(f"moved {story.id} to {story.status}")
        return 0
    if args.command == "claim":
        story, warnings = store.claim(args.id, cli_identity(args.author), ws.user.get("stale_days"), store.claims_elsewhere())
        _warn(warnings)
        print(f"{story.id} claimed by {story.assignee}, now {story.status}")
        return 0
    if args.command == "set":
        return cmd_set(store, args)
    if args.command == "note":
        story = store.append_note(args.id, _read_text_arg(args.text), cli_identity(args.author), args.kind)
        print(f"noted on {story.id}" + (f" ({args.kind})" if args.kind else ""))
        return 0
    if args.command == "rm":
        story = store.delete(args.id, force=args.force)
        print(f"deleted {story.id} ({story.path.name})")
        return 0
    if args.command == "log":
        return cmd_log(store, args)
    if args.command == "archive":
        moved = store.archive(dry_run=args.dry_run)
        verb = "would archive" if args.dry_run else "archived"
        for s in moved:
            print(f"{verb} {s.id}  {s.title}")
        if not moved:
            print("nothing to archive")
        return 0
    if args.command == "unarchive":
        story = store.unarchive(args.id)
        print(f"unarchived {story.id}")
        return 0
    if args.command == "check":
        return cmd_check(store, args)
    if args.command == "status":
        return cmd_status(ws, store, args)
    if args.command == "commit":
        return cmd_commit(ws, store, args)
    if args.command == "changelog":
        return cmd_changelog(store, args)
    if args.command == "commits":
        return cmd_commits(store, args)
    if args.command == "diff":
        return cmd_diff(store, args)
    if args.command == "activity":
        return cmd_activity(store, args)
    if args.command == "columns":
        return cmd_columns(store, args)
    if args.command == "facets":
        return cmd_facets(ws, store, args, args.key)
    if args.command == "epics":
        return cmd_facets(ws, store, args, "epic")
    if args.command == "templates":
        names = store.templates()
        print("\n".join(names) if names else f"no templates; add Markdown files to {store.templates_dir}")
        return 0
    if args.command == "hooks":
        return cmd_hooks(store, args)
    if args.command == "render":
        return cmd_render(store, args)
    parser.print_help()  # pragma: no cover
    return 1


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        return run(argv)
    except SkaldError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return e.exit_code
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:  # pragma: no cover
        return 0


def agents_template() -> str:
    from importlib import resources

    return resources.files("skald").joinpath("templates/AGENTS.md").read_text(encoding="utf-8")
