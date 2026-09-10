"""Shell completion: scripts for bash, zsh, and fish, and the candidates they ask for.

The scripts are thin shims. On every Tab they run ``skald _complete -- CWORD WORD...``
with the words typed after ``skald`` and the index of the word being completed, and
print what comes back. All of the logic lives here, where the parser and the story
files are, so the shells never carry their own copy of the command list.

Candidates are ``(value, description)`` pairs. zsh and fish show the description;
bash shows the value only.
"""
from __future__ import annotations

from typing import Optional

from . import gitutil
from .errors import SkaldError
from .registry import Workspace
from .store import Store

NOTE_KINDS = ["handoff", "decision", "blocker", "result", "progress"]
SET_KEYS = {"title=": "new title", "rank=": "position in the column", "assignee=": "who owns it (empty to clear)"}
CONFIG_KEYS = {"author": "name for notes and claims from the board", "push": "push after committing from the board",
               "port": "board server port", "host": "board server host", "stale_days": "days before an active story is stale"}
ID_COMMANDS = {"show", "move", "claim", "set", "tag", "block", "note", "answer", "rm", "log", "resume", "commits", "archive", "unarchive"}
FLAG_SOURCES = {
    "-p": "projects", "--project": "projects", "--status": "columns", "--template": "templates",
    "--branch": "refs", "--since": "refs", "--until": "refs", "--as": "authors", "--assignee": "authors",
    "--tags": "tags", "--blocked-by": "ids", "--kind": "kinds", "--release": "releases",
}

Candidate = tuple[str, str]


def _flags_of(command: dict) -> dict[str, tuple[bool, list[str], str]]:
    """``{flag: (takes_value, choices, help)}`` for one command from the reference."""
    out = {}
    for a in command["arguments"]:
        if a["positional"]:
            continue
        for f in a["flags"]:
            name = f.split(" ", 1)[0]
            out[name] = (" " in f, a["choices"], a["help"])
    return out


def _positionals_of(command: dict) -> list[dict]:
    return [a for a in command["arguments"] if a["positional"]]


