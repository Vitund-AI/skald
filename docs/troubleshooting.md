# Troubleshooting

The messages you are most likely to see, what they mean, and what to do.
`skald check` is the first thing to run whenever the backlog looks wrong: it
validates every file and names the line at fault.

## Finding the project

**`no .skald directory found here or in any parent; run skald init or pass --project NAME`**
You are outside a repository that uses Skald. Change into one, run
`skald init` to start one, or use `-p NAME` for a registered project.

**`project 'x' is not registered on this machine (see skald projects)`**
The index does not know that project yet. Run any `skald` command inside
its repository once; that registers it. `skald projects` lists what is
known.

**A dependency warns `unavailable`**
A `project:id` reference points at a project that is not registered here.
Clone and register it, or accept the warning: it counts as unmet and blocks
nothing.

## Story files

**`skald check` exits 2 with a problem naming a line**
A frontmatter line is not a JSON literal, a required field is missing, or a
value has the wrong type. The message names the file and line. Fix it in an
editor; the rest of the backlog keeps working meanwhile because corrupt
files are skipped, not fatal.

**`invalid status 'x' (columns: ...)`**
`move` or `new` was given a status that is not a column key. `skald columns`
lists them. A story that already carries an unknown status still lists and
appears in an "Unknown status" column until you move it.

**`'a3' is ambiguous: ...`**
Two ids share that prefix. Use more characters.

**`... is archived; unarchive it first`**
Archived stories are read-only. `skald unarchive <id>` brings one back.

**`not in a done or closed column`**
`archive <id>` and the board's Archive action only accept stories in a
terminal column.

**Conflict markers after a merge**
`skald check` reports them. Resolve the file like any other Markdown
conflict; the frontmatter must end up with one value per line.

**A note with an odd heading**
Notes are only recognised as `## [author] YYYY-MM-DD HH:MM UTC` with an
optional `· kind`. Anything else is body text, which is harmless but will
not show in `resume`.

## The board

**The page is unstyled or the preview does not render**
Tailwind and marked load from CDNs. Without internet access the board works
but looks plain. Nothing else depends on the network.

**`server did not come up within 20s`** or **`server exited immediately`**
The message ends with the tail of the server log, which lives in the
machine-local directory as `server.log`. The usual cause is another program
on the port: `skald config port 9000`, or `skald serve --port 9000` for a
foreground run.

**"The body changed on disk while you were editing"**
Someone or something wrote the story file while the dialog was open. Copy
your text, press Reload, and paste it back. Nothing was overwritten.

**A card says "also name@branch"**
Another agent claimed the story on another local branch. `skald next` skips
it; `skald claim` warns before taking it over.

**The board did not update**
It listens for changes and falls back to polling. If it shows
"disconnected" in the header, the server stopped: `skald server status`,
then `skald server start`.

## Rendering and hooks

**`skald check` warns that the snapshot is out of date**
Run `skald render`. To stop remembering, `skald render --enable` makes
`commit`, the board's commit button, and the hooks re-render automatically.

**`skald hooks git --install` refuses**
There is already a pre-commit hook it did not write. Merge the two by hand;
the hook body is one line each for `skald check` and `skald render
--stage`.

**The GitHub workflow's diff job cannot check out the repository**
The job needs `contents: read` alongside `pull-requests: write`. Regenerate
the workflow with `skald hooks github --install` if you edited it.

## Shell completion

**Nothing completes**
The rc line must be `eval "$(skald completion zsh)"` (or `bash`), and
`skald` must be on `PATH` in that shell. Fish reads the file from its
completions directory on the next shell start.

**`project:id` completes strangely in bash**
Bash splits words on colons. zsh and fish handle them; in bash, type the id
after the colon yourself.

## Upgrading

**A leftover `.skald/skald.py` or `git skald` alias from 0.1**
Run `skald init` in the repository. It removes both, writes `config.json`,
and registers the project; stories are untouched.

## Still stuck

`skald --version` and `skald check` output, plus the story file in
question, are what a bug report needs. Issues live at
<https://github.com/Vitund-AI/skald/issues>.
