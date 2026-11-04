---
name: setting-up-a-project
description: Set up Sphinx documentation for a MATLAB project with sphinxcontrib-matlabdomain 1.0 from scratch - environment, docs folder, conf.py, project root and exclusions, API pages with sphinx-matlab-apidoc, help-text fixes, warnings, the matlab-api-check audit and make targets. Use when a MATLAB repository has no Sphinx docs yet, or when old docs are to be replaced rather than migrated (for a 0.x setup to keep, use migrating-from-0x).
---

# Setting up documentation for a MATLAB project

Work one step at a time. After each step, build, and write down the input
you used, the decision, and who made it. Many steps need a decision from
the project's maintainer: ask, and do not guess. The configuration values
are described in "Configuration" of the sphinxcontrib-matlabdomain docs
(`docs/reference/configuration.rst` in its repository).

The scripts are in `scripts/` and the templates in `templates/` next to
this file (paths below are relative to this skill's folder). Run the
scripts and commands with the project's environment (step 1): prefix them
with `uv run --frozen` from the repository, or use the make targets
(step 3). Commands are POSIX; on Windows PowerShell use `Select-String`
for `grep`.

## 0. Decisions to ask for first

- Where the Sphinx source goes (`docs/` at the root is usual), and what
  happens to existing docs (delete, keep, migrate).
- Whether the generated API pages are committed (then CI runs
  `sphinx-matlab-apidoc --check`) or generated before each build.
- Pages per namespace (`matlab_apidoc_group = "namespace"`, the default)
  or per folder (`"folder"`).
- Which folders are not documented: tests, data, scripts, vendored code,
  git submodules (separate projects).
- Markdown notes next to the code as pages (sidecar docs), the HTML theme,
  and the api-check severities (all `"warning"` at first is safe).
- The Python environment tool (uv recommended) and how matlabdomain is
  pinned.

## 1. Environment

With uv, the docs dependencies go into the repository's `pyproject.toml`
(`[tool.uv] package = false` when it is not a Python package):

```toml
[project]
requires-python = ">=3.12"
dependencies = [
    "sphinx>=8.2,<10",
    "sphinxcontrib-matlabdomain",
    "myst-parser>=4,<6",        # Markdown pages and sidecar docs
    "linkify-it-py>=2",         # MyST linkify
    "sphinx-autobuild>=2025.8", # make livehtml
    "furo>=2024.8",             # or another theme
]

[tool.uv]
package = false

[tool.uv.sources]
# Unreleased 1.0.0; replace with a version pin after the release.
sphinxcontrib-matlabdomain = { git = "https://github.com/<owner>/<repo>", rev = "<full sha>" }
```

- While changing matlabdomain at the same time, use an editable checkout
  (`uv add --editable <checkout>`) and pin the SHA at the end.
- `uv add` keeps the versions an existing `uv.lock` already pins: run
  `uv lock --upgrade` (or `--upgrade-package sphinx`) when the lock holds
  an old Sphinx.
- A git install reports a version like `0.1.devN`; that is 1.0 code. Check
  the installed copy from outside any matlabdomain checkout:
  `uv run python -c "import sphinxcontrib.matlab as m; print(m.__file__)"`.
- `.gitignore`: `docs/_build/`.

## 2. Inventory

Read before writing anything:

```console
python scripts/inventory.py <repo> --version <R20xxx>
python scripts/help_headings.py <repo>
```

`inventory.py` uses the extension's own index: files by top folder and
kind, namespaces, duplicate MATLAB names, plain folders with code inside
namespaces, `private/` files, files that are not callable, `.md` and `.rst`
files that would be sidecar docs, and encoding warnings. Also find:

- the MATLAB path: a MATLAB project (`*.prj`, `resources/project/**`), a
  `startup.m`, or `matlab.toml`. Folders not on the path are usually not
  documented; plain folders inside namespaces that are on the path hold
  global names.
- git submodules (`.gitmodules`), checked out or not.
- the MATLAB release the code targets (CI files, README, project file).
- the help style: comment block before or after the declaration, the
  headings (`Inputs:`, `Outputs:`, `Class Description:`), and licence or
  copyright blocks that run into the help without a blank line.
- the existing docs, build scripts and CI steps.

## 3. Layout

```text
<repo>/
    docs/
        conf.py      templates/conf.py
        index.rst
        _static/
        Makefile     templates/Makefile
        make.bat     templates/make.bat
        API/         written by sphinx-matlab-apidoc (step 7)
```

The make files run everything with `uv run --frozen` (the locked
environment, no activation, `uv.lock` never rewritten) and add the targets
`apidoc`, `apidoc-check` and `livehtml` (`sphinx-autobuild` watching the
repository, with the generator as its pre-build step). Every other target
goes to Sphinx's make mode (`html`, `clean`, `matlab-api-check`).
`make.bat` returns the command's exit code.

## 4. `conf.py`

Start from `templates/conf.py` and fill in:

- `matlab_src_code_project_root = ".."`: the repository root, relative to
  `docs/`. Code outside a namespace is then named by its file name.
- `matlab_src_exclusion_patterns` replaces the defaults: keep them, add
  the folders from step 0, and read the submodule paths from `.gitmodules`
  (the template's `_submodule_paths`). Patterns are relative to the root,
  with `/`. A helper's name must not start with `matlab_`.
- `matlab_version`: the release from step 2.
- `napoleon_custom_sections`: the project's headings from
  `help_headings.py`. Parameter-like headings (`Inputs`, `Outputs`,
  `Name Value Pairs`) as `("Inputs", "params_style")`; spelling variants
  as aliases (`("Input", "Inputs")`); other headings as plain names. A
  long or messy list is a sign to rename the headings in the code instead.
- `matlab_src_sidecar_suffixes = [".md"]` if Markdown notes next to the
  code should be pages (needs `myst_parser`).

Check the selection before the first build:

```console
sphinx-matlab-apidoc -c docs -n
```

It lists the pages it would write and the index warnings (encoding,
duplicate names), without writing.

## 5. Help text

Help text is reStructuredText after napoleon's rewrite. Fix the code's
comments (ask the code owner; comment-only changes):

| Problem | Fix |
|---|---|
| A licence or copyright block runs into the help | a blank line (not `%`) before it ends the help there |
| "Unexpected indentation" after `Label:` and an indented table | `Label::` and a blank comment line: a literal block |
| A list right after a paragraph | a blank comment line before the list; continuation lines under the item's text |
| "Literal block expected; none found" | a `::` line with nothing indented after it: add the syntax line, or remove `::` |
| A property gets commented-out code as its help | a blank line between that comment and the property |
| An unedited template help (wrong name, `TBD`) | rewrite it in the project's style |

Line numbers in docutils warnings count lines of the rewritten docstring,
not of the file: search for the text.

## 6. Home page

`docs/index.rst`: the project title, a short introduction, and a toctree
with `API/index` (step 7). Keep text from old docs that still holds.

## 7. API pages

```console
sphinx-matlab-apidoc -c docs -n    # dry run: pages and warnings
sphinx-matlab-apidoc -c docs       # write
```

- A duplicate MATLAB name (two files, same name) is listed by path on its
  page. If MATLAB runs only one of them, exclude the other with a comment
  in `conf.py` saying why; ask which one.
- Commit `docs/API` if decided in step 0. `make apidoc-check` (or
  `sphinx-matlab-apidoc -c docs --check`) then exits 1 when a page is out
  of date: after files are added, moved, renamed or deleted.

## 8. Build and warnings

```console
sphinx-build -b html -n -w warnings.txt docs docs/_build/html
python ../migrating-from-0x/scripts/group_warnings.py warnings.txt
```

| Warning | Usual fix |
|---|---|
| "reference target not found" for base classes of other projects (submodules, toolboxes) | their namespaces in `matlab_external_names`; later `sphinx.ext.intersphinx` to their published docs |
| "reference target not found" for a project class | its file is excluded, or the name is wrong in the help |
| docutils errors in help | step 5 |
| `mat.encoding` | save the file as UTF-8, or leave it (it decodes) |
| `mat.apidoc` duplicate name | step 7 |
| `toc.not_included` | add the page to a toctree |

The goal: `-n -W` with no warnings, or every remaining warning type
explained. Then `make html SPHINXOPTS="-n -W"` (Windows: set `SPHINXOPTS`
first) is the CI build.

## 9. Help-text audit

The template sets every `matlab_api_check_rules` entry to `"warning"`.

```console
make matlab-api-check
```

The report is `docs/_build/matlab-api-check/api-check.txt` (and `.json`).
Record the counts by rule; which findings to fix first is the project's
choice. Raise rules to `"error"` as the help improves.

## 10. Preview, guide and CI

- `make livehtml` serves the site on http://127.0.0.1:8000 and rebuilds
  when a page or a MATLAB file changes.
- A short build guide for the project's contributors (setup with uv, the
  make targets, when to run `make apidoc`) in `docs/`, in a toctree.
- CI, no MATLAB needed: `uv sync --locked`; `sphinx-matlab-apidoc -c docs
  --check`; `sphinx-build -n -W -b html docs <out>`; optionally the
  api-check build with its report kept; publishing from the default branch.
- On Windows, git's `core.autocrlf` checks the pages out with CRLF; the
  generator ignores line endings, so `--check` still passes.

## Checklist

- [ ] decisions of step 0 recorded
- [ ] inventory read: namespaces, duplicates, MATLAB path, submodules, help style
- [ ] `uv sync --locked` in a fresh clone; matlabdomain pinned to a SHA or release
- [ ] `docs/` with `conf.py`, `index.rst`, make files; `docs/_build/` ignored
- [ ] `sphinx-matlab-apidoc -c docs --check` exits 0
- [ ] `-n -W` clean, or each remaining warning type explained
- [ ] `matlab-api-check` runs; findings recorded
- [ ] build guide and CI notes written