class Completer:
    def __init__(self, ws: Workspace, reference: list[dict]):
        self.ws = ws
        self.reference = {c["name"]: c for c in reference}
        self._store: Optional[Store] = None
        self._store_tried = False
        self._stories = None

    # -- data sources -------------------------------------------------------

    def store(self, project: Optional[str]) -> Optional[Store]:
        if not self._store_tried:
            self._store_tried = True
            try:
                self._store = self.ws.current(project)
            except SkaldError:
                self._store = None
        return self._store

    def stories(self, project, archived: Optional[bool] = None) -> list:
        store = self.store(project)
        if store is None:
            return []
        if self._stories is None:
            self._stories, _ = store.load_all(include_archived=True)
        if archived is None:
            return self._stories
        return [s for s in self._stories if s.archived == archived]

    def ids(self, project, archived: bool = False) -> list[Candidate]:
        return [(s.id, f"{s.title}  ({s.status})") for s in self.stories(project, archived)]

    def columns(self, project) -> list[Candidate]:
        store = self.store(project)
        if store is None:
            return []
        return [(c.key, c.label) for c in store.config.columns]

    def tags(self, project) -> list[Candidate]:
        counts: dict[str, int] = {}
        for s in self.stories(project, archived=False):
            for t in s.tags:
                counts[t] = counts.get(t, 0) + 1
        return [(t, f"{n} stor{'y' if n == 1 else 'ies'}") for t, n in sorted(counts.items())]

    def authors(self, project) -> list[Candidate]:
        names = {"agent"}
        for s in self.stories(project, archived=False):
            if s.assignee:
                names.add(s.assignee)
        me = self.ws.user.get("author")
        if me:
            names.add(me)
        return [(n, "") for n in sorted(names)]

    def projects(self) -> list[Candidate]:
        return [(e["name"], e["path"]) for e in self.ws.registry.entries()]

    def templates(self, project) -> list[Candidate]:
        store = self.store(project)
        return [(t, "template") for t in store.templates()] if store else []

    def refs(self, project) -> list[Candidate]:
        store = self.store(project)
        repo = gitutil.root(store.dir) if store else None
        if repo is None:
            return []
        return [(b["name"], "remote branch" if b["remote"] else "branch") for b in gitutil.branches(repo)]

    def facet_keys(self, project) -> list[Candidate]:
        keys: dict[str, int] = {}
        for s in self.stories(project, archived=False):
            for t in s.tags:
                if ":" in t:
                    k = t.split(":", 1)[0]
                    keys[k] = keys.get(k, 0) + 1
        return [(k, f"{n} tagged") for k, n in sorted(keys.items())]

    def source(self, name: str, project) -> list[Candidate]:
        if name == "projects":
            return self.projects()
        if name == "columns":
            return self.columns(project)
        if name == "templates":
            return self.templates(project)
        if name == "refs":
            return self.refs(project)
        if name == "authors":
            return self.authors(project)
        if name == "tags":
            return self.tags(project)
        if name == "ids":
            return self.ids(project)
        if name == "kinds":
            return [(k, "note kind") for k in NOTE_KINDS]
        if name == "releases":
            seen: dict[str, int] = {}
            for s in self.stories(project, archived=True):
                if s.released:
                    seen[s.released] = seen.get(s.released, 0) + 1
            return [(v, f"{n} stor{'y' if n == 1 else 'ies'}") for v, n in sorted(seen.items(), reverse=True)]
        return []

    # -- the walk -----------------------------------------------------------

    def complete(self, words: list[str], cword: int) -> list[Candidate]:
        """Candidates for ``words[cword]`` given the words before it."""
        words = list(words)
        while len(words) <= cword:
            words.append("")
        cur = words[cword]
        before = words[:cword]

        # Global options: -p NAME / --project NAME, then the command.
        project = None
        i = 0
        command = None
        while i < len(before):
            w = before[i]
            if w in ("-p", "--project"):
                project = before[i + 1] if i + 1 < len(before) else None
                i += 2
                continue
            if w.startswith("--project="):
                project = w.split("=", 1)[1]
                i += 1
                continue
            if w.startswith("-"):
                i += 1
                continue
            command = w
            i += 1
            break
        rest = before[i:]

        prev = before[-1] if before else ""
        if command is None:
            if prev in ("-p", "--project"):
                return self._filter(self.projects(), cur)
            if cur.startswith("-"):
                return self._filter([("-p", "act on a registered project"), ("--project", "act on a registered project"),
                                     ("--version", "print the version"), ("--help", "show help")], cur)
            names = [(n, c["help"]) for n, c in self.reference.items() if not n.startswith("_")]
            return self._filter(names, cur)

        if command == "mv":  # hidden alias
            command = "move"
        spec = self.reference.get(command)
        if spec is None:
            return []
        return self._filter(self._for_command(command, spec, rest, cur, prev, project), cur)

    def _for_command(self, command, spec, rest, cur, prev, project) -> list[Candidate]:
        flags = _flags_of(spec)
        # A flag that takes a value: complete the value.
        if prev in flags and flags[prev][0]:
            takes, choices, _ = flags[prev]
            if choices:
                return [(c, "") for c in choices]
            src = FLAG_SOURCES.get(prev)
            if src in ("tags", "ids") and prev in ("--tags", "--blocked-by"):
                return self._comma(self.source(src, project), cur)
            return self.source(src, project) if src else []
        if "=" in cur and cur.startswith("--"):
            name, val = cur.split("=", 1)
            if name in flags and flags[name][0]:
                inner = self._for_command(command, spec, rest + [name], val, name, project)
                return [(f"{name}={v}", d) for v, d in self._filter(inner, val)]
        if cur.startswith("-") and command not in ("tag", "block"):
            used = set(rest)
            return [(f, h) for f, (takes, _, h) in flags.items() if f not in used or takes]

        # Positionals: count the ones already given (skipping flags and their values).
        pos = []
        j = 0
        while j < len(rest):
            w = rest[j]
            if w in flags:
                j += 2 if flags[w][0] else 1
                continue
            if w.startswith("-") and command not in ("tag", "block"):
                j += 1
                continue
            pos.append(w)
            j += 1
        n = len(pos)

        if command in ("tag", "block"):
            if n == 0:
                return self.ids(project)
            story = self._story(project, pos[0])
            if command == "tag":
                have = set(story.tags) if story else set()
                add = [("+" + t, d) for t, d in self.tags(project) if t not in have]
                remove = [("-" + t, "remove") for t in sorted(have)]
                return add + remove
            have = set(story.blocked_by) if story else set()
            others = [("+" + i, d) for i, d in self.ids(project) if i != (story.id if story else None) and i not in have]
            remove = [("-" + b, "unblock") for b in sorted(have)]
            return others + remove
        if command == "move":
            return self.ids(project) if n == 0 else (self.columns(project) if n == 1 else [])
        if command == "set":
            if n == 0:
                return self.ids(project)
            if cur.startswith("assignee="):
                return [("assignee=" + a, d) for a, d in self.authors(project)]
            return [(k, d) for k, d in SET_KEYS.items()]
        if command == "unarchive":
            return self.ids(project, archived=True) if n == 0 else []
        if command == "archive":
            done = [(s.id, f"{s.title}  ({s.status})") for s in self.stories(project, archived=False)
                    if self._store and self._store.config.is_terminal(s.status)]
            return [c for c in done if c[0] not in pos]
        if command in ID_COMMANDS:
            return self.ids(project) if n == 0 else []
        if command == "facets":
            return self.facet_keys(project) if n == 0 else []
        if command == "config":
            if n == 0:
                return [(k, d) for k, d in CONFIG_KEYS.items()]
            if n == 1 and pos[0] == "push":
                return [("true", ""), ("false", "")]
            return []
        if command == "projects":
            if n == 0:
                return [("rm", "forget a project (files are untouched)"),
                        ("use", "make this checkout the project's primary")]
            if pos[0] == "rm" and n == 1:
                return self.projects()
            return []
        if command in ("hooks", "completion", "server"):
            if n == 0:
                positional = _positionals_of(spec)
                if positional and positional[0]["choices"]:
                    return [(c, "") for c in positional[0]["choices"]]
                return [(s["name"].split()[-1], s["help"]) for s in spec["subcommands"]]
            return []
        return []

    def _story(self, project, ref):
        store = self.store(project)
        if store is None:
            return None
        try:
            return store.get(ref)
        except SkaldError:
            return None

    @staticmethod
    def _comma(cands: list[Candidate], cur: str) -> list[Candidate]:
        """Complete the last item of a comma-separated list, keeping the earlier ones."""
        head, _, tail = cur.rpartition(",")
        if not head:
            return cands
        chosen = set(head.split(","))
        return [(f"{head},{v}", d) for v, d in cands if v not in chosen]

    @staticmethod
    def _filter(cands: list[Candidate], cur: str) -> list[Candidate]:
        seen = set()
        out = []
        for v, d in cands:
            if v.startswith(cur) and v not in seen:
                seen.add(v)
                out.append((v, d))
        return out


