---
title: "Keep Prettier off Skald's files: add .skald/ to .prettierignore on init, and doctor warns when it is missing"
status: "idea"
rank: 130
tags: ["area:cli", "roadmap"]
blocked_by: []
created_at: "2026-11-11T02:01:06Z"
updated_at: "2026-11-11T02:01:06Z"
---
## Requirements

In a project that runs Prettier, `prettier --check .` fails on Skald's own
files, and `prettier --write .` rewrites them. Tried on this repository with
Prettier 3.6: 151 files under `.skald/` flagged. `--write`:

- pads the rendered board's tables and adds a blank line after the render
  marker, so `.skald/README.md` no longer matches its render hash and
  `skald check` calls it stale;
- changes `*emphasis*` to `_emphasis_`, re-indents list continuations
  (it pulled a wrapped line in `.skald/AGENTS.md` back to column 0), and
  adds blank lines around note headings in story files;
- leaves the front matter and `config.json` alone, so nothing breaks
  outright. But every story picks up a formatting diff that Skald's own
  next write partly undoes. That churn turns into noisy diffs and needless
  merge conflicts between branches.

These files are written by Skald in its own canonical layout, so they
should be ignored by formatters, as `node_modules/` is.

- `skald init` adds `.skald/` to `.prettierignore`:
  - when `.prettierignore` exists, append the line if no line already
    covers `.skald` (keep the file's line endings, and add a final newline
    if it lacks one);
  - when it does not exist, create it if the project shows signs of
    Prettier: a `.prettierrc*` or `prettier.config.*` file, or `prettier`
    in `package.json` (a `prettier` key or a dependency). A Python or Go
    repository with no Prettier gets no new file.
  - `skald init` already runs safely on an existing project, so rerunning
    it is the upgrade path; it says what it changed.
- `skald doctor` warns when the project shows signs of Prettier and
  `.skald/` is not ignored, with the line to add. That covers Prettier
  added after init.
- Docs: a short "Formatters" note in the getting-started or git page.
  Other formatters (markdownlint, dprint) are mentioned with the same
  advice, not handled automatically.

Decision to record (DECISIONS): Skald edits a file of the project's own
only when the tool it configures is in evident use. It does not create
`.prettierignore` in every project.

## Acceptance
- [ ] `skald init` appends `.skald/` to an existing `.prettierignore` (once, idempotent) and creates the file only when Prettier is evidently in use; it reports what it did.
- [ ] `skald doctor` warns when Prettier is in use and `.skald/` is not ignored.
- [ ] Tests for append, create, skip, already-present, and the doctor warning.
- [ ] Docs, SPEC, CHANGELOG updated; DECISIONS entry.
