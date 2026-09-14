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
| `release:<v>` | `skald release`, which warns about a story tagged for the version that is not done yet; the board filter | you are planning what a version should carry |

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

## Inventing your own

A new `key:value` tag is a facet the moment you write it: `skald facets`
lists it with per-value done and open counts, the board gives it a filter
and a swimlane, `skald ls --tag key:value` selects it, and `skald next
--tag key:value` routes by it. Add it to `facet_limits` to make it a lane.
Facets are cheap, so prefer one over a new field or a new column when you
just need to slice the board a different way.
