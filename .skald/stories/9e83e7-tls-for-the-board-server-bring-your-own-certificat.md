---
title: "TLS for the board server: bring your own certificate via config"
status: "done"
rank: 20
tags: ["area:server", "roadmap", "security"]
blocked_by: []
assignee: "claude"
created_at: "2026-10-08T05:01:07Z"
updated_at: "2026-10-08T05:23:32Z"
---
## Requirements

A board bound to the network (`host 0.0.0.0`) speaks plain HTTP, so the key in the link, the session cookie, and every story cross the network unencrypted. A security-conscious user should be able to turn on HTTPS.

## Proposal: bring your own certificate, no generation
- Two machine-local settings, `tls_cert` and `tls_key` (paths to PEM files). When both are set, the server wraps its socket with `ssl.SSLContext(PROTOCOL_TLS_SERVER)`, standard library only, and serves HTTPS on the same port.
- All the CLI's printed URLs become `https://`. The session cookie gains `Secure`.
- The health probe, `start_server`, and `doctor` connect to `https://127.0.0.1`. The certificate won't name 127.0.0.1, so those loopback-only probes skip verification; they read only `/api/health`.
- `doctor` checks the files exist and are readable and the key is private (0600). Starting with only one of the two set is an error, not a silent fall back to HTTP.
- Docs: making a certificate devices will trust. `mkcert` makes a local CA plus a cert for `node-0.local` / the LAN IP. `tailscale cert` gives a real cert for a tailnet name. Let's Encrypt suits a public name. The existing SSH-tunnel route stays documented.

## Why not generate a self-signed certificate
- The standard library cannot create certificates. Generating one means shelling out to `openssl`, which isn't on Windows by default, or depending on `cryptography`. Both break the stdlib-only rule.
- A self-signed certificate is untrusted by every browser. It trades "plain HTTP" for a full-page warning that people learn to click through, which is its own security problem. iOS needs a profile install before it accepts one at all.
- A trusted cert from mkcert or Tailscale takes one command and gives a clean padlock. Pointing to those beats shipping a worse version.

## Open
- Whether `serve --tls-cert/--tls-key` flags are worth adding alongside the settings.
- Whether to warn when bound to all interfaces without TLS (a line from `skald open`, a `doctor` WARN).

## [claude] 2026-10-08 05:12 UTC · handoff
Done, as the proposal says, with flags on serve and on server start and restart, and the plain-HTTP warning on stderr.
- `server.py`:
  - `tls_context()` takes TLS 1.2 or later; half a configuration is a SkaldError.
  - `SkaldServer(tls=)` wraps each socket in `get_request` and handshakes in `Handler.setup`.
  - `handle_error` drops SSL and connection errors.
  - The cookie gets `Secure` over TLS.
  - `health(scheme=)` skips verification on loopback.
  - server.json records scheme and cert paths, so restart keeps them.
  - `warn_if_insecure()` runs for open, serve, start and restart.
- Settings `tls_cert` and `tls_key`. doctor has a `tls` check (load, key 0600, plain HTTP on the network).
- Docs updated: board.md#https (mkcert, tailscale cert), troubleshooting, SPEC, multi-project settings. D81, CHANGELOG, contract baseline (new flags).

Verified with 9 new tests (they skip without openssl), the full suite (235), ruff and docs --check. I also ran a real server over HTTPS on 0.0.0.0. It returned 401 without the key, the cookie carried Secure, plain HTTP to the port was dropped while the server carried on, and restart kept HTTPS.
