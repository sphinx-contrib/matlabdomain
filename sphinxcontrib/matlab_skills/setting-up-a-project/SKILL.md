---
name: setting-up-a-project
description: Set up Sphinx documentation for a MATLAB project with sphinxcontrib-matlabdomain 1.0 from scratch - decisions, the scmd quickstart command (dry run, report, answers file), exclusions, help-text fixes, warnings, the matlab-api-check audit, preview, guide and CI. Use when a MATLAB repository has no Sphinx docs yet, or when old docs are to be replaced rather than migrated (for a 0.x setup to keep, use migrating-from-0x).
---

# Setting up documentation for a MATLAB project

Work one step at a time, and write down the input you used, the decision,
and who made it. Many steps need a decision from the project's maintainer:
ask, and do not guess. The command `scmd quickstart` does the
mechanical part (steps 2 and 3): it reads the project, writes the Sphinx
source folder and prints a report. Its user guide is "Setting up a
project" in the sphinxcontrib-matlabdomain docs
(`docs/user-guide/setting-up.rst` in its repository); the configuration
values are in "Configuration" (`docs/reference/configuration.rst`).

`<src>` below is the Sphinx source folder: `docs/` at the repository root
unless step 0 says otherwise. Run the commands with the project's
environment: prefix them with `uv run --frozen` from the repository, or use
the make targets the command writes. Commands are POSIX; on Windows
PowerShell use `Select-String` for `grep`.

## 0. Decisions to ask for first

- Where the Sphinx source goes (`<src>`, usually `docs/`), and what
  happens to existing docs and docs sites (delete, keep, migrate, link).
  The command refuses a folder that has files but no `conf.py`.
- Whether the generated API pages are committed (then CI runs
  `make apidoc-check`) or generated before each build (`api_pages`).
- Pages per namespace (the default) or per folder (`group`).
- Which folders are not documented: tests, data, scripts, vendored code,
  legacy copies of code. Git submodules are left out by the command.
- Duplicate MATLAB names (two files, same name): exclude a copy, or keep
  both, listed by path.
- Whether the help comments in the code may be edited (comment-only
  changes, step 4), and by whom.
- Base classes from other projects or toolboxes: plain text
  (`matlab_external_names`) or links to their docs (intersphinx).
- The MATLAB release the code targets, and where it is written down.
- Markdown notes next to the code as pages (sidecar docs), the HTML theme,
  and the api-check severities (the command sets all to `"warning"`).
- The Python environment tool (uv recommended), how matlabdomain is
  pinned, whether a build guide for contributors is wanted, and what CI
  runs.

## 1. Environment

The command copies how matlabdomain itself is installed into the docs
dependencies (a git URL and commit, an editable folder, or a version), so
install the matlabdomain you want the project to use first. In a uv
project it runs `uv add --frozen --group docs`; uv needs no `[project]`
table for a dependency group, but a `[project]` table must have `name` and
`version`.

- Pin the Python version: `uv python pin 3.12` writes `.python-version`;
  commit it. Without it, machines with different Pythons fork the lock.
- `uv lock` keeps the versions an existing `uv.lock` already pins: run
  `uv lock --upgrade` (or `--upgrade-package sphinx`) when the lock holds
  an old Sphinx.
- While changing matlabdomain at the same time, use an editable checkout
  and pin the SHA at the end.
- A git install reports a version like `0.1.devN`; that is 1.0 code. Check
  the installed copy from outside any matlabdomain checkout:
  `uv run python -c "import sphinxcontrib.matlab as m; print(m.__file__)"`.
- Testing a commit from a local matlabdomain checkout: a non-editable
  install of the folder or `uv build --wheel` reuses the checkout's
  git-ignored `build/` folder. Left from an older build, it brings back the
  removed `sphinxcontrib/__init__.py`, and every command then fails with
  `No module named 'pkg_resources'` (raised in `sphinxcontrib/__init__.py`).
  Delete `build/` in the checkout, or build with `uv build` (the source
  archive first, then the wheel from it), or install from the git URL at
  the SHA.

## 2. Dry run and report

```console
scmd quickstart <repo> --output-dir <repo>/<src> --dry-run
```

It writes nothing and prints the files it would write, the lines it would
add outside `<src>`, and the report: the MATLAB releases it found, uv,
submodules, folders not on the MATLAB project path, the inventory
(namespaces, duplicate MATLAB names, files that are not callable, encoding),
the help headings, and the copyright blocks that run into help. At the end
it offers to save the answers to a TOML file; edit that file with the
decisions of step 0 (keys: `project`, `author`, `matlab_version`, `group`,
`theme`, `html_baseurl`, `exclude`, `markdown`, `sidecars`, `make`, `guide`, `api_pages`,
`napoleon_custom_sections`).

Also check what the command cannot know:

- the MATLAB path beyond the project file: a `startup.m` (`addpath`,
  `genpath`) or start-up scripts. `genpath` skips `+`, `@` and `private`
  folders and everything below them: plain folders inside namespaces are on
  the path only if added by name. Folders not on the path are usually not
  documented; plain folders inside namespaces that are on the path hold
  global names. The command writes the folders it found off the path into
  `conf.py` as commented-out patterns.
- referenced MATLAB projects and toolboxes (base classes).
- the help style: comment block before or after the declaration. A
  reported copyright block runs into the comment above it; check that this
  comment is help.
