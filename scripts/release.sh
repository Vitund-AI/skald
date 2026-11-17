#!/usr/bin/env bash
# Release Skald: the sequence in docs/git-and-ci.md, checked at every step.
#
#   scripts/release.sh 1.2.0            # do it: one confirmation at the preview, then unattended
#   scripts/release.sh 1.2.0 --dry-run  # run every check and the release preview; change nothing
#   scripts/release.sh 1.2.0 --yes      # no confirmation at all
#   scripts/release.sh 1.2.0 --ask      # also stop for a yes before merging into main
#   scripts/release.sh 1.2.0 --resume   # finish a release that stopped partway, from where it stopped
#   scripts/release.sh 1.2.0 --allow-incomplete  # release even with stories still tagged for it
#
# What it does, in order, stopping at the first thing that is not as expected:
#   1. checks: on dev, clean, in step with origin/dev, main holds nothing dev lacks,
#      version well-formed and newer, tag absent, gh available, something to release
#   2. skald release --dry-run, shown for confirmation (the only stop, unless --ask)
#   3. bumps src/skald/__init__.py, runs skald release, commits the bump, runs the tests
#   4. pushes dev, opens (or reuses) the pull request dev -> main, waits for its checks, merges it
#   5. waits for main's render job, tags the merge commit vX.Y.Z (never a [skip ci] commit),
#      and pushes the tag
#   6. merges main back into dev and pushes, so the next release starts level
#   7. watches the publish workflow to the end and reports the result
# With --resume, steps 1-3 are replaced by working out which step the release reached.
set -euo pipefail

VERSION=""
DRY_RUN=0
YES=0
ASK=0
RESUME=0
ALLOW_INCOMPLETE=""   # a fixed flag word or empty; expanded unquoted below (safe on bash 3.2 with set -u)
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes) YES=1 ;;
    --ask) ASK=1 ;;
    --resume) RESUME=1 ;;
    --allow-incomplete) ALLOW_INCOMPLETE="--allow-incomplete" ;;
    -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) VERSION="$arg" ;;
  esac
done

SKALD="${SKALD:-skald}"
GH="${GH:-gh}"   # overridable so the dry run can be exercised without GitHub
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
VERSION_FILE="src/skald/__init__.py"

say()  { printf '\n==> %s\n' "$*"; }
fail() { printf 'release: %s\n' "$*" >&2; exit 1; }
confirm() {
  [ "$YES" = 1 ] && return 0
  read -r -p "$1 [y/N] " answer
  [ "$answer" = y ] || [ "$answer" = Y ] || fail "stopped"
}
version_at() {  # the __version__ a ref carries, or empty
  git show "$1:$VERSION_FILE" 2>/dev/null | sed -n 's/^__version__ = "\(.*\)"$/\1/p'
}
resume_hint() { echo "fix it, then: scripts/release.sh $VERSION --resume"; }

# ---- 1. checks --------------------------------------------------------------
say "checks"
[ -n "$VERSION" ] || fail "usage: scripts/release.sh X.Y.Z [--dry-run] [--yes] [--ask] [--resume]"
case "$VERSION" in v*) fail "give the version without the v: ${VERSION#v} (the v belongs to the tag)" ;; esac
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "version must look like 1.2.0 (got $VERSION)"

CURRENT="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$VERSION_FILE")"
[ -n "$CURRENT" ] || fail "cannot read __version__ from $VERSION_FILE"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" = dev ] || fail "run from dev (on $BRANCH)"
[ -z "$(git status --porcelain)" ] || fail "the working tree is not clean; commit or stash first"
git fetch --quiet origin dev main --tags

TAG_ON_ORIGIN=0
git ls-remote --exit-code --tags origin "v$VERSION" >/dev/null 2>&1 && TAG_ON_ORIGIN=1

# Where the release stands: start (nothing done), pr (bumped, maybe pushed, maybe a PR open),
# tag (merged into main, not tagged), back (tagged, main not yet merged back into dev).
if [ "$RESUME" = 0 ]; then
  STAGE="start"
  [ "$VERSION" != "$CURRENT" ] || fail "$VERSION is already the version in $VERSION_FILE; to finish a release that stopped, add --resume"
  [ "$(printf '%s\n%s\n' "$CURRENT" "$VERSION" | sort -V | tail -1)" = "$VERSION" ] || fail "$VERSION is older than the current $CURRENT"
  echo "version: $CURRENT -> $VERSION"
  [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/dev)" ] || fail "dev is not in step with origin/dev; pull or push first"
  ! git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null || fail "tag v$VERSION already exists locally"
  [ "$TAG_ON_ORIGIN" = 0 ] || fail "tag v$VERSION already exists on origin"
  echo "branch: dev, clean, in step with origin"
  echo "tag: v$VERSION is free"
