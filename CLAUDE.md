# Skald

This repository tracks work with Skald. Read `.skald/AGENTS.md` before starting any task.

- The root `skald.py` is the source of truth. After editing it, copy it over `.skald/skald.py`; a test fails if the two differ.
- Run `python3 -m unittest` before committing. Standard library only, Python 3.9+.
- The design lives in `SPEC.md`. Keep it, `README.md`, and the embedded `AGENTS_MD` template in sync when behaviour changes.