def complete(ws: Workspace, words: list[str], cword: int) -> list[Candidate]:
    from .cli import command_reference

    return Completer(ws, command_reference()).complete(words, cword)


# -- shell scripts ------------------------------------------------------------

BASH = r'''# skald completion for bash. Install with:  eval "$(skald completion bash)"
_skald_candidates() {
  local IFS=$'\n' cword="$1"; shift
  COMPREPLY=($(skald _complete -- "$cword" "$@" 2>/dev/null | cut -f1))
}
_skald() {
  _skald_candidates "$((COMP_CWORD - 1))" "${COMP_WORDS[@]:1}"
  type __ltrim_colon_completions >/dev/null 2>&1 && __ltrim_colon_completions "${COMP_WORDS[COMP_CWORD]}"
}
_git_skald() {
  _skald_candidates "$((COMP_CWORD - 2))" "${COMP_WORDS[@]:2}"
}
complete -o default -F _skald skald
'''

ZSH = r'''#compdef skald
# skald completion for zsh. Install with:  eval "$(skald completion zsh)"
_skald() {
  local -a lines pairs
  local line val desc
  lines=("${(@f)$(skald _complete -- $((CURRENT - 2)) "${words[@]:1}" 2>/dev/null)}")
  for line in "${lines[@]}"; do
    [[ -z "$line" ]] && continue
    val="${line%%$'\t'*}"
    desc="${line#*$'\t'}"
    [[ "$desc" == "$line" ]] && desc=""
    pairs+=("${val//:/\\:}:${desc}")
  done
  (( ${#pairs} )) && _describe -t skald 'skald' pairs
}
_git-skald() { _skald "$@" }
compdef _skald skald
'''

FISH = r'''# skald completion for fish. Install with:  skald completion fish > ~/.config/fish/completions/skald.fish
function __skald_complete --argument-names skip
  set -l toks (commandline -opc)
  set -l cur (commandline -ct)
  set -l words $toks[(math $skip + 1)..-1] $cur
  skald _complete -- (math (count $words) - 1) $words 2>/dev/null
end
complete -c skald -f -a '(__skald_complete 1)'
complete -c git -n '__fish_seen_subcommand_from skald' -f -a '(__skald_complete 2)'
'''

SCRIPTS = {"bash": BASH, "zsh": ZSH, "fish": FISH}
