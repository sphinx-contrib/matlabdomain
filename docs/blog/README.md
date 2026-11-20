# Blog

The blog is part of the project documentation (built from `docs/`).
Posts are Markdown pages using MyST.

Run from `docs/`:

| Task | Command |
|---|---|
| Build (strict) | `uv run --group docs sphinx-build -E -n -W --keep-going -b html . _build/html` |
| Live preview | `uv run --group docs sphinx-autobuild . _build/html` |
| Run a post's demo | `uv run --group docs python blog/<yyyy>/<mm>/<dd-slug>/demo/run.py` |

## Writing a post

- File: `blog/<yyyy>/<mm>/<dd>-<title-slug>.md`. URL becomes
  `blog/<yyyy>/<mm>/<dd>-<title-slug>.html`.
- Runnable examples go in a folder matching the post's filename:
  `blog/<yyyy>/<mm>/<dd>-<title-slug>/demo/`. The `demo/` folders are
  excluded from the build; include files from them with `literalinclude`.
- Add each new post to `blog/index.md`: a dated entry in the
  definition list (newest first) and a matching entry in the hidden
  toctree.
- Each post states the versions it was checked with, and its demo's
  output is pasted from a real run.
