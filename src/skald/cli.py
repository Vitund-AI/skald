"""The ``skald`` command (also reachable as ``git skald``)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Optional

from . import __version__, gitutil
from .config import ProjectConfig, slugify_name
from .errors import GitError, NotFoundError, SkaldError
from .registry import Registry, UserConfig, Workspace, find_skald_dir
from .store import Store, Story, serialise_story, split_ref
from .util import read_text



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
        q = len(s.open_questions())
        kids = [k for k in (idx or {}).values() if k.parent == s.id] if idx else []
        title = s.title
        if kids:
            done = sum(1 for k in kids if store.config.is_terminal(k.status))
            title = f"{s.title}  (children {done}/{len(kids)})"
        elif s.parent:
            title = f"{s.title}  (child of {s.parent})"
        rows.append([sid, s.status, str(s.rank), ",".join(unmet) or "-", f"?{q}" if q else "-", s.assignee or "-",
                     ",".join(s.tags) or "-", title])
    return rows


STORY_HEADERS = ["ID", "STATUS", "RANK", "BLOCKED", "Q", "ASSIGNEE", "TAGS", "TITLE"]


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


def command_reference(parser: Optional[argparse.ArgumentParser] = None) -> list[dict]:
    """Every subcommand with its help text and options, read from the parser so it cannot drift.

    Returns ``[{name, help, usage, arguments: [{flags, help, choices}], subcommands: [...]}]``.
    """
    parser = parser or build_parser()

    def describe(p: argparse.ArgumentParser, prefix: str) -> dict:
        args, subs = [], []
        for a in p._actions:
            if isinstance(a, argparse._HelpAction) or a.help == argparse.SUPPRESS:
                continue
            if isinstance(a, argparse._SubParsersAction):
                for name, sp in a.choices.items():
                    subs.append(describe(sp, f"{prefix} {name}"))
                continue
            flags = list(a.option_strings) or [a.metavar or a.dest]
            if a.option_strings and a.nargs != 0:
                flags = [f"{f} {a.metavar or a.dest.upper()}" for f in flags]
            elif not a.option_strings and a.nargs in ("*", "+", "?"):
                flags = [f"[{flags[0]}...]" if a.nargs in ("*", "+") else f"[{flags[0]}]"]
            args.append({
                "flags": flags, "help": a.help or "",
                "choices": [str(c) for c in a.choices] if a.choices else [],
                "positional": not a.option_strings,
            })
        usage = " ".join(p.format_usage().split()).replace("usage: ", "", 1).replace("[-h] ", "").replace(" [-h]", "")
        return {"name": prefix.strip(), "help": p.description or "", "usage": usage, "arguments": args, "subcommands": subs}

    out = []
    for a in parser._actions:
        if isinstance(a, argparse._SubParsersAction):
            helps = {c.dest: c.help for c in a._choices_actions}
            seen = set()
            for name, sp in a.choices.items():
                if id(sp) in seen:  # an alias such as mv for move
                    continue
                seen.add(id(sp))
                d = describe(sp, name)
                d["help"] = helps.get(name) or sp.description or ""
                for sub in d["subcommands"]:
                    sub_helps = {c.dest: c.help for act in sp._actions if isinstance(act, argparse._SubParsersAction) for c in act._choices_actions}
                    sub["help"] = sub_helps.get(sub["name"].split()[-1]) or sub["help"]
                out.append(d)
    return out


DOCS_HEADER = """# CLI reference

Generated by `skald docs` from the same parser as `skald --help`. Do not edit
by hand; run `skald docs` after changing a command.

