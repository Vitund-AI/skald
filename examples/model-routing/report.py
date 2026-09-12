#!/usr/bin/env python3
"""Intended tier against who did the work, per finished story.

One row per story in a done column or the archive: the effort tag it was
planned with, the author labels on its notes and its assignee, days from
first claim to done, and whether it went back from review. Reads the story
files through the skald package; run where Skald is installed.

    python3 examples/model-routing/report.py [--project NAME] [--json] [--tag-prefix effort:]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

from skald.registry import Workspace
from skald.store import parse_notes


def parse_stamp(stamp: str) -> datetime:
    return datetime.strptime(stamp, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)


def bounces(store) -> dict[str, int]:
    """Story id -> times it went back to a ready column, from `skald activity` over the whole history."""
    root = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], capture_output=True, text=True,
                          cwd=store.dir.parent).stdout.split()
    if not root:
        return {}
    out = subprocess.run(["skald", "activity", "--json", "--since", root[-1]], capture_output=True, text=True,
                         cwd=store.dir.parent).stdout
    events = json.loads(out) if out.strip() else []
    ready = set(store.config.keys_with_role("ready"))
    counts: dict[str, int] = {}
    for e in events:
        bits = e["event"].split()
        if len(bits) == 4 and bits[0] == "status" and bits[2] == "->" and bits[3] in ready and bits[1] not in ready:
            if bits[1] not in store.config.keys_with_role("backlog"):
                counts[e["id"]] = counts.get(e["id"], 0) + 1
    return counts


def row(story, prefix: str, sent_back: int) -> dict:
    notes = parse_notes(story.body)
    intended = next((t[len(prefix):] for t in story.tags if t.startswith(prefix)), "")
    workers = []
    for n in notes:
        if n["author"] not in workers and n["author"] not in ("import", "skald"):
            workers.append(n["author"])
    if story.assignee and story.assignee not in workers:
        workers.append(story.assignee)
    stamps = [parse_stamp(n["stamp"]) for n in notes]
    days = round((max(stamps) - min(stamps)).total_seconds() / 86400, 1) if len(stamps) > 1 else 0.0
    return {"id": story.id, "title": story.title, "intended": intended, "worked_by": workers,
            "notes": len(notes), "days": days, "sent_back": sent_back, "released": story.released}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", help="registered project name (default: the one for the current directory)")
    ap.add_argument("--tag-prefix", default="effort:", help="the intent facet (default: effort:)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    store = Workspace().current(args.project)
    stories, _ = store.load_all(include_archived=True)
    done = [s for s in stories if store.config.is_terminal(s.status) and not store.config.is_closed(s.status)]
    back = bounces(store)
    rows = [row(s, args.tag_prefix, back.get(s.id, 0)) for s in done]
    if args.json:
        json.dump(rows, sys.stdout, indent=2)
        print()
        return 0
    if not rows:
        print("no finished stories yet")
        return 0
    print(f"{'ID':6}  {'INTENDED':10} {'WORKED BY':24} {'DAYS':>5}  {'BACK':4}  TITLE")
    for r in sorted(rows, key=lambda r: (r["intended"], r["id"])):
        print(f"{r['id']:6}  {r['intended'] or '-':10} {', '.join(r['worked_by']) or '-':24.24} {r['days']:5.1f}  "
              f"{r['sent_back'] or '-':>4}  {r['title']}")
    by = {}
    for r in rows:
        k = r["intended"] or "-"
        by.setdefault(k, []).append(r)
    print()
    for k, rs in sorted(by.items()):
        back = sum(1 for r in rs if r["sent_back"])
        print(f"{k}: {len(rs)} finished, {back} sent back from review or in progress, {sum(r['days'] for r in rs) / len(rs):.1f} days on average")
    return 0


if __name__ == "__main__":
    sys.exit(main())
