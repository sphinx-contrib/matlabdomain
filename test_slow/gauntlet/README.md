# Real-project gauntlet

Runs `scmd apidoc` and `sphinx-build` on real MATLAB projects and
reports crashes, warnings by subtype, timings, and serial vs `-j`
differences (15 projects, about 24,000 `.m` files). `scenarios.py` uses the
rest of the interface on the same checkouts (below).

| File | Purpose |
|---|---|
| `projects.toml` | The project list: name, Git URL, optional commit and options. Edit it to change what is tested. |
| `projects.lock.toml` | Written by `fetch.py`: the commit of each checkout. Commit it so other machines and later runs use the same commits. |
| `fetch.py` | Clones a missing project into `../repos/<name>` and moves an existing checkout to its commit. |
| `gauntlet.py` | Runs the gauntlet on the checkouts and writes `results.json` (the summary) and `manifest.json`. Clones nothing. |
| `compare.py` | Compares two runs, or a run and a saved summary. |
| `scenarios.py` | End-to-end scenarios: the options, flags, directives, roles, builders, rebuilds and error paths the gauntlet's default runs never use, each with checks of the expected behavior. |
| `combine_coverage.py` | Combines the coverage of several runs made with `--coverage`. |
| `summaries/` | The baseline per platform (`linux.json`, `windows.json`): the `results.json` of a full run with `--jobs`. `environment` in each names the date and the commit. |

`test_slow/repos/` (checkouts, shared with the profiling tools) and
`runs/` (output) are ignored by Git.

## Run

From the `matlabdomain` repo root, with the project's environment
(`uv sync --all-extras`; on Windows use `.venv\Scripts\python`):

```bash
python test_slow/gauntlet/fetch.py               # or gauntlet.py --fetch
python test_slow/gauntlet/gauntlet.py --jobs     # all projects -> runs/latest
python test_slow/gauntlet/gauntlet.py matpower --trials 1 --out test_slow/gauntlet/runs/mp
python test_slow/gauntlet/compare.py test_slow/gauntlet/summaries/linux.json test_slow/gauntlet/runs/latest
```

NAME arguments keep the projects whose name contains one of them. For each
project, `gauntlet.py` generates the pages 3 times (`--trials`), reruns with
`-f` (expect nothing created or updated), and builds with the defaults
(`conf`), with `matlab_auto_link = "all"` (`all`) and with `-b
matlab-api-check` (`api`, the default rules; its reports are kept as
`<project>/api-check.{txt,json}`); `--variant` picks one. `--variant
inherited` (not in the default set) builds with
`-D matlab_inherited_members=1 -D autodoc_default_options.inherited-members=`,
so every class documents
its inherited members; compare its `html_bytes`, `html_files` and `wall_s`
with `conf`'s to see what `:inherited-members:` costs:

```console
python test_slow/gauntlet/gauntlet.py --jobs --variant conf --variant inherited
```
`--jobs` builds each again with `-j auto` and compares the HTML,
`objects.inv` (the api-check reports) and warnings. On Windows, `-j` runs
serially (no fork).
`gauntlet.py` exits 1 on a problem: a checkout not at its commit, a nonzero
exit code (`api`: 1 with findings of severity `error`, else 0), a
traceback, a duplicate object, a rerun that changes pages, or a
serial vs `-j` difference (unless `parallel_may_differ`).

`--quickstart` runs `scmd quickstart -q` instead, on a temporary
`git worktree` of each checkout (Sphinx source folder `docs`, or
`sphinx-docs` when `docs` exists), then `sphinx-build -E -n` of what it
wrote, and removes the worktree. A problem: a nonzero exit code, a
traceback, a duplicate object, or a checkout that changed. It prints a
table of API pages, indexed files, warnings and times per project.

```bash
python test_slow/gauntlet/gauntlet.py --quickstart --out test_slow/gauntlet/runs/quickstart
```

To update a baseline, copy `runs/<name>/results.json` to `summaries/<platform>.json`.

## Scenarios

