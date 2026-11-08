# Building the documentation

<!-- Written by scmd quickstart (sphinxcontrib-matlabdomain); edit
freely. -->

The documentation is built with [Sphinx](https://www.sphinx-doc.org/) and
[sphinxcontrib-matlabdomain](https://github.com/sphinx-contrib/matlabdomain), which reads the
MATLAB code directly. MATLAB is not needed to build it.

## Set up

Install the documentation dependencies into a Python environment (3.11 or
newer) and activate it before running `make`:

```console
pip install "sphinx>=8.0" "sphinxcontrib-matlabdomain>=1.0" furo sphinx-autobuild
```

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

- **New, moved, renamed or deleted files:** nothing to do; `make` writes
  the API pages in `docs/API` before each build (they are not
  committed).
- **Help text:** write it in Google style (`Args:`, `Returns:`,
  `Examples:`). Put a blank line before a list, and indent a code example
  under a line ending in `::`.
- **Copyright block:** keep it after a blank line, so it is not part of the
  help.
- **Base classes from other projects** are shown as text, not links, once
  they are in `matlab_external_names` in `docs/conf.py`.

## Layout

```text
docs/
├── conf.py            Sphinx configuration
├── index.rst          Home page
├── BUILDING_DOCS.md   This page
├── API/               Generated API pages (not committed)
├── _static/           Static files (CSS, images)
├── _build/            Build output (not committed)
├── Makefile           Build commands for Linux and macOS
└── make.bat           Build commands for Windows
```

## More

- [Sphinx documentation](https://www.sphinx-doc.org/)
- [sphinxcontrib-matlabdomain](https://github.com/sphinx-contrib/matlabdomain)
- [Napoleon (Google style)](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
