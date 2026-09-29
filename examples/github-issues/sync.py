#!/usr/bin/env python3
"""Pull a repository's GitHub issues into the backlog, one way and safe to re-run.

Each issue without a story becomes one: its title, its body under a link back
to the issue, its labels as tags, a `gh:<number>` tag, and its creation date;
each comment becomes a dated note by its author. An issue that already has a
story (matched by that tag, archived stories included) is never imported
twice, and a story created earlier is never edited: instead the run reports
where GitHub and the backlog have drifted apart, for a person to settle.

Nothing is written to GitHub. Run it from inside the repository's checkout;
it drives the `skald` CLI with the interpreter it runs on, so no `skald` on
PATH is needed, and `gh` only when not reading `--from-json`.

    python3 examples/github-issues/sync.py [--repo OWNER/NAME] [--dry-run]
        [--state open|closed|all] [--status COLUMN] [--key gh] [--no-labels]
        [--from-json FILE] [--project NAME] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

FIELDS = "number,title,body,labels,createdAt,url,state,comments,author"


def skald(args: argparse.Namespace, *argv: str, stdin: str | None = None) -> str:
    cmd = [sys.executable, "-m", "skald"]
    if args.project:
        cmd += ["-p", args.project]
    # UTF-8 both ways, whatever the locale: issue text is full of emoji and accents (Windows is cp1252).
    proc = subprocess.run(cmd + list(argv), input=stdin, capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, "PYTHONUTF8": "1"})
    if proc.returncode != 0:
        sys.exit(f"skald {' '.join(argv[:2])} failed: {proc.stderr.strip()}")
    return proc.stdout


def fetch(args: argparse.Namespace) -> list[dict]:
    """Every issue, open and closed: closed ones are needed to spot drift even when only open ones import."""
    if args.from_json:
        with open(args.from_json, encoding="utf-8") as f:
            return json.load(f)
    cmd = ["gh", "issue", "list", "--state", "all", "--limit", str(args.limit), "--json", FIELDS]
    if args.repo:
        cmd += ["--repo", args.repo]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        sys.exit("the gh CLI is needed to fetch issues (https://cli.github.com), or pass --from-json")
    if proc.returncode != 0:
        sys.exit(f"gh issue list failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def label_tag(name: str) -> str:
    """A GitHub label as a Skald tag: `Type: Bug` -> `type:bug`, `good first issue` -> `good-first-issue`."""
    tag = re.sub(r"\s*:\s*", ":", name.strip().lower())
    return re.sub(r"[\s,]+", "-", tag).strip("-")


def ref(issue: dict) -> str:
    """`owner/name#12` from the issue URL, for the link at the top of the story."""
    m = re.search(r"github\.com/([^/]+/[^/]+)/issues/\d+", issue.get("url") or "")
    return f"{m.group(1)}#{issue['number']}" if m else f"#{issue['number']}"


def body_of(issue: dict) -> str:
    source = f"Imported from [{ref(issue)}]({issue['url']})." if issue.get("url") else f"Imported from {ref(issue)}."
    text = (issue.get("body") or "").strip()
    return f"{source}\n\n{text}\n" if text else f"{source}\n"


def login(who) -> str:
    return (who or {}).get("login") or "ghost"


def drift(issue: dict, story: dict) -> list[str]:
    done = story.get("archived") or story.get("role") in ("done", "closed")
    closed = issue.get("state", "").upper() == "CLOSED"
    sid, n = story["id"], issue["number"]
    out = []
    if closed and not done:
        out.append(f"issue #{n} is closed on GitHub, but story {sid} is still {story['status']}")
    if done and not closed:
        where = "archived" if story.get("archived") else story["status"]
        out.append(f"story {sid} is {where}, but issue #{n} is still open")
    if issue["title"].strip() != story["title"]:
        out.append(f"issue #{n} is titled {issue['title'].strip()!r}; story {sid} says {story['title']!r}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", help="OWNER/NAME for gh; default: the repository gh sees from here")
    ap.add_argument("--state", choices=("open", "closed", "all"), default="open",
                    help="which issues to import (drift is checked for all of them); default open")
    ap.add_argument("--status", help="column for new stories; default: the project's default")
    ap.add_argument("--key", default="gh", help="tag key linking a story to its issue; default gh")
    ap.add_argument("--no-labels", action="store_true", help="do not turn labels into tags")
    ap.add_argument("--limit", type=int, default=1000, help="most issues to fetch; default 1000")
    ap.add_argument("--from-json", metavar="FILE", help=f"read `gh issue list --json {FIELDS}` output instead of calling gh")
    ap.add_argument("--project", help="the Skald project; default: the one containing this directory")
    ap.add_argument("--dry-run", action="store_true", help="report what would be created and the drift; change nothing")
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # an emoji title must not crash a cp1252 console

    issues = sorted(fetch(args), key=lambda i: i["number"])
    stories = json.loads(skald(args, "ls", "--all", "--archived", "--json") or "[]")
    prefix = f"{args.key}:"
    linked = {t[len(prefix):]: s for s in stories for t in s["tags"] if t.startswith(prefix)}

    created, skipped, drifted = [], 0, []
    for issue in issues:
        story = linked.get(str(issue["number"]))
        if story:
            skipped += 1
            drifted += drift(issue, story)
            continue
        state = issue.get("state", "").upper()
        if args.state != "all" and state != args.state.upper():
            continue
        tags = [f"{args.key}:{issue['number']}"]
        if not args.no_labels:
            tags += [t for t in (label_tag(lb["name"]) for lb in issue.get("labels") or []) if t]
        comments = issue.get("comments") or []
        row = {"issue": issue["number"], "title": issue["title"].strip(), "tags": tags, "notes": len(comments)}
        if not args.dry_run:
            new = ["new", "--tags", ",".join(tags), "--body", "-", "--created-at", issue["createdAt"], "--json"]
            if args.status:
                new += ["--status", args.status]
            # The title goes after --, so one that starts with a dash is not read as a flag.
            row["id"] = json.loads(skald(args, *new, "--", issue["title"].strip(), stdin=body_of(issue)))["id"]
            for c in comments:
                skald(args, "note", row["id"], "-", "--as", login(c.get("author")), "--kind", "comment",
                      "--at", c["createdAt"], stdin=(c.get("body") or "").strip() or "(empty comment)")
        created.append(row)

    summary = {"dry_run": args.dry_run, "created": created, "already_imported": skipped, "drift": drifted}
    if args.json:
        print(json.dumps(summary, indent=2))
        return 0
    verb = "would create" if args.dry_run else "created"
    for r in created:
        at = f" as {r['id']}" if "id" in r else ""
        print(f"{verb} #{r['issue']}{at}: {r['title']}  [{', '.join(r['tags'])}]  {r['notes']} note(s)")
    print(f"{len(created)} {'to create' if args.dry_run else 'created'}, {skipped} already imported")
    if drifted:
        print("\nDrift (not changed; settle it by hand):")
        for d in drifted:
            print(f"  {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
