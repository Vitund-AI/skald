#!/usr/bin/env python3
"""Say whether a set of changed paths is documentation only, so CI can skip the test matrix.

    git diff --name-only BASE HEAD | python3 scripts/docs_only.py   # prints true or false

Documentation here means files the test suite never reads. CHANGELOG.md is not one
(the version guard reads its newest heading), nor is docs/cli.md (generated from the
parser and checked against it), nor anything under .skald/ or the contract template.
An empty list is not documentation only: with nothing to judge, run everything.
"""
import sys

DOC_FILES = {"README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "SPEC.md", "DECISIONS.md", "LICENSE"}
DOC_DIRS = ("docs/",)
NOT_DOCS = {"docs/cli.md"}


def is_doc(path: str) -> bool:
    path = path.strip().replace("\\", "/")
    if not path or path in NOT_DOCS:
        return False
    if path in DOC_FILES:
        return True
    return any(path.startswith(d) for d in DOC_DIRS)


def docs_only(paths) -> bool:
    paths = [p.strip() for p in paths if p.strip()]
    return bool(paths) and all(is_doc(p) for p in paths)


if __name__ == "__main__":
    print("true" if docs_only(sys.stdin.read().splitlines()) else "false")