Any `<id>` accepts a unique prefix. `-p NAME` before a command targets a
registered project instead of the current directory. Commands that print
stories take `--json`. Exit codes: 0 success (warnings on stderr), 1 usage
error or not found, 2 corrupt story or configuration.
"""


def docs_markdown(parser: Optional[argparse.ArgumentParser] = None) -> str:
    """The CLI reference as Markdown, one section per command."""
    out = [DOCS_HEADER]
    commands = command_reference(parser)
    out.append("## Commands\n")
    for c in commands:
        out.append(f"- [`{c['name']}`](#{c['name'].replace(' ', '-')}) {c['help']}")
    out.append("")

    def section(c: dict, level: int) -> None:
        out.append(f"{'#' * level} {c['name']}\n")
        out.append(f"```\n{c['usage']}\n```\n")
        if c["help"]:
            out.append(f"{c['help'][0].upper()}{c['help'][1:]}.\n" if not c["help"].endswith(".") else c["help"] + "\n")
        if c["arguments"]:
            out.append("| Argument | Description |")
            out.append("| --- | --- |")
            for a in c["arguments"]:
                flags = ", ".join(f"`{f}`" for f in a["flags"])
                desc = a["help"] or ""
                if a["choices"]:
                    desc = (desc + " " if desc else "") + "One of: " + ", ".join(f"`{ch}`" for ch in a["choices"]) + "."
                desc = desc.replace("|", "\\|")
                out.append(f"| {flags} | {desc} |")
            out.append("")
        for sub in c["subcommands"]:
            section(sub, level + 1)

    for c in commands:
        section(c, 2)
    return "\n".join(out).rstrip("\n") + "\n"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="skald", description="Kanban lite for coding agents.")
    p.add_argument("--version", action="version", version=f"skald {__version__}")
    p.add_argument("-p", "--project", metavar="NAME", help="act on a registered project instead of the current directory")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    init = sub.add_parser("init", help="create .skald/ here (or register an existing one)")
    init.add_argument("--name", help="project name (default: the directory name)")
    init.add_argument("--columns", choices=["default", "lifecycle"], default="default",
                      help="column set for a new config.json: default (backlog, ready, in_progress, review, done) or lifecycle (idea, plan, ready, in_progress, review, done)")

    ls = sub.add_parser("ls", help="list stories")
    ls.add_argument("--status", metavar="COLUMN", help="only this column")
    ls.add_argument("--tag", help="only stories with this tag (facets such as epic:auth work)")
    ls.add_argument("--assignee", help="only stories assigned to this name")
    ls.add_argument("--unblocked", action="store_true", help="only stories with no unmet dependencies")
    ls.add_argument("--questions", action="store_true", help="only stories with an open question (waiting on a human)")
    ls.add_argument("--parent", metavar="ID", help="only the children of this story")
    ls.add_argument("--all", action="store_true", help="include done and closed stories")
    ls.add_argument("--archived", action="store_true", help="include archived stories")
    ls.add_argument("--release", metavar="VERSION", help="only stories shipped in this version (implies --archived and --all)")
    ls.add_argument("--all-projects", action="store_true", help="every registered project")
    ls.add_argument("--branch", metavar="REF", help="read stories from a git ref instead of the working tree")
    ls.add_argument("--all-branches", action="store_true", help="stories that exist only on, or differ on, other branches")
    ls.add_argument("--json", action="store_true", help="print JSON")
    ls.add_argument("--compact", action="store_true", help="with --json: only the fields an agent needs")

    nx = sub.add_parser("next", help="the story to pick up next")
    nx.add_argument("--as", dest="author", help="skip stories assigned to someone else")
    nx.add_argument("--all-projects", action="store_true", help="every registered project")
    nx.add_argument("--json", action="store_true", help="print JSON")
    nx.add_argument("--compact", action="store_true", help="with --json: only the fields an agent needs")

    cx = sub.add_parser("context", help="one orientation block for an agent: mine, next, blockers, uncommitted")
    cx.add_argument("--as", dest="author", help="whose assignments to show (default: agent)")
    cx.add_argument("--json", action="store_true", help="print JSON")

    rs = sub.add_parser("resume", help="requirements, checklist state, dependencies, and the latest handoff for a story")
    rs.add_argument("id", help="story id or unique prefix")
    rs.add_argument("--section", metavar="NAME", help="print one section of the body instead, matched by prefix (e.g. design)")
    rs.add_argument("--full", action="store_true", help="print the whole body, every section, instead of the requirements")
    rs.add_argument("--json", action="store_true", help="print JSON")

    au = sub.add_parser("audit", help="check a story's cited paths, path:line references, and commit hashes against the tree, and note the result")
    au.add_argument("id", help="story id or unique prefix")
    au.add_argument("--notes", action="store_true", help="also check claims made in notes, not only the body above them")
    au.add_argument("--no-note", action="store_true", help="print the result without appending an audit note")
    au.add_argument("--as", dest="author", help="author label for the audit note (default: agent)")
    au.add_argument("--json", action="store_true", help="print JSON")

    sh = sub.add_parser("show", help="print a story file")
    sh.add_argument("id", help="story id or unique prefix")
    sh.add_argument("--branch", metavar="REF", help="read the story from a git ref")
    sh.add_argument("--json", action="store_true", help="print JSON with derived fields, body, and body hash")

    br = sub.add_parser("branches", help="story counts per branch and how they differ from the working tree")
    br.add_argument("--json", action="store_true", help="print JSON")

    new = sub.add_parser("new", help="create a story")
    new.add_argument("title", help="the story title")
    new.add_argument("--status", metavar="COLUMN", help="starting column (default: the first backlog column)")
    new.add_argument("--tags", default="", help="comma-separated")
    new.add_argument("--blocked-by", default="", help="comma-separated ids, or project:id")
    new.add_argument("--body", default="", help="requirements text, or - to read stdin")
    new.add_argument("--template", help="a template from .skald/templates/")
    new.add_argument("--assignee", default="", help="assign on creation")
    new.add_argument("--parent", metavar="ID", help="make this a child of another story in this project; its facet tags are inherited")
    new.add_argument("--no-inherit", action="store_true", help="with --parent: do not copy the parent's facet tags")
    new.add_argument("--created-at", metavar="WHEN", help="backdate created_at and updated_at: YYYY-MM-DD HH:MM (UTC) or an ISO instant; for migrations, default now")
    new.add_argument("--json", action="store_true", help="print the story as JSON instead of its id")

    mv = sub.add_parser("move", aliases=["mv"], help="move a story to a column")
    mv.add_argument("id", help="story id or unique prefix")
    mv.add_argument("status", metavar="COLUMN", help="a column key from .skald/config.json")

    cl = sub.add_parser("claim", help="assign a story to yourself and start it")
    cl.add_argument("id", help="story id or unique prefix")
    cl.add_argument("--as", dest="author", help="who is claiming (default: agent)")

    st = sub.add_parser("set", help="set title=..., rank=N, assignee=NAME, or parent=ID")
    st.add_argument("id", help="story id or unique prefix")
    st.add_argument("assignments", nargs="+", metavar="key=value", help="title=..., rank=N, assignee=NAME (assignee= clears it), parent=ID (parent=- clears it)")

    sub.add_parser("tag", help="tag <id> +tag -tag ...")
    sub.add_parser("block", help="block <id> +id -id ... (project:id for other projects)")

    note = sub.add_parser("note", help="append a note to a story")
    note.add_argument("id", help="story id or unique prefix")
    note.add_argument("text", help="note text, or - to read stdin")
    note.add_argument("--as", dest="author", help="author label (default: agent)")
    note.add_argument("--kind", help="handoff, decision, blocker, question (open until a later decision), or any short word; shown in the heading")
    note.add_argument("--at", metavar="WHEN", help="backdate the note heading: YYYY-MM-DD HH:MM (UTC) or an ISO instant; for migrations, default now")

    ans = sub.add_parser("answer", help="answer a story's open questions: appends a decision note, which closes them")
    ans.add_argument("id", help="story id or unique prefix")
    ans.add_argument("text", help="the decision, or - to read stdin")
    ans.add_argument("--as", dest="author", help="author label (default: agent)")
    ans.add_argument("--question", type=int, metavar="N", help="close only the Nth open question (1-based, as resume lists them); default: all of them")

    imp = sub.add_parser("import", help="bring a folder of Markdown records into the backlog, driven by a mapping file")
    imp.add_argument("paths", nargs="+", metavar="PATH", help="Markdown files, or directories searched recursively")
    imp.add_argument("--map", metavar="FILE", help="JSON mapping: created_at, status, tags, notes, strip, exclude rules (see docs/importing.md)")
    imp.add_argument("--status", metavar="COLUMN", help="column for every imported story; overrides the mapping's status rules")
    imp.add_argument("--rewrite-links", metavar="ROOT", help="rewrite references to each imported file across ROOT to the new story path")
    imp.add_argument("--rm", action="store_true", help="delete each source file after importing it, so one commit carries removal and creation")
    imp.add_argument("--dry-run", action="store_true", help="print what would be written, per file, and write nothing")
    imp.add_argument("--as", dest="author", help="author label for the extracted notes (default: import)")

    rm = sub.add_parser("rm", help="delete a story")
    rm.add_argument("id", help="story id or unique prefix")
    rm.add_argument("--force", action="store_true", help="delete even if other stories depend on it or are its children; their references are cleared")

    lg = sub.add_parser("log", help="git history of a story")
    lg.add_argument("id", help="story id or unique prefix")
    lg.add_argument("--json", action="store_true", help="print JSON")

    ar = sub.add_parser("archive", help="move done and closed stories to .skald/archive/")
    ar.add_argument("ids", nargs="*", help="only these stories (default: every done or closed story)")
    ar.add_argument("--dry-run", action="store_true", help="list what would move; change nothing")
    ua = sub.add_parser("unarchive", help="move a story back out of the archive")
    ua.add_argument("id", help="story id or unique prefix")

    ck = sub.add_parser("check", help="validate every story file")
    ck.add_argument("--json", action="store_true", help="print JSON")
    ck.add_argument("--hook", action="store_true", help="also fail on uncommitted story changes (for agent stop hooks)")

    stt = sub.add_parser("status", help="project summary: branch, counts, uncommitted story changes")
    stt.add_argument("--json", action="store_true", help="print JSON")

    cm = sub.add_parser("commit", help="commit everything under .skald/ with Skald-Story trailers")
    cm.add_argument("-m", "--message", help="commit message (default: skald: update N story file(s))")
    cm.add_argument("--push", action="store_true", help="push afterwards")
    cm.add_argument("--no-trailers", action="store_true", help="do not add Skald-Story trailers")

    cmts = sub.add_parser("commits", help="commits that reference a story (Skald-Story trailer or [id])")
    cmts.add_argument("id", help="story id or unique prefix")
    cmts.add_argument("--all-branches", action="store_true", help="search every branch, not just the current one")
    cmts.add_argument("--no-children", action="store_true", help="on a parent, do not include commits that reference its children")
    cmts.add_argument("--json", action="store_true", help="print JSON")

    df = sub.add_parser("diff", help="backlog changes between two git refs")
    df.add_argument("--since", required=True, metavar="REF", help="the earlier state: a branch, tag, or commit")
    df.add_argument("--until", default=None, metavar="REF", help="default: the working tree")
    df.add_argument("--markdown", action="store_true", help="Markdown with a <!-- skald-diff --> marker, for pull request comments")
    df.add_argument("--json", action="store_true", help="print JSON")

    act = sub.add_parser("activity", help="every backlog event in git history, oldest first")
    act.add_argument("--since", metavar="REF", help="default: 20 commits back")
    act.add_argument("--until", default="HEAD", metavar="REF", help="default: HEAD")
    act.add_argument("--json", action="store_true", help="print JSON")

    gr = sub.add_parser("graph", help="dependency graph as Mermaid (default), DOT, or JSON")
    gr.add_argument("--format", choices=["mermaid", "dot", "json"], default="mermaid", help="output format")
    gr.add_argument("--all", action="store_true", help="include stories without dependencies")
    gr.add_argument("--archived", action="store_true", help="include archived stories")

    chg = sub.add_parser("changelog", help="stories completed between two git refs")
    chg.add_argument("--since", required=True, metavar="REF", help="the earlier state: a branch, tag, or commit")
    chg.add_argument("--until", default="HEAD", metavar="REF", help="default: HEAD")
    chg.add_argument("--json", action="store_true", help="print JSON")

    sub.add_parser("columns", help="list this project's columns").add_argument("--json", action="store_true", help="print JSON")
    fc = sub.add_parser("facets", help="key:value tags with progress, e.g. epic:auth")
    fc.add_argument("key", nargs="?", help="only this facet key")
    fc.add_argument("--all-projects", action="store_true", help="every registered project")
    fc.add_argument("--json", action="store_true", help="print JSON")
    ep = sub.add_parser("epics", help="shorthand for: facets epic")
    ep.add_argument("--all-projects", action="store_true", help="every registered project")
    ep.add_argument("--json", action="store_true", help="print JSON")
    sub.add_parser("templates", help="list story templates in .skald/templates/")

    pr = sub.add_parser("projects", help="list projects registered on this machine")
    pr.add_argument("--json", action="store_true", help="print JSON")
    prs = pr.add_subparsers(dest="projects_cmd")
    prm = prs.add_parser("rm", help="forget a project (files are untouched)")
    prm.add_argument("name", help="the project name from its config.json")
    pru = prs.add_parser("use", help="make this checkout the project's primary: the one -p NAME and the board open")
    pru.add_argument("path", nargs="?", help="a checkout of the project; default: the current directory")

    cf = sub.add_parser("config", help="get or set a user setting")
    cf.add_argument("key", nargs="?", help="author, push, port, host, or stale_days")
    cf.add_argument("value", nargs="?", help="new value; omit to show the current one")
    cf.add_argument("--unset", action="store_true", help="return the key to its default")

    hk = sub.add_parser("hooks", help="print or install hooks: claude (agent), git (pre-commit), github (workflow)")
    hk.add_argument("target", choices=["claude", "git", "github"], help="which hook to print or install")
    hk.add_argument("--install", action="store_true", help="write the hook instead of printing it")
    hk.add_argument("--strict", action="store_true", help="claude: stop hook also fails on uncommitted story changes")
    hk.add_argument("--as", dest="author", metavar="NAME", help="claude: bake the agent's name into the SessionStart hook (skald context --as NAME)")

    rd = sub.add_parser("render", help="write a Markdown or HTML snapshot of the board to commit")
    rd.add_argument("--format", choices=["md", "html"], help="default: from config.json, else md")
    rd.add_argument("--out", metavar="PATH", help="default: from config.json, else .skald/README.md")
    rd.add_argument("--archived", action="store_true", help="include archived stories")
    rd.add_argument("--stage", action="store_true", help="git add the output afterwards")
    rd.add_argument("--stdout", action="store_true", help="print instead of writing")
    rd.add_argument("--enable", action="store_true", help="also record the path in config.json so commit and hooks re-render automatically")

    sv = sub.add_parser("serve", help="run the board in the foreground")
    sv.add_argument("--host", help="interface to bind (default: from skald config host)")
    sv.add_argument("--port", type=int, help="port (default: from skald config port)")
    sv.add_argument("--open", action="store_true", help="open the browser once the server is up")

    srv = sub.add_parser("server", help="manage the background board server")
    srvs = srv.add_subparsers(dest="server_cmd")
    ss = srvs.add_parser("start", help="start the board server in the background")
    ss.add_argument("--host", help="interface to bind (default: from skald config host)")
    ss.add_argument("--port", type=int, help="port (default: from skald config port)")
    srvs.add_parser("stop", help="stop the background server")
    srvs.add_parser("status", help="show whether the background server is running")
    tk = srvs.add_parser("token", help="print the board's access token (scripts send it as Authorization: Bearer)")
    tk.add_argument("--rotate", action="store_true", help="replace it; existing browser sessions stop working")

    sub.add_parser("open", help="start the server if needed and open the board for this project")
    rl = sub.add_parser("release", help="record a version: a changelog section from the done column, then archive those stories")
    rl.add_argument("version", help="the version being shipped, e.g. 1.2.0")
    rl.add_argument("--changelog", default=None, metavar="PATH", help="default: CHANGELOG.md at the repository root")
    rl.add_argument("--date", help="YYYY-MM-DD (default: today)")
    rl.add_argument("--dry-run", action="store_true", help="print the section and the stories; change nothing")
    rl.add_argument("--no-commit", action="store_true", help="write and archive but do not commit")
    dc = sub.add_parser("docs", help="write the CLI reference (docs/cli.md) from the parser")
    dc.add_argument("--out", metavar="PATH", help="default: docs/cli.md at the repository root")
    dc.add_argument("--stdout", action="store_true", help="print instead of writing")
    dc.add_argument("--check", action="store_true", help="exit 1 if the file is out of date; write nothing")
    cp = sub.add_parser("completion", help="print a shell completion script: eval \"$(skald completion zsh)\"")
    cp.add_argument("shell", choices=["bash", "zsh", "fish"], help="which shell's script to print")
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
        if getattr(args, "columns", "default") != "default":
            lines.append(f"columns unchanged: {cfg_path.name} already exists; edit its columns list by hand")
        if args.name and args.name != config.name:
            config.name = slugify_name(args.name)
            config.save(cfg_path)
            lines.append(f"renamed project to '{config.name}' in {cfg_path.name}")
        else:
            lines.append(f"kept {cfg_path.name} (project '{config.name}')")
    else:
        name = slugify_name(args.name) if args.name else slugify_name(skald_dir.parent.name)
        from .config import COLUMN_PRESETS, Column

        preset = getattr(args, "columns", None) or "default"
        config = ProjectConfig(name, [Column(**c) for c in COLUMN_PRESETS[preset]])
        config.save(cfg_path)
        lines.append(f"wrote {cfg_path.name} (project '{name}', columns: {config.describe()})")

    agents = skald_dir / "AGENTS.md"
    if agents.exists():
        lines.append("kept existing AGENTS.md")
    else:
        agents.write_text(agents_template(), encoding="utf-8")
        lines.append("wrote AGENTS.md")

    notice = ws.registry.register(config.name, skald_dir)
    lines.append(notice or f"project '{config.name}' already registered")
    lines.extend(write_instruction_pointer(repo or skald_dir.parent))
    lines.append("")
    lines.append("Commit .skald/ and run `skald open` to see the board.")
    for line in lines:
        print(line)
    return 0


POINTER = "This repository tracks work with Skald. Read `.skald/AGENTS.md` before starting any task."


def write_instruction_pointer(root: Path) -> list[str]:
    """Append the one-line pointer to root CLAUDE.md and AGENTS.md; create AGENTS.md if neither exists."""
    out = []
    targets = [p for p in (root / "CLAUDE.md", root / "AGENTS.md") if p.exists()]
    if not targets:
        (root / "AGENTS.md").write_text(f"# Agent instructions\n\n{POINTER}\n", encoding="utf-8")
        return [f"created {root / 'AGENTS.md'} with the Skald pointer"]
    for p in targets:
        text = p.read_text(encoding="utf-8", errors="replace")
        if ".skald/AGENTS.md" in text:
            out.append(f"{p.name} already points at .skald/AGENTS.md")
            continue
        sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        p.write_text(text + sep + POINTER + "\n", encoding="utf-8")
        out.append(f"added the Skald pointer to {p.name}")
    return out


def _filtered(store: Store, args, stories, idx):
    rows = stories
    release = getattr(args, "release", None)
    if release:
        return [s for s in rows if s.released == release]
    if args.status:
        rows = [s for s in rows if s.status == args.status]
    elif not args.all:
        rows = [s for s in rows if not store.config.is_terminal(s.status)]
    if args.tag:
        tag = args.tag.strip().lower()
        rows = [s for s in rows if tag in s.tags]
    if getattr(args, "assignee", None):
        rows = [s for s in rows if s.assignee == args.assignee]
    if getattr(args, "parent", None):
        pid = store.resolve(args.parent)
        rows = [s for s in rows if s.parent == pid]
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
        stories, load_warnings = st.load_all(include_archived=args.archived or bool(getattr(args, "release", None)))
        _warn(load_warnings)
        idx = {s.id: s for s in stories}
        sel = _filtered(st, args, stories, idx)
        if getattr(args, "questions", False):
            sel = [s for s in sel if s.open_questions()]
        rows.extend(_story_rows(st, sel, idx, qualify=args.all_projects))
        dicts.extend(st.story_dict(s, idx, ws.user.get("stale_days"), compact=args.compact) for s in sel)
    if args.json:
        print(json.dumps(dicts, indent=2))
    else:
        _print_table(rows, STORY_HEADERS)
    return 0


def _elsewhere(ws: Workspace, store: Store) -> dict:
    """Claims on other branches and in other checkouts' working trees (see Store.claims_elsewhere)."""
    return store.claims_elsewhere(checkouts=ws.other_checkouts(store))