else
  [ "$CURRENT" = "$VERSION" ] || fail "nothing to resume: $VERSION_FILE reads $CURRENT, not $VERSION; run without --resume to start the release"
  if [ "$TAG_ON_ORIGIN" = 1 ]; then
    STAGE="back"
  elif [ "$(version_at origin/main)" = "$VERSION" ]; then
    STAGE="tag"
  else
    STAGE="pr"
    # Local commits not yet pushed are fine (a run that stopped before the push); behind is not.
    git merge-base --is-ancestor origin/dev HEAD || fail "dev is behind or diverged from origin/dev; pull first"
  fi
  case "$STAGE" in
    pr)   echo "resume from: step 4, push dev and the pull request to main" ;;
    tag)  echo "resume from: step 5, tag main (the pull request is merged)" ;;
    back) echo "resume from: step 6, merge main back into dev (v$VERSION is tagged)" ;;
  esac
fi

# main must hold no change dev lacks, or the pull request to main can conflict (the render job's
# commits on main, a hotfix): merge it into dev first. Commits that change nothing, such as the
# merge of the last release pull request, are let through: merging main would leave dev's files
# exactly as they are, and step 6 merges them back. Not needed once the release is merged.
if [ "$STAGE" = start ] || [ "$STAGE" = pr ]; then
  AHEAD="$(git log --oneline HEAD..origin/main)"
  if [ -z "$AHEAD" ]; then
    echo "main: nothing that dev lacks"
  elif MERGED="$(git merge-tree --write-tree HEAD origin/main 2>/dev/null | head -1)" \
       && [ "$MERGED" = "$(git rev-parse 'HEAD^{tree}')" ]; then
    # merge-tree (git 2.38+) exits non-zero on a conflict or on an older git: both refuse below.
    echo "main: $(printf '%s\n' "$AHEAD" | wc -l | tr -d ' ') commit(s) that dev lacks, none changing a file; the release merges them back"
  else
    printf 'main has changes that dev lacks:\n%s\n' "$AHEAD" >&2
    fail "merge them into dev first: git merge origin/main && git push origin dev (if .skald/README.md conflicts, run skald render and add it)"
  fi
fi

command -v "$SKALD" >/dev/null || fail "$SKALD is not on PATH (pip install -e .)"
command -v "$GH" >/dev/null || fail "the gh CLI is needed for the pull request to main (https://cli.github.com)"
"$GH" auth status >/dev/null 2>&1 || fail "gh is not logged in (gh auth login)"
echo "tools: $SKALD, $GH"

# ---- 2. the release preview -------------------------------------------------
if [ "$STAGE" = start ]; then
  say "skald release $VERSION --dry-run"
  "$SKALD" release "$VERSION" --dry-run $ALLOW_INCOMPLETE
fi

if [ "$DRY_RUN" = 1 ]; then
  say "dry run: every check passed; nothing was changed"
  if [ "$RESUME" = 1 ]; then echo "next: scripts/release.sh $VERSION --resume"; else echo "next: scripts/release.sh $VERSION"; fi
  exit 0
fi
if [ "$STAGE" = start ]; then
  confirm "Release $VERSION with this section? After this the release runs to the end on its own."
fi

# ---- 3. bump, release, test -------------------------------------------------
if [ "$STAGE" = start ]; then
  say "bump $VERSION_FILE and run the release"
  sed -i.bak "s/^__version__ = \"$CURRENT\"$/__version__ = \"$VERSION\"/" "$VERSION_FILE" && rm -f "$VERSION_FILE.bak"
  grep -q "^__version__ = \"$VERSION\"$" "$VERSION_FILE" || fail "the bump did not take"
  "$SKALD" release "$VERSION" $ALLOW_INCOMPLETE
  git add "$VERSION_FILE"
  git commit --quiet -m "Bump to $VERSION"
fi
if [ "$STAGE" = start ] || [ "$STAGE" = pr ]; then
  say "tests"
  python3 -m unittest || fail "tests failed; nothing is pushed yet. $(resume_hint)"
fi

