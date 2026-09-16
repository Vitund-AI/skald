# Screenshots

- Board, story, and swimlanes: a demo project on the lifecycle columns, built
  by `make-demo.sh` (an epic with children, a claimed story with a checklist
  and a handoff, questions waiting on a human, a blocked story, two done, and
  `epic:` / `area:` facets), served by `skald serve` and captured by
  `capture.py` in headless Chromium at a device pixel ratio of 2. The shots
  are declared in the `SHOTS` list in `capture.py`: the board at 1640×560 in
  the dark and light themes, the story dialog at 1640×1080 dark in view mode,
  and the swimlanes view (grouped by the `area` facet) captured full-height.
  To showcase a new feature, add it to `make-demo.sh` and add a shot with a
  `setup(page)` that drives the board to the view.
  The README shows `board-dark.png` and picks `board-light.png` through
  `<picture>` when the reader's GitHub theme is light.
- Graph and multi-select: this repository's own backlog, 1440×860.
- Terminal images: real command output wrapped in a small HTML terminal
  frame and rendered the same way. The completion image shows
  `skald _complete` output laid out the way zsh's `_describe` prints it.

Retake them after a visible change to the board or to command output:

```sh
docs/images/make-demo.sh /tmp/wireguard-overlay
(cd /tmp/wireguard-overlay && skald server start)
python3 docs/images/capture.py wireguard-overlay docs/images
```

Where the browser cannot reach the CDNs (a sandbox behind a proxy), put
copies of the Tailwind and marked scripts at `docs/images/tailwind.js`
and `docs/images/marked.js`, and the Google Fonts stylesheet with its
`.woff2` files in `docs/images/fonts/` (the stylesheet as `fonts.css`,
each font URL rewritten to `http://127.0.0.1:1/NAME.woff2`); `capture.py`
serves them from disk. Those copies are ignored by git.
