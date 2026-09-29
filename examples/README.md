# Examples

Worked setups on top of the core, each in its own directory with a README.
They are written against the Skald version in this repository and are
tested for at least compiling and running; copy what fits.

| Example | What it shows |
| --- | --- |
| [model-routing](model-routing/) | Route stories to model-pinned Claude Code subagents by an `effort:` tag, drain the backlog through them with an executive skill, and report which tier finished what. |
| [github-issues](github-issues/) | Pull a repository's GitHub issues into the backlog, one way and safe to re-run: `gh:<number>` tags prevent duplicates, labels become tags, comments become notes, and drift between the two is reported rather than overwritten. |
