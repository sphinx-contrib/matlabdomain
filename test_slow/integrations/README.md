# Integration probes: several projects, one search, several versions

Two scripts that check the extension with
[sphinx-multiproject](https://github.com/readthedocs/sphinx-multiproject),
a search over several sites ([Pagefind](https://pagefind.app/)) and
[sphinx-multiversion](https://github.com/sphinx-contrib/multiversion), on
synthetic fixtures. They copy the fixtures to a work folder (default: the
system temp folder) and never change the checkout. pytest does not collect
them. The user documentation of the results is
`docs/user-guide/projects-and-versions.rst`.

| Path | What |
|---|---|
| `multiproject/` | Two projects, Alpha and Beta, with the same namespace (`+shared`), path references (`+shared/compute.m`, `util/helper.m`), page names and sidecar image names, but different help text. `docs/alpha` and `docs/beta` build on their own; `docs/conf.py` is the sphinx-multiproject root; `docs/combined` is one build over both (comparison only); `search/` is the search page over both. |
| `probe_multiproject.py` | `prepare`: API pages, builds, checks, Pagefind index of `<work>/serve/docs-prefix/`. `update`: changes Alpha's help, removes Beta's `+gizmo` namespace, rebuilds and re-indexes. |
| `multiversion/` | `rev1/` (tag `v1.0`) and `rev2/` (files that change, `DELETED` lists removed files; tag `v2.0` and branch `main`). Version two changes `area`'s help, adds `perimeter`, removes `legacyArea` and `legacy.rst`, and changes the sidecar doc and its image. |
| `probe_multiversion.py` | Builds a throwaway Git repository from `multiversion/` (local commits and tags only) and runs sphinx-multiversion in several scenarios (below). |

The fixtures' `conf.py` files write a JSON record per build (only when
`PROBE_RECORD` / `PROBE_RECORD_DIR` is set): source and conf folders,
project root, indexed files, the `sphinxcontrib.matlab` module file and
version, Sphinx, Python, and (multiversion) the documented commit. The
probes check that every build imported this checkout's matlabdomain.

## Environments

The multiproject probe runs on the project environment and on Sphinx
8.2. sphinx-multiversion 0.2.5 fails on Sphinx 9 (`Config.read()` takes its
overrides by keyword since 9.0; upstream issue #201, open PR #202), so its
probe needs Sphinx 8. Neither helper extension is a dependency: install
them into the environment you run the probe with. Pagefind runs through
`uvx` (override with the `PAGEFIND` environment variable).

```powershell
# Project environment (Sphinx 9.1.0 at the time of writing)
uv sync --frozen --all-extras
uv pip install sphinx-multiproject==1.0.0
# Sphinx 8.2 environment for sphinx-multiversion (".venv*" is ignored by Git)
uv venv --python 3.14 .venv-sphinx82
uv pip install --python .venv-sphinx82 -e ".[markdown]" sphinx==8.2.3 sphinx-multiproject==1.0.0 "sphinx-multiversion @ git+https://github.com/sphinx-contrib/multiversion@cd4c0db"
```

Checked on 2026-11-05, Windows 11, CPython 3.14.3, Git 2.55.0.windows.1,
matlabdomain `0.22.2.dev149+g0e789d298` plus the changes next to this file.
Both helper extensions were installed from a `git archive` of the
commits below (the `git+` line above is the equivalent, not what ran):

| Package | Project env | Sphinx 8.2 env |
|---|---|---|
| Sphinx | 9.1.0 | 8.2.3 |
| docutils | 0.22.4 | 0.21.2 |
| myst-parser | 5.1.0 | 5.1.0 |
| tree-sitter / tree-sitter-matlab | 0.26.0 / 1.3.0 | 0.26.0 / 1.3.1 |
| sphinx-multiproject | 1.0.0 (git `0ae48d4`, the 1.0.0 tag) | same |
| sphinx-multiversion | not usable | 0.2.5 (git `cd4c0db`; PyPI has 0.2.4) |
| Pagefind | 1.6.0 (`pagefind[bin]` via `uvx`) | same |

Linux and macOS were not run.

## Run

```powershell
.venv\Scripts\python test_slow\integrations\probe_multiproject.py prepare
.venv\Scripts\python test_slow\integrations\probe_multiproject.py update
.venv-sphinx82\Scripts\python test_slow\integrations\probe_multiproject.py prepare --work $env:TEMP\mp82
.venv-sphinx82\Scripts\python test_slow\integrations\probe_multiversion.py
```

Each step prints its checks and writes `<work>/<step>.json` (checks and
notes); exit 1 when a check fails. Results on 2026-11-05: multiproject
`prepare` 40/40 and `update` 13/13 on both environments; multiversion
62/62.

### Browser checks

Serve the work folder below a URL prefix and open the pages:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory <work>\serve
#  http://127.0.0.1:8765/docs-prefix/search/index.html?q=zorblax
python -m http.server 8766 --bind 127.0.0.1 --directory <multiversion work>\serve
#  http://127.0.0.1:8766/mv-prefix/v1.0/api/geo.html
```

What was seen:

- After `prepare`, `zorblax` gives 5 results, 3 Alpha and 2 Beta, titled
  `Alpha: …` / `Beta: …`, with a Project filter. Sub-results link objects,
  for example `/docs-prefix/beta/api/shared.html#mat-+shared/compute.m`.
  That link opens Beta's page with the `dt` of the object as the target,
  its CSS and sidecar image loaded and no 4xx responses. Alpha's own
  search (`alpha/search.html`) finds only Alpha's pages. The "Search all
  projects" link of each page opens the shared search page.
- After `update`, `frobnitz` finds only Alpha's `compute`, and `gadgetron`
  (the removed namespace) finds nothing.
- The multiversion site: `v1.0/api/geo.html` lists `area` and
  `legacyArea` (no `perimeter`), and its version list links
  `../../v2.0/api/geo.html`, which lists `area` and `perimeter`. On
  `v1.0/legacy.html` the v2.0 entry goes to `../v2.0/index.html`. Each
  page's footer reads "Documents v1.0 (release 1.0), built with
  matlabdomain 0.22.2.dev149+g0e789d298". In Sphinx's search, `legacyonly`
  finds a page in v1.0 only and `perimeteronly` in v2.0 only.

## Compatibility matrix

| Integration | Status | Evidence / limits |
|---|---|---|
| Several projects, one standalone build each, linked with intersphinx | Supported | Separate index, environment, inventory, images; same path references and page names are fine; `:external+alpha:mat:func:` links the other project, a bare role resolves locally; rebuilding Alpha leaves Beta untouched. |
| sphinx-multiproject 1.0.0, values through `config` | Supported | HTML identical to the standalone builds; `srcdir` moves to `docs/<project>`, `confdir` stays `docs`; relative root stays relative to `docs/<project>`. `scmd apidoc -c docs` (the root) stops: run it per project folder. |
| sphinx-multiproject 1.0.0, default (`<project>/conf.py`) | Limited | Sphinx 8.2: works, but a project `conf.py` may not set `extensions` and other early values. Sphinx 9: fails in the extension (`eval_config_file` needs a `Path`). |
| One output/doctree folder for several projects | Unsupported | Each build starts from scratch and pages of the other project stay. |
| One combined build over both projects (root above both) | Limited | `scmd apidoc` merges same-named namespaces into one page and lists duplicates by path, with a `mat.apidoc` warning each; the build itself has no warnings. Changes every path reference; not a multi-project solution. |
| Unified search (Sphinx, intersphinx, either extension) | Unsupported | Each build has its own search index. |
| Unified search with Pagefind 1.6.0 | Supported (external tool) | One query over both projects, project filter and titles, works under a URL prefix without settings. Needs the `layout.html` markers; fragment links need the search page's `processResult` (Sphinx's section ids are on `<section>`). Index fresh builds only. |
| sphinx-multiversion 0.2.5, Sphinx 8.2.3 | Supported, with committed API pages | Each version: own code, pages, inventory, sidecar docs and images; `release` from the revision; `conf.py` and matlabdomain from the checkout; navigation to the same page or the start page. Clean runs repeat byte for byte (without `.doctrees`/`.buildinfo`). |
| sphinx-multiversion, API pages generated once before it | Unsupported | `git archive` copies committed files only: no version gets API pages. |
| sphinx-multiversion, absolute project root | Unsupported | Every version documents the checkout's code. |
| sphinx-multiversion on Sphinx 9 | Unsupported (upstream) | Fails before building. |
| Revision with a top-level `sphinxcontrib/` | Limited | Imported instead of the installed extension; `PYTHONSAFEPATH=1` prevents it. |
| Linux, macOS; Read the Docs hosting; Pagefind multisite (`mergeIndex`) | Untested | |

## Other findings

- A typo in a `matlab_*` name passed through sphinx-multiproject's `config`
  was silently ignored; the build now stops with a `ConfigError`
  (`tests/test_config.py`).
- sphinx-multiversion on Python 3.12+: `-d DIR` is split (`DIR` becomes a
  page name; upstream issue #170), use
  `--doctree-dir=DIR`; a run into the same folder rebuilds everything and
  leaves `.buildinfo.bak`; the output contains `.doctrees`; the default
  `smv_released_pattern` matches no tag.
- Pagefind takes `image` metadata from the first image, as a relative URL;
  the search page hides images. Heading `¶` marks are indexed text.
- Git may miss a same-size change to a file copied with its old mtime
  (`shutil.copy2`); the probe copies with `shutil.copy`.
