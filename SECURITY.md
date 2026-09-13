# Security policy

Skald is a command-line tool and a local web board that run on your machine
with your own privileges, reading and writing Markdown files in a repository
you already control. That shapes what a vulnerability in Skald looks like.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's
private vulnerability reporting for this repository:

https://github.com/Vitund-AI/skald/security/advisories/new

The report reaches the maintainers only. If that page is unavailable to
you, open a public issue that says only that you have a security report and
would like a private channel; do not put the details in it.

Include what you can: the version (`skald --version`), the command or
request that triggers the problem, what happens, and what you expected.

## What to expect

- Acknowledgement within three working days.
- An assessment within seven: whether it is a vulnerability, its severity,
  and a plan. Reports that turn out to be out of scope get an explanation,
  not silence.
- A fix as soon as the severity warrants, released as a new version. We aim
  for fourteen days for anything that lets one party act as another or
  read outside the repository, and we will say if it takes longer.
- Credit in the advisory, if you want it.

We ask that you give us that time before disclosing publicly, and we will
keep you informed as we go.

## Supported versions

| Version | Receives security fixes |
| --- | --- |
| The latest release on PyPI | Yes |
| Earlier releases | No, unless a maintainer decides to patch a line; see below |

Skald is pre-1.0 and every fix ships as a new release; upgrading is
`pip install --upgrade skald-kanban`. A critical issue in an earlier line
may get a patch release cut from that line's tag, at the maintainers'
discretion; the flow is in
[docs/git-and-ci.md](docs/git-and-ci.md#patching-an-earlier-release).

## Scope

In scope, because Skald is responsible for it:

- The board server: the token that gates it, the request handling behind
  it, and anything reachable from a browser on the same machine or, with
  `--host 0.0.0.0`, the same network.
- Path handling: story files, templates, imports, and link rewriting must
  never read or write outside the repository they are given.
- The MCP server and the `skald` CLI acting on input from story files,
  which other agents and other people write.
- The published package: what `pip install skald-kanban` delivers.

Out of scope, because it is the user's own machine and privileges:

- An agent or person with write access to the repository editing story
  files, the configuration, or the contract. That is what the tool is for.
- A board opened to the network with `--host 0.0.0.0` and the token shared
  or guessed. The token is the control there; the option is documented.
- Anything that requires already running code on the user's machine.

If you are unsure, report it; the assessment step exists to sort it out.

## After a fix

- A GitHub security advisory for this repository, with a CVE where the
  severity warrants one, naming the affected and fixed versions.
- A changelog entry that says what was fixed.
- The vulnerable release is yanked on PyPI when the issue is serious: it
  stays installable only for someone who pins that exact version, and
  everyone else's resolver skips it. Releases are not deleted, and git tags
  are never removed or moved once a release has been published from them;
  a vulnerable version is superseded, never erased.
