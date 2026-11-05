# Building the documentation

<!-- Written by sphinx-matlab-quickstart (sphinxcontrib-matlabdomain); edit
freely. -->

The documentation is built with [Sphinx](https://www.sphinx-doc.org/) and
[sphinxcontrib-matlabdomain](https://github.com/sphinx-contrib/matlabdomain), which reads the
MATLAB code directly. MATLAB is not needed to build it.

## Set up

You need [uv](https://docs.astral.sh/uv/). The `make` commands below run
everything with `uv run --frozen --group docs`, which creates `.venv` with
the packages locked in `uv.lock` on first use; no activation is needed. To
create it beforehand, run from the repository root:

```console
uv sync --group docs
```

The git submodules do not need to be checked out: the documentation skips
them (`docs/conf.py` reads their paths from `.gitmodules`).

## Commands

Run these from the `docs` folder. On Windows, `make` is `make.bat`.

| Command | What it does |
|---|---|
| `make html` | Builds the site into `docs/_build/html`; open `index.html` there. |
| `make livehtml` | Builds the site, serves it at <http://127.0.0.1:8000> and rebuilds when a MATLAB file or a page changes. Stop it with `Ctrl+C`. |
| `make apidoc` | Writes the API pages in `docs/API` from the MATLAB code. |
| `make apidoc-check` | Fails when the API pages in `docs/API` are out of date. |
| `make matlab-api-check` | Lists gaps in the MATLAB help text in `docs/_build/matlab-api-check/api-check.txt`. |
| `make clean` | Deletes `docs/_build`. |

A strict build from scratch, which treats every warning as an error (on
Windows: `set SPHINXOPTS=-n -W`, then `make clean` and `make html`):

```console
make clean html SPHINXOPTS="-n -W"
```

## When you change the MATLAB code

- **New, moved, renamed or deleted files:** run `make apidoc` and commit the
  changes in `docs/API`. `make apidoc-check` tells you whether this is
  needed. Edits inside an existing file need no new API pages.
- **Help text:** write it in Google style. Besides `Args:` and `Returns:`,
  the project's own headings work: `Description:`, `Outputs:`, `Inputs:`, `Input:`
  (`napoleon_custom_sections` in `docs/conf.py`). Put a blank line
  before a list, and indent a code example under a line ending in `::`.
- **Copyright block:** keep it after a blank line, so it is not part of the
  help.
- **Base classes from other projects** are shown as text, not links, once
  they are in `matlab_external_names` in `docs/conf.py`.
- **Notes in Markdown:** a `.md` file next to the MATLAB code becomes part
  of the API pages after `make apidoc`.

## Layout

```text
docs/
├── conf.py            Sphinx configuration
├── index.rst          Home page
├── BUILDING_DOCS.md   This page
├── API/               Generated API pages (committed)
├── _static/           Static files (CSS, images)
├── _build/            Build output (not committed)
├── Makefile           Build commands for Linux and macOS
└── make.bat           Build commands for Windows
```

## More

- [Sphinx documentation](https://www.sphinx-doc.org/)
- [sphinxcontrib-matlabdomain](https://github.com/sphinx-contrib/matlabdomain)
- [Napoleon (Google style)](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
- [MyST Markdown](https://myst-parser.readthedocs.io/)
- [uv](https://docs.astral.sh/uv/)
