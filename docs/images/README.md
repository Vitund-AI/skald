# Screenshots

- Board and story: a demo project on the lifecycle columns, built by
  `make-demo.sh` (an epic with children, a claimed story with a checklist
  and a handoff, questions waiting on a human, a blocked story, two done),
  served by `skald serve` and captured by `capture.py` in headless Chromium
  at a device pixel ratio of 2: the board at 1640×560, light and dark by the
  OS colour scheme the page follows, and the story dialog at 1640×1080.
  The README picks `board-dark.png` through `<picture>` when the reader's
  GitHub theme is dark.
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
