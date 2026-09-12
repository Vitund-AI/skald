#!/usr/bin/env bash
# Build the demo project the README screenshots show: a WireGuard overlay backlog on the
# lifecycle columns, with an epic and its children, a claimed story with a checklist and a
# handoff, questions waiting on a human, a blocked story, and two done ones.
#
#   docs/images/make-demo.sh /tmp/wireguard-overlay && (cd /tmp/wireguard-overlay && skald serve)
set -euo pipefail
D="${1:?usage: make-demo.sh DIR}"
rm -rf "$D" && mkdir -p "$D" && cd "$D"
git init -q && git -c user.name=jon -c user.email=jon@example.com commit -q --allow-empty -m "init"
skald init --columns lifecycle >/dev/null
n() { skald new "$@"; }

EPIC=$(n "WireGuard overlay network" --status in_progress --tags infra,epic:overlay --created-at "2026-08-20 09:00" --body "## Requirements

Every host in the fleet reaches every other over an encrypted overlay, with peers discovered automatically and keys rotated without downtime.

## Acceptance

- [x] design agreed
- [ ] peers discover each other
- [ ] keys rotate on a schedule")
IMPL=$(n "Implement WireGuard overlay" --status in_progress --tags infra --parent "$EPIC" --assignee claude --created-at "2026-08-22 10:00" --body "## Requirements

Bring up wg0 on every host from the generated config and verify a full mesh.

## Acceptance

- [x] wg0 up on one host
- [x] config generated from the inventory
- [ ] full mesh verified
- [ ] handshake failures logged")
DISC=$(n "Peer discovery via DNS" --status review --tags infra --parent "$EPIC" --assignee sonnet --created-at "2026-08-25 14:00" --body "## Requirements

Publish each peer's endpoint and public key as a DNS record; hosts resolve their peers at start and every ten minutes.

## Acceptance

- [x] records published
- [x] hosts resolve peers
- [x] refresh interval configurable")
n "Rotate keys on a schedule" --status idea --tags infra,security --parent "$EPIC" --created-at "2026-08-28 11:00" >/dev/null
n "Write the network docs" --status ready --tags docs --blocked-by "$IMPL" --created-at "2026-08-26 09:30" >/dev/null
CFG=$(n "Design the config format" --status plan --tags design --created-at "2026-08-27 16:00" --body "## Requirements

One file per host, generated from the inventory, human-readable, diffable in review.

## Design

TOML or YAML; a section per peer; secrets referenced, never inline.")
HEALTH=$(n "Add a health endpoint" --status ready --tags ops --created-at "2026-08-29 08:15")
n "Prometheus exporter for tunnel metrics" --status idea --tags observability --created-at "2026-09-01 12:00" >/dev/null
n "Set up CI" --status done --tags ops --created-at "2026-08-18 10:00" >/dev/null
DB=$(n "Choose the state store" --status done --tags design --created-at "2026-08-19 10:00")
MULTI=$(n "Multi-region routing" --status plan --tags infra,epic:overlay --created-at "2026-09-02 10:00" --body "## Requirements

Route between regions over the overlay without a hairpin through one hub.")

skald note "$DB" "SQLite, one file per host, committed. Postgres would be a service to run." --as jon --kind decision --at "2026-08-19 15:00" >/dev/null
skald note "$IMPL" "wg0 is up on host-01 with the generated config; mesh verification next. Handshake logging depends on the log format in the config story." --as claude --kind handoff --at "2026-09-03 17:40" >/dev/null
skald note "$CFG" "TOML or YAML? The inventory is YAML today, but TOML reads better for a section per peer." --as claude --kind question --at "2026-09-02 11:20" >/dev/null
skald note "$CFG" "Should secrets be referenced by path or by name in a vault?" --as claude --kind question --at "2026-09-02 11:25" >/dev/null
skald note "$MULTI" "Is a hub per region acceptable for the first version?" --as claude --kind question --at "2026-09-03 09:10" >/dev/null
skald note "$DISC" "Records published for all 12 hosts; refresh interval defaults to 600s, configurable. Ready for review." --as sonnet --kind result --at "2026-09-04 15:05" >/dev/null
skald note "$HEALTH" "Blocked on nothing; picks up after the overlay lands." --as jon --at "2026-08-30 09:00" >/dev/null
skald note "$EPIC" "Discovery is in review and the mesh is half up; key rotation stays an idea until the config format is settled." --as jon --at "2026-09-11 16:30" >/dev/null
git add -A && git -c user.name=jon -c user.email=jon@example.com commit -q -m "Backlog for the overlay"
echo "demo project at $D: $(basename "$D")"