def cmd_next(ws: Workspace, args, store: Optional[Store]) -> int:
    author = cli_identity(args.author)
    stores = ws.open_all()[0] if args.all_projects else [store]
    stale_days = ws.user.get("stale_days")
    for st in stores:
        notes: list[str] = []
        s = st.next_story(for_author=author, stale_days=stale_days, elsewhere=_elsewhere(ws, st), warnings=notes)
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


WAITING_CAP = 5


def build_context(ws: Workspace, store: Store, author: str) -> dict:
    stories, load_warnings = store.load_all()
    idx = {s.id: s for s in stories}
    repo, uncommitted = _uncommitted(store)
    mine = [s for s in stories if s.assignee == author and not store.config.is_terminal(s.status)]
    elsewhere = _elsewhere(ws, store)
    stale_days = ws.user.get("stale_days")
    next_notes: list[str] = []
    nxt = store.next_story(for_author=author, stale_days=stale_days, elsewhere=elsewhere, warnings=next_notes)
    ready_blocked = [s for s in stories if store.config.role(s.status) == "ready" and store.unmet(s, idx)]
    from .store import _is_stale

    stale_claims = [s for s in stories if s.assignee and s.assignee != author
                    and store.config.role(s.status) == "active" and _is_stale(s, stale_days)]
    # Not filtered to the actor: an agent needs to know a story it is about to pick is stalled on a
    # decision, and the human running context needs the whole list.
    waiting = []
    for s in stories:
        qs = s.open_questions()
        if qs:
            newest = qs[-1]
            waiting.append({"id": s.id, "title": s.title, "status": s.status, "open": len(qs),
                            "question": newest["text"].strip().splitlines()[0] if newest["text"].strip() else "",
                            "stamp": newest["stamp"], "author": newest["author"]})
    # Hook output is paid for on every session start (D50), so this section is bounded: newest first, five at most.
    waiting.sort(key=lambda w: w["stamp"], reverse=True)
    waiting_more = max(0, len(waiting) - WAITING_CAP)
    waiting = waiting[:WAITING_CAP]

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
        "waiting": waiting,
        "waiting_more": waiting_more,
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
    if ctx["waiting"]:
        print("\nWaiting on a human (answer with skald answer <id> \"...\"):")
        for w in ctx["waiting"]:
            more = f" (+{w['open'] - 1} more)" if w["open"] > 1 else ""
            print(f"  {w['id']}  {w['title']}\n          {w['author']} asked: {w['question']}{more}")
        if ctx.get("waiting_more"):
            print(f"  ... and {ctx['waiting_more']} more: skald ls --questions")
    if ctx["stale_claims"]:
        print(f"\nStale claims (no update for {ws.user.get('stale_days')}+ days; take over with skald claim <id>):")
        for c in ctx["stale_claims"]:
            print(f"  {c['id']}  {c['status']:<12} {c['title']}  ({c['assignee']}, {c['updated_at'][:10]})")
    if ctx["claimed_elsewhere"]:
        print("\nClaimed on other branches or in other checkouts:")
        for sid, claims in ctx["claimed_elsewhere"].items():
            print(f"  {sid}  " + "; ".join(
                f"{c['assignee']} on {c['branch']} ({c['status']})" + (f", uncommitted in {c['checkout']}" if c.get("checkout") else "")
                for c in claims))
    if ctx["uncommitted"]:
        print(f"\nUncommitted story files: {len(ctx['uncommitted'])} (commit them with your code)")
    _warn(ctx["warnings"])
    return 0