`gauntlet.py` builds every project with the default configuration, so it
reaches about 78% of the code. `scenarios.py` runs the real `scmd` and
`sphinx-build` on the same checkouts (and on the repo's `docs/`) with the
rest of the interface: apidoc's options and
flags, incremental rebuilds after edits, hand-written pages with every
directive and role, intersphinx between projects, every invalid
configuration value, quickstart answered on stdin and from answers files,
`scmd skills`, broken input, the other configuration
values and builders, api-check settings, and classes with events. Each
scenario checks what correct behavior is (exit codes, warnings, pages,
links); a project that is changed is copied first.

```bash
python test_slow/gauntlet/scenarios.py --list
python test_slow/gauntlet/scenarios.py                  # all 14, about 8 minutes
python test_slow/gauntlet/scenarios.py incremental      # one
```

Exit 1 on a failed check, a traceback, or a scenario that raised. A check
marked with a bug id (`bug="E2E-3"`) is a known bug: it is listed as known
while it fails, and the run asks to remove the mark when it passes. The
ids are described in `matlabdomain-ai-files/gauntlet-coverage.md`.

## Coverage

`--coverage` (in `gauntlet.py` and `scenarios.py`) measures every child
process with the test suite's coverage settings (`[tool.coverage]` of
`pyproject.toml`, plus what it takes to follow child and `-j` worker
processes) and writes `OUT/coverage/report.txt`, `coverage.json` and
`htmlcov/`. To see what all the end-to-end runs reach together:

```bash
python test_slow/gauntlet/gauntlet.py --jobs --coverage --out runs/g
python test_slow/gauntlet/gauntlet.py --quickstart --coverage --out runs/q
python test_slow/gauntlet/scenarios.py --coverage --out runs/s
python test_slow/gauntlet/combine_coverage.py runs/g runs/q runs/s --out runs/all
```

With coverage the runs take about 1.5 times as long.

## Repeatable commits

- `commit` in `projects.toml` pins a project (a SHA, best in full, or a tag).
- Without `commit`, the first fetch takes the default branch HEAD and records
  it in `projects.lock.toml`; later fetches keep it.
  `fetch.py --update` moves those projects to the newest HEAD.
- A checkout with local changes is not moved; `fetch.py` reports it.
  `fetch.py --reset` discards the changes (`git reset --hard`,
  `git clean -fd`).
- New checkouts are shallow (depth 1) and set `core.symlinks=true`: with
  `false`, Git for Windows writes symlinks as text files (matpower has 807,
  so its pages differed from Linux).

Checkouts from before this folder existed (`test_slow/artifacts/<name>/repo`)
can be moved instead of fetched again:

```bash
for d in test_slow/artifacts/*/repo; do n=$(basename "$(dirname "$d")"); mv "$d" "test_slow/repos/$n"; done
```

Checkouts from before `test_slow/repos` existed (`test_slow/gauntlet/repos`) can
be moved the same way: `mv test_slow/gauntlet/repos test_slow/repos`.

## Expected (`summaries/`, 2026-11)

The Linux baseline (2026-11-24) has all 15 projects. The Windows baseline
(2026-11-12) is older: it lacks widgets-toolbox (added 2026-11-19), its
matpower `all` build counts 3492 `mat.ambiguous` warnings where the Linux
one counts 3213 (since then an ambiguous name in help text warns once per
help text), and it was made when Simulink files were read (every api-check
summary has a `simulink_files` count, and WEC-Sim and WEC-Sim_Applications
have the pages and warnings of their 19 and 60 Simulink files).
`compare.py` shows all of this until the Windows baseline is made
again. All projects: exit 0 everywhere except `api` (exit 1: every project
has findings), no traceback or duplicate object, the rerun changes nothing,
and Windows and Linux give the same pages, warnings and api-check findings.
`compare.py` on the two summaries prints `15 of 15 projects differ`
(`1 of 15` with a current Windows baseline): matpower, in its `-j` rows.
On Windows `-j` builds serially, so those rows say `identical` there.
On Linux, matpower's serial and `-j` builds differ (6 pages with the
defaults, 10 with `matlab_auto_link = "all"`, 39 `ref.equation` warnings;
for `api` only the warnings, the reports are identical): its
symlinked copies define each equation label twice, and Sphinx's math
domain merges them per worker. A file that is not valid UTF-8
decodes as ISO-8859-1 on Linux and Windows ANSI on Windows, so its warnings
may differ between the two.
