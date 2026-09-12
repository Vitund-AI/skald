# Model routing: which model should work this story, and which one did

A worked example, not a feature. Skald has no model field and no token
counter, on purpose (see DECISIONS.md, D61). Everything here is a
convention over tags and note authors, plus a Claude Code setup that
acts on it. Copy what fits; the pieces are independent.

## The convention

**Intent** is a facet tag on the story, set when the story is planned:

```sh
skald new "Rework the placement solver" --status ready --tags effort:deep
skald tag a3f9c2 +effort:quick
```

Use a level of effort (`effort:deep`, `effort:quick`) rather than a model
name. Model names change every quarter; what the planner means is "this one
needs the expensive model" or "any model can do this", and that stays true
after the models are renamed. The tag shows on the card, filters on the
board, and `skald ls --tag effort:deep` lists them. A story with no tag is
for whichever agent gets to it first.

**Actuals** are the author label on every note and claim. Pass the model as
the name:

```sh
skald claim a3f9c2 --as fable-5.1-max
skald note a3f9c2 "..." --as fable-5.1-max --kind result
```

The story file now records which model decided what, when, and the
`SessionStart` hook and the board show the same label. No new field, and
the record reads without any tool.

**Cost** is not recorded. Skald cannot observe tokens; only the harness
running the agent can. If yours reports them, a note of kind `cost` with
the number is enough, and nothing in the core has to know about it.

## Routing with Claude Code subagents

`agents/` holds three subagent definitions for `.claude/agents/`, each
pinned to a model and effort level:

| File | Model | Takes |
| --- | --- | --- |
| `deep.md` | the strongest available, high effort | `effort:deep` |
| `standard.md` | the everyday model | untagged stories |
| `quick.md` | the fast model, low effort | `effort:quick` |

Each one claims and works a story under its own name, so the actuals land
in the notes without anyone remembering to set `--as`.

`skills/executive/SKILL.md` is the loop the top-level session runs. It asks
Skald for the next story per tier with `skald next --tag effort:deep --as
deep`, dispatches it to the matching subagent, and repeats until every tier
reports nothing ready. Skald does what it already does in that loop: hand out
unclaimed ready work, keep two agents off one story, and take the notes
back. The contract's rule that a story carrying an intent tag you do not
match is not yours applies to the subagents too; the executive is the one
that routes.

Install:

```sh
cp examples/model-routing/agents/*.md .claude/agents/
cp -r examples/model-routing/skills/executive .claude/skills/
```

Then, in a Claude Code session: `/executive`.

## Learning from it

`report.py` joins the intended tag with the authors of the notes that
finished each story and how long the story took, so after a few releases
you can see which shape of work the quick tier finished cleanly and which it
bounced back into review:

```sh
python3 examples/model-routing/report.py            # this project
python3 examples/model-routing/report.py --json     # for a spreadsheet
```

It reads story files through the `skald` package and runs `skald activity`
with the same interpreter, so run it with the Python that has Skald
installed. The output is one row per finished story: intended tier, the
labels that worked it, days from claim to done, and whether it went back
from review.

That table is the answer to "what shape of problem is best served by which
model", and it is the reason the intent tag and the actual author are worth
keeping distinct: the gap between them is the finding.
