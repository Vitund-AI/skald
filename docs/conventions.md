# Facet conventions

A tag written as `key:value` is a **facet**. Nothing in the story format
knows what any particular key means: the board gives every facet key a
filter and a swimlane option, and a handful of keys unlock more because a
command or a config setting reads them. This page lists the conventions that
have grown up, what each one turns on, and when to reach for it. None is
required, and you can invent your own.

| Facet | What reads it | Use it when |
| --- | --- | --- |
| `epic:<name>` | `skald epics` and `skald ls --tag epic:<name>`; the board's "swimlanes by epic" | you want to group related stories under a name without making a parent story |
| `lane:<name>` | `facet_limits` (a WIP cap per value), `skald status` busy lanes, and `skald next`, which skips a story whose lane is already busy | parallel agents need non-overlapping tracks, so at most N run in a lane at once |
| `effort:<tier>` | `skald next --tag effort:<tier>`; the [model-routing example](../examples/model-routing/) | you route a story to a class of agent (a model or cost tier); an agent skips a tier it does not match |
| `area:<name>` | grouping and filtering like any facet; `skald import` can set it automatically from a path or a label | you want to mark which part of the codebase a story touches |
| `release:<v>` | `skald release`, which warns about a story tagged for the version that is not done yet (or refuses outright when `block_release_on_incomplete` is set in `config.json`, unless `--allow-incomplete`); the board filter | you are planning what a version should carry |

`model:<name>` and cost are conventions too, carried by the note author and a
tag rather than a field, so the intended and the actual model can be joined
per story; the [model-routing example](../examples/model-routing/) shows the
whole setup, and [DECISIONS.md](../DECISIONS.md) D61 records why they stay
conventions instead of core fields.

## Making a facet a lane

Any facet becomes a WIP-limited lane by naming its key in `facet_limits` in
`.skald/config.json`:

```json
{ "facet_limits": { "lane": 1 } }
```

Now at most one story per `lane:` value may sit in an active column at a
time; `skald status` reports the busy lanes, `skald next` passes over a
story whose lane is taken, and the board turns a full lane's count red. See
[Stories](stories.md#lanes) for the worked example.

## Parking work you're not doing now

Work you've decided against *for now* — but that isn't a won't-do — is a flow
state, not a facet or a priority, so it belongs in a column, not a tag. Don't
reach for `area:deferred` or `priority:on-hold`: "is this in play?" isn't the
question those answer, and a card is either parked or in the flow (mutually
exclusive), which is the signature of a status.

The convention is an **Icebox** column with the `backlog` role — the `lifecycle`
preset ships one at the front of the board. Because it's `backlog`, parked work
never shows up in `skald next` or the ready view and is never swept into a
release, and reviving it is a drag back into the flow. Keep it distinct from
**won't-do** (a `closed` column): won't-do is a final, recorded decision that
lands in the changelog's "Not doing"; Icebox is temporary and comes back.

Since the Icebox leads the board, the preset also sets `default_status` to
`idea`, so new stories are captured in Idea rather than the leftmost column
(add your own to any config where the first column isn't the capture point).

One guideline, not enforced: **revive to Idea or Plan, not straight to Ready.**
A plan parked for a while may be stale; sending it back through grooming is the
chance to re-validate it before anyone executes it. Skald won't stop you moving
it twice — it just doesn't make the risky jump the easy one.

## Inventing your own

A new `key:value` tag is a facet the moment you write it: `skald facets`
lists it with per-value done and open counts, the board gives it a filter
and a swimlane, `skald ls --tag key:value` selects it, and `skald next
--tag key:value` routes by it. Add it to `facet_limits` to make it a lane.
Facets are cheap, so prefer one over a new field or a new column when you
just need to slice the board a different way.