def _resume_extras(story: Story, args) -> dict:
    """Body views for ``resume``: requirements by default, one section, or everything before the notes."""
    from .store import prelude_of, requirements_of, section_of, sections_of

    out: dict = {"requirements": requirements_of(story.body), "sections": sections_of(story.body)}
    section = getattr(args, "section", None)
    if section:
        text = section_of(story.body, section)
        if text is None:
            names = ", ".join(s["heading"] for s in out["sections"]) or "none"
            raise NotFoundError(f"{story.id} has no section starting with '{section}' (sections: {names})")
        out["section"] = {"heading": text.splitlines()[0].lstrip("# ").strip(), "text": text}
    if getattr(args, "full", False):
        out["body"] = prelude_of(story.body)
    return out


def cmd_resume(ws: Workspace, store: Store, args) -> int:
    story = store.get(args.id)
    idx = store.index()
    d = store.story_dict(story, idx, ws.user.get("stale_days"), compact=True)
    notes = story.notes()
    handoff = story.last_note("handoff")
    latest = handoff or (notes[-1] if notes else None)
    d.update(_resume_extras(story, args))
    d["deps"] = [x.to_dict() for x in store.dep_states(story, idx)]
    d["latest"] = latest
    d["note_count"] = len(notes)
    d["decisions"] = [n for n in notes if n["kind"] == "decision"]
    d["blockers"] = [n for n in notes if n["kind"] == "blocker"]
    d["open_questions"] = story.open_questions()
    if story.parent and story.parent in idx:
        from .store import requirements_of

        p = idx[story.parent]
        d["parent_story"] = {"id": p.id, "title": p.title, "status": p.status, "requirements": requirements_of(p.body)}
    from . import audit as au

    d["audit"] = au.status_line(story, _repo_of(store))
    if args.json:
        print(json.dumps(d, indent=2))
        return 0
    print(f"{story.id}  {story.title}")
    print(f"status {story.status}" + (f" · assignee {story.assignee}" if story.assignee else "")
          + (f" · checklist {d['checklist']['done']}/{d['checklist']['total']}" if d["checklist"]["total"] else "")
          + (f" · acceptance {d['acceptance']['done']}/{d['acceptance']['total']}" if d.get("acceptance") else "")
          + f" · {d['audit']}")
    if d["deps"]:
        print("depends on: " + ", ".join(f"{x['ref']} ({x['state']}{'' if x['satisfied'] else ', unmet'})" for x in d["deps"]))
    if d.get("parent_story"):
        p = d["parent_story"]
        print(f"\nchild of {p['id']}  {p['title']}  ({p['status']})")
        if p.get("requirements"):
            print(textwrap.indent(p["requirements"].strip(), "  "))
    if "section" in d:
        print("\n" + d["section"]["text"].strip() + "\n")
    elif "body" in d:
        print("\n" + d["body"].strip() + "\n")
    else:
        print("\n" + d["requirements"].strip() + "\n")
        # The rest of the body is a map, not a dump: an agent pays for a section only when it asks.
        shown = d["requirements"].splitlines()[0].lstrip("# ").strip().lower() if d["requirements"].startswith("## ") else None
        others = [s for s in d["sections"] if s["heading"].lower() != shown]
        if others and shown is not None:
            if len(others) > 4:
                print("Also in this story:")
                for s in others:
                    print(f"  ## {s['heading']} ({s['lines']} lines)")
            else:
                print("Also in this story: " + " · ".join(f"## {s['heading']} ({s['lines']} lines)" for s in others))
            first = others[0]["heading"].split()[0].lower()
            print(f"  skald resume {story.id} --section {first}   |   skald resume {story.id} --full\n")
    if d["decisions"]:
        print("Decisions:")
        for n in d["decisions"]:
            print(f"  - {n['stamp']} [{n['author']}] {n['text'].strip().splitlines()[0]}")
        print()
    if d["open_questions"]:
        print("Open questions (waiting on a human; work on what does not depend on them; skald answer <id> --question N):")
        for i, n in enumerate(d["open_questions"], 1):
            print(f"  {i}. {n['stamp']} [{n['author']}] {n['text'].strip()}")
        print()
    if latest:
        label = "Latest handoff" if handoff else "Latest note"
        others = len(notes) - 1
        print(f"{label} ({latest['stamp']}, {latest['author']}){f', {others} earlier note(s) in the file' if others > 0 else ''}:")
        print(latest["text"].rstrip())
    else:
        print("No notes yet.")
    return 0