# ---- 4. push dev, pull request to main --------------------------------------
if [ "$STAGE" = start ] || [ "$STAGE" = pr ]; then
  say "push dev and open the pull request to main"
  git push origin dev
  HEAD_SHA="$(git rev-parse HEAD)"
  PR_URL="$("$GH" pr list --base main --head dev --state open --json url --jq '.[0].url // empty')"
  if [ -n "$PR_URL" ]; then
    echo "reusing $PR_URL"
  else
    PR_URL="$("$GH" pr create --base main --head dev --title "Release $VERSION" \
      --body "Release $VERSION: the changelog section, released stamps, and archive from \`skald release\`, and the version bump. Tag v$VERSION follows the merge." )"
    echo "$PR_URL"
  fi
  say "waiting for the checks on the pull request"
  # GitHub moves the pull request to the pushed commit, then registers its checks, a few seconds
  # apart. Until both happen `gh pr checks` reports the old commit or "no checks reported" (exit 1,
  # which --watch would take for a failure), so wait for them first.
  waited=0
  while :; do
    pr_head="$("$GH" pr view "$PR_URL" --json headRefOid --jq .headRefOid 2>/dev/null || true)"
    out="$("$GH" pr checks "$PR_URL" 2>&1 || true)"
    if [ "$pr_head" = "$HEAD_SHA" ]; then
      case "$out" in *"no checks reported"*) ;; *) break ;; esac
    fi
    [ "$waited" -lt 300 ] || fail "no checks appeared on $PR_URL after 5 minutes; check the workflows ran. $(resume_hint)"
    sleep 5
    waited=$((waited + 5))
  done
  "$GH" pr checks "$PR_URL" --watch --fail-fast || fail "a check failed on $PR_URL. Fix it on dev; $(resume_hint)"
  [ "$ASK" = 0 ] || confirm "Checks passed. Merge $PR_URL into main?"
  "$GH" pr merge "$PR_URL" --merge
  STAGE="tag"
fi

# ---- 5. tag main ------------------------------------------------------------
skips_ci() {  # true if the commit's message tells GitHub Actions to skip
  git log -1 --format='%B' "$1" | grep -qiF \
    -e '[skip ci]' -e '[ci skip]' -e '[no ci]' \
    -e '[skip actions]' -e '[actions skip]' -e '***no_ci***'
}
if [ "$STAGE" = tag ]; then
  say "tag main"
  git fetch --quiet origin main
  MERGE_SHA="$(git rev-parse origin/main)"
  # The skald workflow re-renders the board on main after a merge and may commit it. Let it finish,
  # so the tag and the merge back into dev both see main as it will stay.
  # Its run takes a few seconds to appear; if none has after a minute, there is none to wait for.
  waited=0
  while [ "$waited" -lt 600 ]; do
    counts="$("$GH" run list --workflow skald.yml --branch main --commit "$MERGE_SHA" --json status \
      --jq '"\(length) \([.[] | select(.status != "completed")] | length)"' 2>/dev/null || echo "0 0")"
    total="${counts%% *}"; pending="${counts##* }"
    if [ "${total:-0}" != 0 ] && [ "${pending:-0}" = 0 ]; then break; fi
    if [ "${total:-0}" = 0 ] && [ "$waited" -ge 60 ]; then break; fi
    sleep 10
    waited=$((waited + 10))
  done
  git checkout --quiet main
  git pull --quiet origin main
  [ "$(version_at HEAD)" = "$VERSION" ] || fail "main carries version $(version_at HEAD), not $VERSION; the tag would be refused"

  # A tag push whose head commit says [skip ci] runs no workflow at all, publish included, and
  # the render job's commit says exactly that. Tag the newest ancestor that does not: the merge
  # commit, which carries the version bump (D65).
  TAG_TARGET="$(git rev-parse HEAD)"
  while skips_ci "$TAG_TARGET"; do
    echo "skipping [skip ci] commit $(git rev-parse --short "$TAG_TARGET"); tagging its parent instead"
    TAG_TARGET="$(git rev-parse "$TAG_TARGET^")"
  done
  [ "$(version_at "$TAG_TARGET")" = "$VERSION" ] || fail "the runnable commit $(git rev-parse --short "$TAG_TARGET") carries version $(version_at "$TAG_TARGET"), not $VERSION; tag by hand"

  if git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null; then
    # Tagged here by a run that stopped before the push: push that tag if it is the right commit.
    [ "$(git rev-parse "v$VERSION^{commit}")" = "$TAG_TARGET" ] \
      || fail "a local tag v$VERSION points at another commit; delete it (git tag -d v$VERSION) and resume"
  else
    git tag -a "v$VERSION" -m "Release $VERSION" "$TAG_TARGET"
  fi
  git push origin "v$VERSION"
  echo "tag v$VERSION pushed at $(git rev-parse --short "$TAG_TARGET")"
  STAGE="back"
fi

# ---- 6. main back into dev --------------------------------------------------
if [ "$STAGE" = back ]; then
  say "merge main back into dev"
  git fetch --quiet origin dev main
  git checkout --quiet dev
  git pull --quiet origin dev
  git merge --quiet origin/main -m "Merge main after release $VERSION" \
    || fail "main did not merge cleanly into dev; resolve it (skald render for .skald/README.md), commit, and push dev"
  git push origin dev
fi

# ---- 7. publish -------------------------------------------------------------
say "watching the publish workflow"
RUN_ID=""
waited=0
while [ -z "$RUN_ID" ] && [ "$waited" -lt 120 ]; do
  RUN_ID="$("$GH" run list --workflow publish.yml --branch "v$VERSION" --limit 1 --json databaseId \
    --jq '.[0].databaseId // empty' 2>/dev/null || true)"
  [ -n "$RUN_ID" ] || { sleep 5; waited=$((waited + 5)); }
done
REPO_URL="$("$GH" repo view --json url -q .url)"
[ -n "$RUN_ID" ] || fail "no publish run appeared for v$VERSION; see $REPO_URL/actions/workflows/publish.yml"
echo "$REPO_URL/actions/runs/$RUN_ID (if the pypi environment still asks for approval, approve it there)"
"$GH" run watch "$RUN_ID" --exit-status >/dev/null \
  || fail "the publish run failed: $REPO_URL/actions/runs/$RUN_ID. The tag is pushed; fix the cause and re-run it (gh run rerun $RUN_ID --failed)"

say "released $VERSION"