- the existing docs, build scripts and CI steps.

Napoleon notes for `napoleon_custom_sections`: a heading in 10 or more
files becomes an entry (parameter-like headings as `params_style`, their
`name - text` and `name: text` items become parameters), its plural or
singular an alias. Napoleon matches headings ignoring case, and only
headings made of letters, digits, `_` and spaces: `Name-Value Pairs:` never
matches, so rename it in the code. A long or messy list is a sign to rename
the headings in the code instead.

## 3. Write the files

```console
scmd quickstart <repo> --output-dir <repo>/<src> --answers <file>
```

It stops before writing anything if `pyproject.toml`, `.gitignore` or
`.gitattributes` has uncommitted changes, so its edits stay separate. It
writes `<src>/conf.py`, `index.rst`, `_static/.gitkeep`, `Makefile`,
`make.bat` (CRLF), `BUILDING_DOCS.md` and the API pages in `<src>/API`,
adds the docs dependency group (uv), `<src>/_build/` to `.gitignore` and
`*.bat text eol=crlf` to `.gitattributes`. The templates are in the package,
`sphinxcontrib/matlab_quickstart/templates/`. Then:

```console
uv lock
uv sync --group docs
```

Review `conf.py`: uncomment the exclusions that are not the project's API,
add the folders of step 0, and set `smartquotes = False` if the help quotes
code (`'name'`) in prose and the straight quotes should stay. A helper's
name in `conf.py` must not start with `matlab_`. After a change of the
exclusions, `make apidoc` rewrites the API pages.

## 4. Help text

Help text is reStructuredText after napoleon's rewrite. Fix the code's
comments if step 0 allows it (comment-only changes):

| Problem | Fix |
|---|---|
| A licence or copyright block runs into the help (the report lists them) | a blank line (not `%`) before it ends the help there |
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

## 5. Home page and API pages

- `<src>/index.rst`: write a short introduction under the title; keep text
  from old docs that still holds.
- A duplicate MATLAB name (two files, same name) is reported only by the
  generator (`mat.apidoc`), not by the build, and `--check` passes with
  it. Both files are listed by path on their page. If MATLAB runs only one
  of them, exclude the other with a comment in `conf.py` saying why; ask
  which one.
- Commit `<src>/API` if decided in step 0. `make apidoc-check` then exits 1
  when a page is out of date: after files are added, moved, renamed or
  deleted.

## 6. Build and warnings

Count warnings on a clean build: an incremental build reports only the
pages it rebuilds. From `<src>`:

```console
make clean html SPHINXOPTS="-n -w _build/warnings.txt"
python <skills>/setting-up-a-project/scripts/group_warnings.py _build/warnings.txt --show 10
```

On Windows: `set SPHINXOPTS=-n -w _build/warnings.txt`, then `make clean`
and `make html`. `group_warnings.py` groups by type and subtype, so all
docutils warnings are one group: read them in the file.

| Warning | Usual fix |
|---|---|
| "reference target not found" for base classes of other projects (submodules, referenced projects, toolboxes) | find the project with the namespace folder (`+name`), then its namespaces in `matlab_external_names` (commented out in `conf.py`); later `sphinx.ext.intersphinx` to their published docs |
| "reference target not found" for a project class | its file is excluded, or the name is wrong in the help |
| docutils errors in help | step 4 |
| `mat.encoding` | save the file as UTF-8, or leave it (it decodes) |
| `mat.invalid_matlab` | a syntax error or an unfinished file: fix it, or exclude it if it is not code |
| `mat.not_callable` | the message says why; rename or move the file, or suppress it if intended |
| `mat.apidoc` duplicate name | step 5 |
| `toc.not_included` | add the page to a toctree |

The goal: `-n -W` with no warnings, or every remaining warning type
explained. Then `make clean html SPHINXOPTS="-n -W"` is the CI build.

## 7. Help-text audit

`conf.py` sets every `matlab_api_check_rules` entry to `"warning"`.

```console
make matlab-api-check
```

The report is `<src>/_build/matlab-api-check/api-check.txt` (and `.json`).
Record the counts by rule; which findings to fix first is the project's
choice. Raise rules to `"error"` as the help improves.

## 8. Preview, guide and CI

- `make livehtml` serves the site on http://127.0.0.1:8000 and rebuilds
  when a page or a MATLAB file changes.
- `<src>/BUILDING_DOCS.md` is the build guide for contributors: fill in
  the project's specifics (external names, the CI build).
- CI, no MATLAB needed: `uv sync --locked`; `make apidoc-check`; `make
  clean html SPHINXOPTS="-n -W"`; optionally the api-check build with its
  report kept; publishing from the default branch.
- On Windows, git's `core.autocrlf` checks the pages out with CRLF; the
  generator ignores line endings, so `--check` still passes.

## Checklist

- [ ] decisions of step 0 recorded
- [ ] report read: namespaces, duplicates, MATLAB path, submodules, help headings, copyright blocks
- [ ] `.python-version` committed; `uv sync --locked` works in a fresh clone; matlabdomain pinned to a SHA or release
- [ ] `scmd quickstart` run with the answers file; `conf.py` reviewed
- [ ] `scmd apidoc --conf-dir <src> --check` exits 0
- [ ] clean `-n -W` build passes, or each remaining warning type explained
- [ ] `matlab-api-check` runs; findings recorded
- [ ] build guide and CI notes written
