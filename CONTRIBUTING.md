# Contributing to Skald

Thanks for considering it. Skald is small on purpose: one Python package
with no dependencies beyond the standard library, a CLI, a local board, and
a set of Markdown story files. Contributions that keep it that way are the
easiest to merge.

## Before you start

- Read the [README](README.md) for what Skald is, and
  [SPEC.md](SPEC.md) for how it is designed. [DECISIONS.md](DECISIONS.md)
  explains the choices that are not obvious; if you are about to reverse
  one, read its entry first and say why in your proposal.
- Open an issue for anything larger than a fix, so the shape is agreed
  before the work is done. Bug reports with the command you ran, what
  happened, and what you expected are the most useful kind.
- This project follows a [code of conduct](CODE_OF_CONDUCT.md).

## Setting up

```sh
git clone https://github.com/Vitund-AI/skald.git
cd skald
pip install -e .
python -m unittest              # the test suite, standard library only
pip install ruff && ruff check src tests examples
```

Python 3.9 or newer, and git. The suite runs in CI on Linux for Python 3.9
to 3.13 and on macOS and Windows, so a change that passes locally on one
platform can still fail there; the run on your pull request is the check.
If a test depends on the platform (line endings, path separators, an older
`datetime`), say so in a comment.

## The story workflow

This repository tracks its own work with Skald, and contributors use it the
same way agents do. The contract is [.skald/AGENTS.md](.skald/AGENTS.md); the
short version:

1. `skald context --as <your-name>` to see what is assigned and waiting.
2. Create a story for your change, or claim an existing one:
   `skald new "Title" --as <you> --status in_progress`, or
   `skald claim <id> --as <you>`.
3. Put acceptance criteria under `## Acceptance` as a checklist and tick
   them as you verify each. Record decisions with
   `skald note <id> "..." --kind decision`.
4. Commit story files with the code they describe, with a
   `Skald-Story: <id>` trailer in the commit message.
5. When done, `skald move <id> review` with a closing note that says what
   changed and how it was verified. A maintainer moves stories to done.

The board for this repository is at [.skald/README.md](.skald/README.md),
and `skald serve` opens the live one.

## Making the change

- **Branches and pull requests.** Work lands on `dev` through pull requests;
  `main` carries releases. Open your pull request against `dev`.
- **Keep the documents in sync.** A change in behaviour touches
  `SPEC.md`, the user docs under `docs/`, `README.md`, and `CHANGELOG.md`
  (under an `Unreleased` heading). A non-obvious choice gets a numbered
  entry in `DECISIONS.md`. After changing a command, run `skald docs` to
  regenerate `docs/cli.md`; a test fails if it is stale.
- **The agent contract** lives in `src/skald/templates/AGENTS.md`. After
  editing it, copy it over `.skald/AGENTS.md` and update the copy in
  `.claude/skills/skald/SKILL.md`; a test fails if the template and its
  copy differ.
- **No runtime dependencies.** The package imports the standard library
  only. Development tools such as ruff are fine; a new import in
  `src/skald/` is not, and a pull request that adds one will be asked to do
  without it.
- **Tests.** Every change comes with a test, in the module that matches the
  layer: `test_store.py` for the story model, `test_cli.py` for commands,
  `test_server.py` for the HTTP API, `test_mcp.py` for the MCP tools.
  Tests create their own temporary repositories through the helpers in
  `tests/helpers.py`.
- **Commits.** A subject line that says what changed and why, a body when
  the why needs more than a line, and the `Skald-Story` trailer.

## Releases

Maintainers release from `dev`: `skald release X.Y.Z` turns the done
column into a changelog section and archives the stories, `dev` merges to
`main`, and a `vX.Y.Z` tag publishes to PyPI. Contributors do not need to
touch versions or the changelog headings; an entry under `Unreleased` is
enough.

## Licence

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE) that covers the project.