def cmd_audit(ws: Workspace, store: Store, args) -> int:
    """The tool checks claims; the agent checks premises. It lists what it could verify and never says the story is true."""
    from . import audit as au

    story = store.get(args.id)
    repo = _repo_of(store)
    result = au.run_audit(story, repo, include_notes=args.notes)
    lines = au.summary_lines(result)
    noted = None
    if not args.no_note:
        noted = store.append_note(story.id, "\n".join(lines), cli_identity(args.author), "audit")
    if args.json:
        result["noted"] = noted is not None
        print(json.dumps(result, indent=2))
        return 0
    print(f"audit {story.id}  {story.title}")
    for line in lines:
        print(f"  {line}")
    if noted is not None:
        print(f"noted on {story.id} (audit)")
    return 0


def cmd_import(ws: Workspace, store: Store, args) -> int:
    from . import importer as imp

    mapping = imp.load_mapping(Path(args.map)) if args.map else {}
    files = imp.collect([Path(p) for p in args.paths], mapping)
    if not files:
        print("nothing to import: no Markdown files under the given paths (after the mapping's exclude rules)")
        return 0
    author = (args.author or "").strip() or "import"
    if args.status:
        store._check_status(args.status)
    plans = []
    for source, rel in files:
        text = read_text(source)
        plan = imp.plan_text(text, rel, source, mapping, default_status=args.status)
        if args.status:
            plan.status = args.status
        if plan.status is not None:
            try:
                store._check_status(plan.status)
            except SkaldError as e:
                plan.problems.append(str(e))
        plans.append(plan)
    problems = [(p.relpath, x) for p in plans for x in p.problems]
    if problems:
        for rel, x in problems:
            print(f"ERROR: {rel}: {x}", file=sys.stderr)
        raise SkaldError(f"{len(problems)} problem(s); nothing imported")

    root = Path(args.rewrite_links).resolve() if args.rewrite_links else None
    if args.dry_run:
        for p in plans:
            print(f"{p.relpath}")
            print(f"  title:      {p.title}")
            print(f"  status:     {p.status or '(first backlog column)'}")
            print(f"  tags:       {', '.join(p.tags) or '-'}")
            print(f"  created_at: {p.created_at or '(now)'}")
            print(f"  body:       {len(p.body.splitlines())} lines")
            for n in p.notes:
                first = n.text.splitlines()[0] if n.text else ""
                print(f"  note:       [{n.kind}] {n.at or 'at created_at'}: {first[:70]}")
        if root is not None:
            # Count what a real run would rewrite, without knowing the ids yet: map each source to a stand-in.
            fake = {src: store.stories_dir / f"000000-{Path(rel).stem}.md" for src, rel in files}
            counts = imp.rewrite_links(root, fake, write=False)
            total = sum(counts.values())
            print(f"\nlinks: {total} reference(s) in {len(counts)} file(s) would be rewritten")
            for f, n in sorted(counts.items()):
                print(f"  {f}: {n}")
        print(f"\ndry run: {len(plans)} file(s), {sum(len(p.notes) for p in plans)} note(s); nothing written")
        return 0

    moved: dict[Path, Path] = {}
    for p in plans:
        story, _ = store.create(p.title, p.status, p.tags, [], p.body, "", None, created_at=p.created_at, wrap=False)
        for n in p.notes:
            store.append_note(story.id, n.text, author, n.kind, at=n.at or p.created_at)
        moved[p.source] = story.path
        print(f"imported {story.id}  {p.title}  ({len(p.notes)} note(s); {', '.join(p.tags) or 'no tags'})")
    if root is not None:
        counts = imp.rewrite_links(root, moved, write=True)
        total = sum(counts.values())
        print(f"links: rewrote {total} reference(s) in {len(counts)} file(s)")
        for f, n in sorted(counts.items()):
            print(f"  {f}: {n}")
    if args.rm:
        for src in moved:
            os.unlink(src)
        print(f"removed {len(moved)} source file(s)")
    print(f"imported {len(moved)} stor{'y' if len(moved) == 1 else 'ies'}; review them, then commit .skald/ together with the removals")
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
    story, warnings = store.create(args.title, args.status, tags, blockers, body, args.assignee, args.template,
                                   parent=getattr(args, "parent", None), inherit=not getattr(args, "no_inherit", False),
                                   created_at=getattr(args, "created_at", None))
    _warn(warnings)
    if args.json:
        print(json.dumps(store.story_dict(story), indent=2))
    else:
        print(story.id)
    return 0


