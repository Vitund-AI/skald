# Skald

This repository tracks work with Skald. Read `.skald/AGENTS.md` before starting any task.

- The package lives in `src/skald/`. Install it for development with `pip install -e .`.
- Run `python3 -m unittest` before committing. Standard library only, Python 3.10+.
- `src/skald/templates/AGENTS.md` is the agent contract template. After changing it, copy it over `.skald/AGENTS.md`; a test fails if the two differ.
- The design lives in `SPEC.md`, the reasoning in `DECISIONS.md`. Keep `SPEC.md`, `README.md`, `CHANGELOG.md`, and the `AGENTS.md` template in sync when behaviour changes, and add a numbered entry to `DECISIONS.md` for any non-obvious choice.
