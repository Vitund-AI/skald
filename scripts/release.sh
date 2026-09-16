#!/usr/bin/env bash
# Release Skald: the sequence in docs/git-and-ci.md, checked at every step.
#
#   scripts/release.sh 1.2.0            # do it
#   scripts/release.sh 1.2.0 --dry-run  # run every check and the release preview; change nothing
#   scripts/release.sh 1.2.0 --yes      # no confirmation prompts
#
# What it does, in order, stopping at the first thing that is not as expected:
#   1. checks: on dev, clean tree, in step with origin/dev, version well-formed and newer,
#      tag absent, gh available, something to release
#   2. skald release --dry-run, shown for confirmation
#   3. bumps src/skald/__init__.py, runs skald release, commits the bump, runs the tests
#   4. pushes dev, opens the pull request dev -> main, waits for its checks, merges it
#   5. tags the merge commit vX.Y.Z, skipping the render job's [skip ci] commit,
#      and pushes the tag; the publish workflow takes it from there
#   6. merges main back into dev (the render job commits on main) and pushes
set -euo pipefail

VERSION=""
DRY_RUN=0
YES=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes) YES=1 ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
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

# ---- 1. checks --------------------------------------------------------------
say "checks"
[ -n "$VERSION" ] || fail "usage: scripts/release.sh X.Y.Z [--dry-run] [--yes]"
case "$VERSION" in v*) fail "give the version without the v: ${VERSION#v} (the v belongs to the tag)" ;; esac
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "version must look like 1.2.0 (got $VERSION)"

CURRENT="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$VERSION_FILE")"
[ -n "$CURRENT" ] || fail "cannot read __version__ from $VERSION_FILE"
[ "$VERSION" != "$CURRENT" ] || fail "$VERSION is already the version in $VERSION_FILE"
[ "$(printf '%s\n%s\n' "$CURRENT" "$VERSION" | sort -V | tail -1)" = "$VERSION" ] || fail "$VERSION is older than the current $CURRENT"
echo "version: $CURRENT -> $VERSION"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" = dev ] || fail "run from dev (on $BRANCH)"
[ -z "$(git status --porcelain)" ] || fail "the working tree is not clean; commit or stash first"
git fetch --quiet origin dev main --tags
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/dev)" ] || fail "dev is not in step with origin/dev; pull or push first"
echo "branch: dev, clean, in step with origin"

! git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null || fail "tag v$VERSION already exists locally"
! git ls-remote --exit-code --tags origin "v$VERSION" >/dev/null 2>&1 || fail "tag v$VERSION already exists on origin"
echo "tag: v$VERSION is free"

command -v "$SKALD" >/dev/null || fail "$SKALD is not on PATH (pip install -e .)"
command -v "$GH" >/dev/null || fail "the gh CLI is needed for the pull request to main (https://cli.github.com)"
"$GH" auth status >/dev/null 2>&1 || fail "gh is not logged in (gh auth login)"
echo "tools: $SKALD, $GH"

# ---- 2. the release preview -------------------------------------------------
say "skald release $VERSION --dry-run"
"$SKALD" release "$VERSION" --dry-run

if [ "$DRY_RUN" = 1 ]; then
  say "dry run: every check passed; nothing was changed"
  echo "next: scripts/release.sh $VERSION"
  exit 0
fi
confirm "Release $VERSION with this section?"

# ---- 3. bump, release, test -------------------------------------------------
say "bump $VERSION_FILE and run the release"
sed -i.bak "s/^__version__ = \"$CURRENT\"$/__version__ = \"$VERSION\"/" "$VERSION_FILE" && rm -f "$VERSION_FILE.bak"
grep -q "^__version__ = \"$VERSION\"$" "$VERSION_FILE" || fail "the bump did not take"
"$SKALD" release "$VERSION"
git add "$VERSION_FILE"
git commit --quiet -m "Bump to $VERSION"

say "tests"
python3 -m unittest || fail "tests failed after the release commit; dev is untouched on origin, fix and rerun"

# ---- 4. push dev, pull request to main --------------------------------------
say "push dev and open the pull request to main"
git push origin dev
PR_URL="$("$GH" pr create --base main --head dev --title "Release $VERSION" \
  --body "Release $VERSION: the changelog section, released stamps, and archive from \`skald release\`, and the version bump. Tag v$VERSION follows the merge." )"
echo "$PR_URL"
say "waiting for the checks on the pull request"
"$GH" pr checks "$PR_URL" --watch --fail-fast || fail "a check failed on the pull request; fix on dev and rerun from step 4 by hand"
confirm "Checks passed. Merge $PR_URL into main?"
"$GH" pr merge "$PR_URL" --merge

# ---- 5. tag main ------------------------------------------------------------
say "tag main"
git checkout --quiet main
git pull --quiet origin main
MAIN_VERSION="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$VERSION_FILE")"
[ "$MAIN_VERSION" = "$VERSION" ] || fail "main carries version $MAIN_VERSION, not $VERSION; the tag would be refused"

# The publish workflow triggers on the tag push, but GitHub skips every
# workflow for a push whose head commit message carries a skip instruction
# ([skip ci] and its documented variants) -- a tag push included. The skald
# render job commits a "[skip ci]" render onto main right after the merge,
# so main's HEAD is usually that commit. Tag the newest ancestor that is not
# a skip commit -- the merge commit, which carries the version bump -- so the
# tag push actually runs the workflow.
skips_ci() {  # true if the commit's message tells GitHub Actions to skip
  git log -1 --format='%B' "$1" | grep -qiF \
    -e '[skip ci]' -e '[ci skip]' -e '[no ci]' \
    -e '[skip actions]' -e '[actions skip]' -e '***no_ci***'
}
TAG_TARGET="$(git rev-parse HEAD)"
while skips_ci "$TAG_TARGET"; do
  echo "skipping [skip ci] commit $(git rev-parse --short "$TAG_TARGET"); tagging its parent instead"
  TAG_TARGET="$(git rev-parse "$TAG_TARGET^")"
done
TARGET_VERSION="$(git show "$TAG_TARGET:$VERSION_FILE" | sed -n 's/^__version__ = "\(.*\)"$/\1/p')"
[ "$TARGET_VERSION" = "$VERSION" ] || fail "the runnable commit $(git rev-parse --short "$TAG_TARGET") carries version $TARGET_VERSION, not $VERSION; tag by hand"

git tag -a "v$VERSION" -m "Release $VERSION" "$TAG_TARGET"
git push origin "v$VERSION"
echo "tag v$VERSION pushed at $(git rev-parse --short "$TAG_TARGET"); approve the publish job at:"
echo "  $("$GH" repo view --json url -q .url)/actions/workflows/publish.yml"

# ---- 6. main back into dev --------------------------------------------------
say "merge main back into dev"
git checkout --quiet dev
git merge --quiet main -m "Merge main after release $VERSION"
git push origin dev

say "released $VERSION"
