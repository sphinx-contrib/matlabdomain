---
name: migrating-from-0x
description: Migrate a Sphinx project that documents MATLAB code with sphinxcontrib-matlabdomain 0.x (0.22 and earlier) to 1.0. Use when a conf.py sets matlab_src_dir or matlab_keep_package_prefix, pages use dotted MATLAB names or module/automodule directives, a 1.0 build fails with a ConfigError about removed values, or a project wants scmd apidoc pages and the matlab-api-check builder instead of a 0.x page generator or doc-check script.
---

# Migrating a project from matlabdomain 0.x to 1.0

Work in small steps and build after each one. The reference is the
migration guide: "Migrating from 0.22 and earlier" in the
sphinxcontrib-matlabdomain docs (`docs/user-guide/migration.rst` in its
repository). The scripts are in `scripts/` next to this file (paths below
are relative to this skill's folder); they need only Python and Sphinx.
Commands are POSIX; on Windows PowerShell use `Select-String` for `grep`
(`Get-ChildItem -Recurse docs -Include *.rst,*.md | Select-String -Pattern ...`).

## 1. Learn the project first

Find out, and write down:

- where `conf.py` is, what runs the build (a Makefile, a CI step, a wrapper
  script in another language), and the Sphinx and matlabdomain versions;
- where the MATLAB code is (`matlab_src_dir`) and whether the build copies
  or links it into a separate source tree first;
- whether the pages are hand-written or generated (by a script, at build
  time), and whether generated pages are committed;
- the directives and options the pages use (`grep -rn "^\.\. " docs`), and
  anything that reads the build output (XML, doctrees, HTML ids), such as a
  doc-check script;
- the warnings the build has today.

## 2. Baseline with 0.x

Build once with the current setup, unchanged, in a scratch copy if the build
writes into the repository. Use the Sphinx version the project pinned; if it
pinned none, Sphinx 7.x works with 0.22. Build with `-n` as well, so the
warnings compare with step 9. Keep the HTML output's `objects.inv`, the
warnings (`-w warnings.txt`), the page list and the time. If pages are
generated at build time, keep the generated pages too: they let you
separate what the extension changes from what the generator changes
(step 10).

```console
python scripts/compare_inventories.py _build/html/objects.inv
```

## 3. Environment

- Python >= 3.11, Sphinx >= 8.0.
- Replace a `sphinxcontrib-matlabdomain==0.*` pin with `>=1,<2`. Before a
  1.0 release, pin a git URL to a full commit SHA:
  `"sphinxcontrib-matlabdomain @ git+https://github.com/<owner>/<repo>@<sha>"`
  (with uv: `[tool.uv.sources]` `{ git = "...", rev = "<sha>" }`). Such an
  install reports a version like `0.1.devN`; that is still 1.0 code.
- Recreate the environment. A reused virtual environment (CI agents,
  scripts that create it only when missing) keeps 0.x.
- Remove `sys.path` entries in `conf.py` that point at a checkout of the
  extension (common in projects copied from the extension's own test
  docs). An old checkout's `sphinxcontrib/__init__.py` breaks the
  `sphinxcontrib` namespace in a 1.0 build ("Could not import extension
  sphinxcontrib.applehelp (No module named 'pkg_resources')").
- Check the environment: `scmd --version` exists only in
  1.0, and
  `python -c "import sphinxcontrib.matlab as m; print(m.__file__)"`
  shows the installed copy (it does not run `conf.py`).
- uv: a `pyproject.toml` with the docs dependencies (`package = false` for a
  project that is not a Python package), `uv sync`, `uv run sphinx-build`.
  pip: a requirements file and a fresh `python -m venv`.
- Installing from a local checkout: a non-editable install of the folder or
  `uv build --wheel` reuses the checkout's git-ignored `build/` folder. Left
  from an older build, it brings back the removed
  `sphinxcontrib/__init__.py`, and every command then fails with
  `No module named 'pkg_resources'` (raised in `sphinxcontrib/__init__.py`).
  Delete `build/` in the checkout, use an editable install, or build with
  `uv build` (the source archive first, then the wheel from it).

## 4. `conf.py`

Follow the `conf.py` table of the migration guide:

- `matlab_src_dir = os.path.abspath("..")` -> `matlab_src_code_project_root = ".."`
  (relative to the folder of `conf.py`).
- Remove `matlab_keep_package_prefix` and `matlab_short_links`; one
  `ConfigError` lists every removed value that is set.
- Any other `matlab_*` name that is not a configuration value is an error:
  rename helper variables (`_matlab_root`).
- `add_module_names = False` -> `matlab_add_namespace_names = False`.
- Set `matlab_version` to the release the code targets (default R2026a;
  R2024a or newer). Set `matlab_src_encoding` only if every file without a
  byte-order mark uses that codec; otherwise leave it, and files that are
  not UTF-8 get `mat.encoding` (step 9).
- Exclusions: `matlab_src_exclude_patterns` replaces its defaults
  (`"README.*", "CHANGES.*", "CHANGELOG.*", "LICENSE.*", "CONTRIBUTING.*",
  "CODE_OF_CONDUCT.*", "SECURITY.*"`); copy them into your list. Patterns
  use `/` and match path references (folder names such as `"tests"` or
  globs such as `"**/private"`). Port an existing exclusion list one to one
  first, then review it: 1.0 parses files that 0.x could not, so some
  entries may be unnecessary (probe a doubtful entry with a small project
  whose include patterns select only it). Patterns from a wrapper script
  differ: a MATLAB `dir`-style `X/*` lists the files directly in `X`, while
  a 1.0 pattern `X/*` also matches subfolders (an excluded folder is not
  searched); a bare `*.json` matches only at the root; entries for the old
  Sphinx source or the copied tree become stale. 1.0 indexes every file
  below the root and
  warns about broken ones on every build: exclude unrelated code there
  (other projects, vendored copies, generated files), or select folders
  with `matlab_src_include_patterns`.
- `extensions`: `sphinxcontrib.matlab`; keep `myst_parser`, napoleon and
  others as they were.

## 5. Layout

- Drop a build step that copies or links the code into a source tree: the
  root may be outside the Sphinx source folder, and the patterns leave files
  out. Move the old Sphinx source (`conf.py`, static files, pages) into the
  docs folder if it lived inside the copied tree. Search the pages for the
  copied tree's folder name: `include` paths and `:doc:` links into it now
  point at the code (`../<code path>`) or at sidecar docs.
- A MATLAB project (`.prj`, `resources/project`) lists moved and deleted
  files; update it from MATLAB (`addFile`, `removeFile`) or let its owner do
  it.
- Notes next to the code (`README.md`, guides) become sidecar docs:
  `matlab_src_sidecar_suffixes = [".md"]` (needs `myst_parser`). Do not add
  their names to the exclusion patterns.

## 6. Pages: directives, roles and names

Dry-run the rewrite script, read the diff (`--summary` lists only the pages
and notes, for many pages), then write:

```console
python scripts/rewrite_pages.py --root <code root> docs
python scripts/rewrite_pages.py --root <code root> --write docs
```

It turns `module`/`automodule`/`currentmodule` (with or without `mat:`)
into `mat:folder`/`mat:autofolder`/`mat:currentfolder`, `:mat:mod:` into
`:mat:folder:`, dotted names into path references (`+pkg/Cls.m`,
`+pkg/Cls.m.method`), `:ref:` links to `modindex` into `mat-folderindex`
and `:friend-members:` into `:access-list-members:`, and removes
`:special-members:` and `:inherited-members:`. It lists what it cannot do
("check by hand"): an `automodule` of a class folder or the root (it
becomes `mat:currentfolder`, which documents nothing; check that the page
documents the class or its files), names not found below the root, bare
names it keeps as MATLAB names (after `.. module:: .`, say; they must be
unique, or use a path reference), `exception`, `decorator` and
`classmethod` directives (use `mat:staticmethod` for a static method).
It also reads directives inside Markdown block quotes (`> .. module::`).
Pages that a generator writes are replaced in step 8 instead.

Old directives and removed options are errors that drop the object, yet the
build exits 0 without `-W`. After the rewrite, nothing should match:

```console
grep -rnE "(auto|current)?module::|:mat:mod:|:(special|inherited)-members:|mat:(auto)?(exception|decorator)|mat:classmethod" docs
```

## 7. Help text

1.0 follows MATLAB's `help`: a comment block above the `function` or
`classdef` line wins over the one below it. List the files:

```console
python scripts/find_help_before_declaration.py <code root> --exclude "tests/*"
```

(`--exclude` globs are relative to the code root; the script does not read
`conf.py`, so pass the exclusions you set there.) Licence headers,
`%#ok` pragmas, `%%` section titles and commented-out signatures show up as
help. Moving them changes code files: ask the code owner, and change
comments only.

Roles in help text are not rewritten by step 6. A 0.x dotted name there
(``:class:`~pkg.+sub.Cls` ``) gives "reference target not found"; change
the comment to a path reference or a MATLAB name. Find them with:

```console
grep -rnE ':(mat:)?(class|func|meth|attr|mod|obj):`[^`]*[+@]' --include=*.m <code root>
```

## 8. Generated pages: `scmd apidoc`

Replace a page generator or folder-mirroring pages:

- `matlab_apidoc_output_dir = "api"` (any folder below the docs folder) and
  the other `matlab_apidoc_*` values in `conf.py`;
- `scmd apidoc --conf-dir docs`; add `api/index` to the root toctree;
- either commit the pages and check them in CI
  (`scmd apidoc --check --conf-dir docs`), or generate them before each
  build and do not commit them;
- remove the old generator.

The pages show public members. To keep private members, as many 0.x pages
did, set `autodoc_default_options = {"private-members": True}`. By default
there is one page per namespace (all its folders) plus Global for the files
outside any namespace, listed flat on the root page, at most
`matlab_apidoc_page_size` entries (100) per page, without `private/` files
and with the sidecar docs on their namespace's page: close to a 0.x
generator that wrote one page per namespace. `matlab_apidoc_group =
"folder"` gives one page per folder instead.

## 9. First build and warnings

```console
sphinx-build -b html -n -w warnings.txt docs docs/_build/html
```

Group the warnings by type and fix the largest groups first:

```console
python scripts/group_warnings.py warnings.txt
```

| Warning | Usual fix |
|---|---|
| "reference target not found" for another toolbox's classes (`sltest.*`, a vendor's namespace) | add them to `matlab_external_names` (below); MATLAB's own (`handle`, `matlab.*`, `Simulink.*`, `int32`) are in its default |
| "reference target not found" for other base classes that are not in the project | add them to `matlab_external_names`, or document them |
| "reference target not found" for a project class | its file is excluded (review the exclusions) or not documented |
| "reference target not found" for a dotted name with `+` or `@` | a 0.x name in help text (step 7) |
| "duplicate object description" | a hand-written page and a generated page document the same file: `:no-index:` on one |
| `toc.not_readable`, `ref.doc`, include file not found | a page still points into the copied tree (step 5) |
| `mat.ambiguous` | use the path reference the warning lists, or exclude copies |
| `mat.not_found` | a name the rewrite missed, a file now excluded or removed |
| `mat.empty_code_file` | an empty `.m` file: delete it, or exclude it |
| `mat.not_callable` | rename the file, or suppress if intended |
| `mat.encoding` | save the file as UTF-8; set `matlab_src_encoding` only if all files share one codec; suppress if intended |
| `mat.invalid_matlab` | the file is probably broken MATLAB; fix it or exclude it |
| docutils errors in help ("Unexpected indentation") | fix the help text (it is reStructuredText); comment-only changes |
| `image.not_readable` from help | paths in help are relative to the code file (0.x: the documentation page); fix the path |
| unknown directive / role / option | step 6 |
| MyST and Markdown page warnings | fix the page |

MATLAB's own classes are text by default (`matlab_external_names`); add
other toolboxes' names to its default list, and drop a 0.x
`nitpick_ignore_regex` that only covered MATLAB's names:

```python
from sphinxcontrib.matlab import DEFAULT_EXTERNAL_NAMES

matlab_external_names = [*DEFAULT_EXTERNAL_NAMES, r"sltest\..+"]
```

When only intended warnings remain, build with `-W --keep-going` and make
that the CI build. If help-text fixes are deferred, CI builds with `-n`
without `-W` meanwhile and tracks the warning count (`group_warnings.py`).
`scmd apidoc` skips the warnings named in `suppress_warnings`; it
still exits 0 after warnings.

## 10. Compare with the baseline

```console
python scripts/compare_inventories.py old/objects.inv _build/html/objects.inv --root <code root>
```

If the old pages were generated, build them first after step 6 alone (in a
scratch copy) and compare: 0.x with those (with `--root`), then those with
the `scmd apidoc` pages (two 1.0 builds: without `--root`).
Explain every object only one side has; group them and give counts.
Expected:

- 1.0 adds enumeration members and members the 0.x parser dropped after a
  line it could not parse ("Expected property", "Invalid signature" in the
  0.x warnings), and files 0.x could not place ("don't know which
  module").
- The script maps 0.x modules to 1.0 folders and `mat-modindex` to
  `mat-folderindex`. A class folder or the root as a module has no folder
  object in 1.0.
- 0.x alone may have members of a `classdef` inside a `%{ ... %}` block
  comment, pages of a copied source tree, the same object under a second
  short name (after `.. module:: .`), and files the migration removed (the
  old generator).
- Files re-included or newly excluded by the exclusion review.
- apidoc pages: no private members (step 8); class-folder method files are
  methods, not also functions (a 0.x page per class folder becomes the
  class on its namespace page); `private/` files are left out (with
  `"folder"` grouping they get pages).
- Anchors are `mat-<path reference>`: deep links and intersphinx users of
  the old names break once.

## 11. Help-text checks: `matlab-api-check`

A script that read the 0.x output to check help text breaks; replace it:

```python
matlab_api_check_rules = {  # start with warnings; make rules "error" as help improves
    "description": "warning",
    "method-description": "warning",
    "inputs": "warning",
    "outputs": "warning",
    "name-value": "warning",
    "sidecar-documented": "warning",
    "sidecar-links": "warning",
}  # property-, event-description, example and method-example warn by default
```

```console
sphinx-build -b matlab-api-check -d docs/_build/doctrees docs docs/_build/api-check
```

Reusing the HTML build's doctrees makes it fast. It checks every file below
the root that the patterns select, documented or not, so it may report
parse warnings (`mat.invalid_matlab`) that the HTML build did not. It exits
1 when a finding has severity `"error"`, else 0; do not add `-W` while
rules are warnings. An old script's Example-section and property-description
checks map to the rules `example`, `method-example` and
`property-description`. A pull-request comment from the JSON report, limited to the files
a change touches (a large project has thousands of findings; a comment has
a size limit):

```python
import json, re, subprocess, sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
changed = set(
    subprocess.run(
        ["git", "diff", "--name-only", sys.argv[2]], capture_output=True, text=True
    ).stdout.splitlines()
)
prefix = (
    sys.argv[3] if len(sys.argv) > 3 else ""
)  # code root relative to the repository


def file_of(ref):  # "+pkg/Cls.m.method" -> "+pkg/Cls.m"
    return re.match(r".*?\.(?:m|mlapp|md|rst)(?=\.|$)", ref)[0]


rows = [f for f in report["findings"] if prefix + file_of(f["reference"]) in changed]
print("| Object | Rule | Missing |\n|---|---|---|")
for f in rows:
    print(f"| `{f['reference']}` | {f['rule']} | {f['message']} |")
```

## 12. CI and local preview

- CI: the environment (step 3); with committed apidoc pages,
  `scmd apidoc --check --conf-dir docs` (or generate them first; nothing
  for hand-written pages); `sphinx-build -n -W --keep-going`; the
  api-check build (without `-W`, step 11). Any runner works: a Makefile
  target, Read the Docs (`build.jobs.pre_build`), or a stage in Jenkins or
  GitHub Actions running the same commands. CI steps that called the old
  wrapper (or a MATLAB build script) call these commands instead.
- Live preview (install `sphinx-autobuild`):
  `sphinx-autobuild docs docs/_build/html --watch <code folder> --pre-build "scmd apidoc --conf-dir docs --quiet"`
  (on Windows, use `/` in paths inside `--pre-build`).

## Checklist

- [ ] baseline kept (inventory, warnings, time, generated pages)
- [ ] fresh environment imports 1.0
- [ ] `conf.py` builds without `ConfigError`
- [ ] no old directives, roles or options remain
- [ ] help-before-declaration files reviewed with the code owner
- [ ] `scmd apidoc --check` exits 0 (if pages are committed)
- [ ] `-n -W` clean, or each remaining warning type explained
- [ ] every object only one side has is explained
- [ ] `matlab-api-check` runs; findings recorded
- [ ] old generator, copied tree and doc-check script removed or scheduled