def cmd_complete(ws: Workspace, argv: list[str]) -> int:
    """``skald _complete -- CWORD WORD...``: candidates for the shell scripts, one per line as value<TAB>description."""
    from .completion import complete

    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        return 1
    try:
        cword = int(argv[0])
    except ValueError:
        return 1
    words = argv[1:]
    try:
        cands = complete(ws, words, cword)
    except Exception:  # completion must never break the shell
        return 0
    for value, desc in cands:
        print(f"{value}\t{desc}" if desc else value)
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
        elif key == "parent":
            kwargs["parent"] = value.strip()
        else:
            raise SkaldError(f"cannot set '{key}' (use move, tag, or block for status, tags, blocked_by)")
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
    busy = store.busy_lanes(stories, _elsewhere(ws, store)) if store.config.facet_limits else {}
    lanes = {f"{k}:{v}": {"active": len(ids), "limit": store.config.facet_limits[k]}
             for k, values in busy.items() for v, ids in values.items()}
    info = {
        "project": store.name,
        "path": str(store.dir),
        "branch": gitutil.branch(repo) if repo else None,
        "counts": counts,
        "unknown_status": unknown,
        "ready_unblocked": len(ready),
        "lanes": lanes,
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
    if info["lanes"]:
        busy_l = [f"{k} {d['active']}/{d['limit']}" for k, d in info["lanes"].items() if d["active"] >= d["limit"]]
        print("lanes busy: " + (", ".join(busy_l) if busy_l else "none"))
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
    kids = [] if getattr(args, "no_children", False) else [k.id for k in store.children(story.id)]
    entries = gitutil.commits_for_family(repo, story.id, kids, all_branches=args.all_branches)
    if args.json:
        print(json.dumps(entries, indent=2))
        return 0
    if not entries:
        print(f"no commits reference {story.id} (add a '{gitutil.TRAILER}: {story.id}' trailer or [{story.id}] to commit messages)")
        return 0
    for e in entries:
        via = f"  [{e['story']}]" if e.get("story") != story.id else ""
        print(f"{e['sha']}  {e['date'][:16].replace('T', ' ')}  {e['author']:<20}  {e['subject']}{via}")
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


def cmd_graph(store: Store, args) -> int:
    from .graph import build_graph, render_as

    stories, warnings = store.load_all(include_archived=args.archived)
    _warn(warnings)
    g = build_graph(store, stories, include_isolated=args.all)
    if not g["edges"] and not args.all:
        print("no dependencies between stories; use --all to draw every story", file=sys.stderr)
    sys.stdout.write(render_as(g, args.format))
    return 0


def cmd_docs(args) -> int:
    from .util import atomic_write

    text = docs_markdown()
    if args.stdout:
        sys.stdout.write(text)
        return 0
    root = gitutil.root(Path.cwd()) or Path.cwd()
    path = Path(args.out) if args.out else root / "docs" / "cli.md"
    if not path.is_absolute():
        path = root / path
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if args.check:
        if current == text:
            print(f"{path} is up to date")
            return 0
        print(f"{path} is out of date; run `skald docs`", file=sys.stderr)
        return 1
    if current == text:
        print(f"{path} unchanged")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, text)
    print(f"wrote {path}")
    return 0


