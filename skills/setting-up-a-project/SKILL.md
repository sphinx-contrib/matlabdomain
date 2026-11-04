---
name: setting-up-a-project
description: Set up Sphinx documentation for a MATLAB project with sphinxcontrib-matlabdomain 1.0 from scratch - environment, docs folder, conf.py, project root and exclusions, API pages with sphinx-matlab-apidoc, help-text fixes, warnings, the matlab-api-check audit and make targets. Use when a MATLAB repository has no Sphinx docs yet, or when old docs are to be replaced rather than migrated (for a 0.x setup to keep, use migrating-from-0x).
---

# Setting up documentation for a MATLAB project

Work one step at a time, and write down the input you used, the decision,
and who made it. Many steps need a decision from the project's maintainer:
ask, and do not guess. Nothing is built before step 8: until then, check
with the inventory (step 2) and the generator's dry run (step 4). The
configuration values are described in "Configuration" of the
sphinxcontrib-matlabdomain docs (`docs/reference/configuration.rst` in its
repository).

`<src>` below is the Sphinx source folder: `docs/` at the repository root
unless step 0 says otherwise. The scripts are in `scripts/` and the
templates in `templates/` next to this file (paths below are relative to
this skill's folder). Run the scripts and commands with the project's
environment (step 1): prefix them with `uv run --frozen` from the
repository, or use the make targets (step 3). Commands are POSIX; on
Windows PowerShell use `Select-String` for `grep`.

## 0. Decisions to ask for first

- Where the Sphinx source goes (`<src>`, usually `docs/`), and what
  happens to existing docs and docs sites (delete, keep, migrate, link).
- Whether the generated API pages are committed (then CI runs
  `sphinx-matlab-apidoc --check`) or generated before each build.
- Pages per namespace (`matlab_apidoc_group = "namespace"`, the default)
  or per folder (`"folder"`).
- Which folders are not documented: tests, data, scripts, vendored code,
  legacy copies of code, git submodules (separate projects).
- Duplicate MATLAB names (two files, same name): exclude a copy, or keep
  both, listed by path.
- Whether the help comments in the code may be edited (comment-only
  changes, step 5), and by whom.
- Base classes from other projects or toolboxes: plain text
  (`matlab_external_names`) or links to their docs (intersphinx).
- The MATLAB release the code targets, and where it is written down.
- Markdown notes next to the code as pages (sidecar docs), the HTML theme,
  and the api-check severities (all `"warning"` at first is safe).
- The Python environment tool (uv recommended), how matlabdomain is
  pinned, whether a build guide for contributors is wanted, and what CI
  runs.

## 1. Environment

With uv, the docs dependencies go into the repository's `pyproject.toml`.
uv needs `name` and `version` even when the repository is not a Python
package (`[tool.uv] package = false`). If a `pyproject.toml` exists, add
to it and keep its name and version; uv rejects `[project]` keys that are
not PEP 621.

```toml
[project]
name = "<project>-docs"
version = "0.0.0"
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

- Pin the Python version: `uv python pin 3.12` writes `.python-version`;
  commit it. Without it, machines with different Pythons fork the lock.
- `uv lock` and `uv add` keep the versions an existing `uv.lock` already
  pins: run `uv lock --upgrade` (or `--upgrade-package sphinx`) when the
  lock holds an old Sphinx.
- While changing matlabdomain at the same time, use an editable checkout
  (`uv add --editable <checkout>`) and pin the SHA at the end.
- A git install reports a version like `0.1.devN`; that is 1.0 code. Check
  the installed copy from outside any matlabdomain checkout:
  `uv run python -c "import sphinxcontrib.matlab as m; print(m.__file__)"`.
- `.gitignore`: `<src>/_build/`.

## 2. Inventory

Read before writing anything:

```console
python scripts/inventory.py <repo> --version <R20xxx> --docs <repo>/<src>
python scripts/help_headings.py <repo> --exclude <patterns>
```

`inventory.py` uses the extension's own index: files by top folder and
kind, namespaces and class folders, duplicate MATLAB names, plain folders
with code inside namespaces, `private/` files, files that are not callable,
`.md` and `.rst` files that would be sidecar docs, and encoding warnings.
It prints the Sphinx source folder it assumed (`--docs`, default
`<repo>/docs`); files there are never sidecar docs. `help_headings.py` is
step 4's input. Both take `--exclude` with the patterns of step 4 (they
replace the defaults, as the configuration value does).

Also find:

- the MATLAB path. A MATLAB project (`*.prj`) lists its path folders in
  `resources/project/**/*.xml` as `<Info Ref="<folder>" Type="Relative"/>`,
  and its start-up and shut-down scripts as `Type="StartUp"` or
  `Type="Shutdown"` entries with a `File=` attribute:

  ```console
  grep -rhoE 'Ref="[^"]*" Type="Relative"' resources/project | sort
  grep -rhE 'Type="(StartUp|Shutdown)"' resources/project
  ```

  Otherwise a `startup.m` (`addpath`, `genpath`) or `matlab.toml`.
  `genpath` skips `+`, `@` and `private` folders and everything below
  them: plain folders inside namespaces are on the path only if added by
  name. Folders not on the path are usually not documented; plain folders
  inside namespaces that are on the path hold global names.
- git submodules (`.gitmodules`), checked out or not, and referenced
  MATLAB projects.
- the MATLAB release the code targets (CI files, README, project file).
- the help style: comment block before or after the declaration, the
  headings, and licence or copyright blocks that run into the help without
  a blank line:

  ```console
  python - <<'EOF'
  import pathlib, re
  for p in pathlib.Path(".").rglob("*.m"):
      lines = p.read_text(errors="replace").splitlines()
      for i in range(1, len(lines)):
          if re.match(r"\s*%.*(copyright|licen[cs]e|restrictions)", lines[i], re.I) \
                  and lines[i - 1].lstrip().startswith("%"):
              print(f"{p}:{i + 1}: {lines[i].strip()}")
              break
  EOF
  ```

  A hit is a block that runs into the comment above it; check that this
  comment is help.
- the existing docs, build scripts and CI steps.

## 3. Layout

```text
<repo>/
    .python-version
    pyproject.toml, uv.lock
    <src>/
        conf.py           templates/conf.py
        index.rst         placeholder until step 6
        BUILDING_DOCS.md  templates/BUILDING_DOCS.md (step 10)
        _static/.gitkeep  git keeps no empty folders; Sphinx warns without it
        Makefile          templates/Makefile
        make.bat          templates/make.bat
        API/              written by sphinx-matlab-apidoc (step 7)
```

A placeholder `index.rst` (a title and an empty toctree) lets every later
check run. The make files run everything with `uv run --frozen` (the
locked environment, no activation, `uv.lock` never rewritten) and add the
targets `apidoc`, `apidoc-check` and `livehtml` (`sphinx-autobuild`
watching the repository, with the generator as its pre-build step). Every
other target goes to Sphinx's make mode (`html`, `clean`,
`matlab-api-check`). `make.bat` returns the command's exit code.

`make.bat` needs CRLF line endings (cmd.exe misreads labels in LF-only
files). Add to `.gitattributes`:

```text
*.bat text eol=crlf
```

## 4. `conf.py`

Start from `templates/conf.py` and fill in:

- `matlab_src_code_project_root = ".."`: the repository root, relative to
  `<src>`. Code outside a namespace is then named by its file name.
- `matlab_src_exclusion_patterns` replaces the defaults: keep them, add
  the folders from step 0, and read the submodule paths from `.gitmodules`
  (the template's `_submodule_paths`). Patterns are relative to the root,
  with `/`. A helper's name must not start with `matlab_`.
- `matlab_version`: the release from step 2.
- `napoleon_custom_sections`: the project's headings from
  `help_headings.py`. Parameter-like headings (`Inputs`, `Outputs`,
  `Name Value Pairs`) as `("Inputs", "params_style")`: their
  `name - text` and `name: text` items become parameters. Spelling
  variants as aliases (`("Input", "Inputs")`); other headings as plain
  names. Napoleon matches headings ignoring case (one entry covers
  `INPUTS:` and `Inputs:`), and only headings made of letters, digits,
  `_` and spaces: `Name-Value Pairs:` or `Input/Output:` never match, so
  an entry for them does nothing; rename them in the code. Its built-in
  sections (`Args`, `Returns`, `Example`, `Note`, `See Also`, ...) need no
  entry. A long or messy list is a sign to rename the headings in the
  code instead.
- `matlab_src_sidecar_suffixes = [".md"]` if Markdown notes next to the
  code should be pages (needs `myst_parser`).
- `smartquotes = False` if the help quotes code (`'name'`) in prose and
  the straight quotes should stay.

Check the selection, without writing:

```console
sphinx-matlab-apidoc -c <src> -n
```

It lists the pages it would write and the index warnings (encoding,
duplicate names, files that are not callable and why).

## 5. Help text

Help text is reStructuredText after napoleon's rewrite. Fix the code's
comments if step 0 allows it (comment-only changes):

| Problem | Fix |
|---|---|
| A licence or copyright block runs into the help (step 2 recipe) | a blank line (not `%`) before it ends the help there |
| "Unexpected indentation" after `Label:` and an indented table | `Label::` and a blank comment line: a literal block |
| "Block quote ends without a blank line" or "Definition list ends without a blank line" | a blank comment line after the indented lines, or indent the following lines alike |
| A list right after a paragraph | a blank comment line before the list; continuation lines under the item's text |
| "Literal block expected; none found" | a `::` line with nothing indented after it: add the syntax line, or remove `::` |
| "Undefined substitution referenced" (`\|name\|`, an absolute value or norm) | double backquotes around the expression |
| "Unknown target name" (`word_`, a name ending in `_`) | double backquotes, or `\_` |
| "Unexpected section title" or "Title underline too short" (`----` lines) | a blank comment line around the rule, or remove it |
| "Inline emphasis start-string without end-string" (a lone `*`) | double backquotes around the expression, or `\*` |
| "Anonymous hyperlink mismatch" (`text__`) | double backquotes |
| A property gets commented-out code as its help | a blank line between that comment and the property |
| An unedited template help (wrong name, `TBD`) | rewrite it in the project's style |

Line numbers in docutils warnings count lines of the rewritten docstring,
not of the file: search for the text.

Code the project may not edit (third-party, vendored): exclude it, list
its warnings for its owners only, or turn off all docutils warnings with
`suppress_warnings = ["docutils"]` (Sphinx 7.4 or later; this covers the
project's own pages too).

## 6. Home page

`<src>/index.rst`: the project title, a short introduction, and a toctree
with `API/index` (step 7). Keep text from old docs that still holds.

## 7. API pages

```console
sphinx-matlab-apidoc -c <src>
```

- A duplicate MATLAB name (two files, same name) is reported only by the
  generator (`mat.apidoc`), not by the build, and `--check` passes with
  it. Both files are listed by path on their page. If MATLAB runs only one
  of them, exclude the other with a comment in `conf.py` saying why; ask
  which one.
- Commit `<src>/API` if decided in step 0. `make apidoc-check` (or
  `sphinx-matlab-apidoc -c <src> --check`) then exits 1 when a page is out
  of date: after files are added, moved, renamed or deleted.

## 8. Build and warnings

Count warnings on a clean build: an incremental build reports only the
pages it rebuilds. From `<src>`:

```console
make clean html SPHINXOPTS="-n -w _build/warnings.txt"
python <skills>/migrating-from-0x/scripts/group_warnings.py _build/warnings.txt --show 10
```

On Windows: `set SPHINXOPTS=-n -w _build/warnings.txt`, then `make clean`
and `make html`. `group_warnings.py` comes from the migrating-from-0x
skill; it groups by type and subtype, so all docutils warnings are one
group: read them in the file.

| Warning | Usual fix |
|---|---|
| "reference target not found" for base classes of other projects (submodules, referenced projects, toolboxes) | find the project with the namespace folder (`+name`), then its namespaces in `matlab_external_names`; later `sphinx.ext.intersphinx` to their published docs |
| "reference target not found" for a project class | its file is excluded, or the name is wrong in the help |
| docutils errors in help | step 5 |
| `mat.encoding` | save the file as UTF-8, or leave it (it decodes) |
| `mat.invalid_matlab` | a syntax error or an unfinished file: fix it, or exclude it if it is not code |
| `mat.not_callable` | the message says why; rename or move the file, or suppress it if intended |
| `mat.apidoc` duplicate name | step 7 |
| `toc.not_included` | add the page to a toctree |

The goal: `-n -W` with no warnings, or every remaining warning type
explained. Then `make clean html SPHINXOPTS="-n -W"` is the CI build.

## 9. Help-text audit

The template sets every `matlab_api_check_rules` entry to `"warning"`.

```console
make matlab-api-check
```

The report is `<src>/_build/matlab-api-check/api-check.txt` (and `.json`).
Record the counts by rule; which findings to fix first is the project's
choice. Raise rules to `"error"` as the help improves.

## 10. Preview, guide and CI

- `make livehtml` serves the site on http://127.0.0.1:8000 and rebuilds
  when a page or a MATLAB file changes.
- A short build guide for the project's contributors in `<src>`, in a
  toctree: start from `templates/BUILDING_DOCS.md`.
- CI, no MATLAB needed: `uv sync --locked`; `sphinx-matlab-apidoc -c <src>
  --check`; `sphinx-build -n -W -b html <src> <out>`; optionally the
  api-check build with its report kept; publishing from the default branch.
- On Windows, git's `core.autocrlf` checks the pages out with CRLF; the
  generator ignores line endings, so `--check` still passes.

## Checklist

- [ ] decisions of step 0 recorded
- [ ] inventory read: namespaces, duplicates, MATLAB path, submodules, help style
- [ ] `.python-version` committed; `uv sync --locked` works in a fresh clone; matlabdomain pinned to a SHA or release
- [ ] `<src>/` with `conf.py`, `index.rst`, `_static/.gitkeep`, make files (`make.bat` CRLF); `<src>/_build/` ignored
- [ ] `sphinx-matlab-apidoc -c <src> --check` exits 0
- [ ] clean `-n -W` build passes, or each remaining warning type explained
- [ ] `matlab-api-check` runs; findings recorded
- [ ] build guide and CI notes written