def cmd_release(ws: Workspace, store: Store, args) -> int:
    from . import release as rel

    repo = _repo_of(store)
    plan = rel.plan(store, args.version, args.date)
    _warn(plan.warnings)
    if args.dry_run:
        sys.stdout.write(plan.section())
        print(f"\nwould archive {len(plan.stories)} stor{'y' if len(plan.stories) == 1 else 'ies'} with released: {plan.version}")
        return 0
    root = repo or store.dir.parent
    changelog = Path(args.changelog) if args.changelog else root / rel.DEFAULT_CHANGELOG
    if not changelog.is_absolute():
        changelog = root / changelog
    result = rel.apply(store, plan, changelog)
    print(f"wrote {changelog.relative_to(root).as_posix() if changelog.is_relative_to(root) else changelog}: section {plan.version} ({plan.date})")
    for s in plan.stories:
        print(f"archived {s.id}  {s.title}")
    if args.no_commit or repo is None:
        if repo is None:
            print("not a git repository; nothing committed")
        return 0
    skald_rel = _skald_rel(store, repo)
    rendered = auto_render(store, repo)
    paths = [skald_rel]
    for extra in (rendered, changelog.relative_to(repo).as_posix() if changelog.is_relative_to(repo) else None):
        if extra and not extra.startswith(skald_rel + "/") and extra not in paths:
            paths.append(extra)
    message = with_trailers(f"Release {plan.version}", [s.id for s in plan.stories])
    sha = gitutil.commit_path(repo, paths, message)
    print(f"committed {sha}: Release {plan.version}")
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
    if args.projects_cmd == "use":
        start = Path(args.path).expanduser().resolve() if args.path else None
        skald_dir = find_skald_dir(start)
        if skald_dir is None or not (skald_dir / "stories").is_dir():
            raise NotFoundError(f"no Skald project at {start or Path.cwd()}")
        cfg = skald_dir / "config.json"
        if not cfg.exists():
            raise NotFoundError(f"{skald_dir} has no config.json; run any skald command there first")
        name = ProjectConfig.load(cfg).name
        ws.registry.use(name, skald_dir)
        print(f"project '{name}' now points at {skald_dir}")
        return 0
    entries = ws.registry.entries()
    _notice(ws.registry.notices)
    if args.json:
        for e in entries:
            for c in e["checkouts"]:
                repo = gitutil.root(Path(c["path"]))
                c["branch"] = gitutil.branch(repo) if repo else None
        print(json.dumps(entries, indent=2))
        return 0
    if not entries:
        print("no projects registered; run `skald init` inside a repository")
        return 0
    rows = []
    for e in entries:
        rows.append([e["name"], "ok" if e["exists"] else "missing", e["path"]])
        for c in e["checkouts"]:
            repo = gitutil.root(Path(c["path"]))
            branch = (gitutil.branch(repo) if repo else None) or "-"
            try:
                dirty = len(gitutil.changes(repo, str(Path(c["path"]).relative_to(repo)))) if repo else 0
            except (GitError, ValueError):
                dirty = 0
            kind = "worktree" if c["worktree"] else "checkout"
            rows.append(["", f"{kind} on {branch}" + (f", {dirty} uncommitted" if dirty else ""), c["path"]])
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
    if key == "epic":
        # Structural epics too: a parent with children counts as one, keyed by its id and titled.
        for st in stores:
            stories, _ = st.load_all(include_archived=True)
            by_parent: dict = {}
            for s in stories:
                if s.parent:
                    by_parent.setdefault(s.parent, []).append(s)
            for pid, kids in by_parent.items():
                p = next((s for s in stories if s.id == pid), None)
                label = f"{st.name}:{pid}" if args.all_projects else pid
                m = merged.setdefault("parent", {}).setdefault(label, {"total": 0, "done": 0, "open": 0, "ids": [],
                                                                      "title": p.title if p else "(missing)"})
                for k in kids:
                    m["total"] += 1
                    m["done" if st.config.is_terminal(k.status) else "open"] += 1
                    m["ids"].append(f"{st.name}:{k.id}" if args.all_projects else k.id)
    if args.json:
        print(json.dumps(merged, indent=2))
        return 0
    if not merged:
        print(f"no {key + ' ' if key else ''}facet tags; tag stories like {key or 'epic'}:name to create one"
              + (", or give stories a parent" if key == "epic" else ""))
        return 0
    rows = []
    for k in sorted(merged):
        for v in sorted(merged[k]):
            b = merged[k][v]
            pct = int(round(100 * b["done"] / b["total"])) if b["total"] else 0
            label = f"{v}  {b['title']}" if k == "parent" and b.get("title") else v
            rows.append([k, label, str(b["total"]), str(b["done"]), str(b["open"]), f"{pct}%"])
    _print_table(rows, ["KEY", "VALUE", "TOTAL", "DONE", "OPEN", "PROGRESS"])
    return 0


def cmd_columns(store: Store, args) -> int:
    if args.json:
        print(json.dumps([c.to_dict() for c in store.config.columns], indent=2))
        return 0
    rows = [[c.key, c.label, c.role, str(c.limit) if c.limit else "-"] for c in store.config.columns]
    _print_table(rows, ["KEY", "LABEL", "ROLE", "LIMIT"])
    if store.config.facet_limits:
        print("\nLanes (at most N active stories per value):")
        for key, n in store.config.facet_limits.items():
            print(f"  {key}: {n}")
    return 0


def claude_hooks(strict: bool, author: Optional[str] = None) -> dict:
    """The Claude Code hooks. SessionStart runs the bounded orientation block, never a full listing:
    hook output is paid for on every session start, resume, clear, and compaction, whatever the backlog size."""
    stop = "skald check --hook" if strict else "skald check"
    start = "skald context" + (f" --as {author}" if author else "")
    return {
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": start}]}],
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


# Until the first PyPI release, generated workflows install from the repository.
INSTALL_SPEC = "git+https://github.com/Vitund-AI/skald.git"


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
      - run: pip install {INSTALL_SPEC}
      - run: skald check

  diff:
    if: github.event_name == 'pull_request'
    needs: check
    runs-on: ubuntu-latest
    permissions:
      contents: read        # listing any permission drops the rest to none; checkout needs this
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install {INSTALL_SPEC}
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
      - run: pip install {INSTALL_SPEC}
      - run: skald render --out {render_path}
      - name: Commit the rendered board if it changed
        run: |
          if ! git diff --quiet -- {render_path}; then
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
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
    print(f"wrote {path.relative_to(repo).as_posix()}")
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
    snippet = claude_hooks(args.strict, getattr(args, 'author', None))
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
    skill = repo / ".claude" / "skills" / "skald" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text(claude_skill(), encoding="utf-8")
    print(f"wrote {skill.relative_to(repo).as_posix()}")
    return 0


def claude_skill() -> str:
    return (
        "---\n"
        "name: skald\n"
        "description: Work this repository's Skald backlog. Use at the start of any task to orient "
        "(skald context), when picking or claiming work, when recording progress, decisions, or a handoff, "
        "and when finishing a story. Covers the skald CLI and the rules for story files.\n"
        "---\n\n"
        + agents_template()
    )


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------

PROJECT_COMMANDS = {
    "ls", "next", "show", "new", "move", "mv", "claim", "set", "tag", "block", "note", "rm", "log",
    "archive", "unarchive", "check", "status", "commit", "changelog", "columns", "templates",
    "hooks", "open", "branches", "facets", "epics", "render", "context", "resume", "answer",
    "commits", "diff", "activity", "graph", "release", "audit", "import",
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
    if argv and argv[0] == "_complete":
        return cmd_complete(ws, argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    if args.command == "init":
        return cmd_init(ws, args)
    if args.command == "completion":
        from .completion import SCRIPTS

        sys.stdout.write(SCRIPTS[args.shell])
        return 0
    if args.command == "docs":
        return cmd_docs(args)
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
    if args.command == "audit":
        return cmd_audit(ws, store, args)
    if args.command == "import":
        return cmd_import(ws, store, args)
    if args.command == "next":
        return cmd_next(ws, args, store)
    if args.command == "show":
        return cmd_show(ws, args, store)
    if args.command == "new":
        return cmd_new(ws, args, store)
    if args.command in ("move", "mv"):
        story, warnings = store.update(args.id, status=args.status, elsewhere=_elsewhere(ws, store))
        _warn(warnings)
        print(f"moved {story.id} to {story.status}")
        return 0
    if args.command == "claim":
        story, warnings = store.claim(args.id, cli_identity(args.author), ws.user.get("stale_days"), _elsewhere(ws, store))
        _warn(warnings)
        print(f"{story.id} claimed by {story.assignee}, now {story.status}")
        return 0
    if args.command == "set":
        return cmd_set(store, args)
    if args.command == "note":
        story = store.append_note(args.id, _read_text_arg(args.text), cli_identity(args.author), args.kind, at=getattr(args, "at", None))
        print(f"noted on {story.id}" + (f" ({args.kind})" if args.kind else ""))
        return 0
    if args.command == "answer":
        open_qs = store.get(args.id).open_questions()
        text = _read_text_arg(args.text)
        which = getattr(args, "question", None)
        if which is not None:
            if not 1 <= which <= len(open_qs):
                raise SkaldError(f"--question must be between 1 and {len(open_qs)} (open questions on this story)" if open_qs
                                 else "this story has no open question")
            from .store import answer_line

            text = f"{answer_line(open_qs[which - 1])}\n{text}"
        story = store.append_note(args.id, text, cli_identity(args.author), "decision")
        closed = 1 if which is not None else len(open_qs)
        print(f"answered on {story.id} (decision; {closed} question(s) closed)" if closed else f"noted on {story.id} (decision; no open question)")
        return 0
    if args.command == "rm":
        cleared: list[str] = []
        story = store.delete(args.id, force=args.force, notes=cleared)
        for line in cleared:
            print(line)
        print(f"deleted {story.id} ({story.path.name})")
        return 0
    if args.command == "log":
        return cmd_log(store, args)
    if args.command == "release":
        return cmd_release(ws, store, args)
    if args.command == "archive":
        moved = store.archive(dry_run=args.dry_run, ids=args.ids or None)
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
    if args.command == "graph":
        return cmd_graph(store, args)
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
