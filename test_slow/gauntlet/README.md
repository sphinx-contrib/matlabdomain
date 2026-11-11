# Real-project gauntlet

Runs `scmd apidoc` and `sphinx-build` on real MATLAB projects and
reports crashes, warnings by subtype, timings, and serial vs `-j`
differences. Added in Phase 8 (14 projects, about 24,000 `.m` files).

| File | Purpose |
|---|---|
| `projects.toml` | The project list: name, Git URL, optional commit and options. Edit it to change what is tested. |
| `projects.lock.toml` | Written by `fetch.py`: the commit of each checkout. Commit it so other machines and later runs use the same commits. |
| `fetch.py` | Clones a missing project into `../repos/<name>` and moves an existing checkout to its commit. |
| `gauntlet.py` | Runs the gauntlet on the checkouts and writes `results.json` (the summary) and `manifest.json`. Clones nothing. |
| `compare.py` | Compares two runs, or a run and a saved summary. |
| `summaries/` | The baseline per platform (`linux.json`, `windows.json`: the `results.json` of the Phase 9 runs). |

`test_slow/repos/` (checkouts, shared with the profiling and Simulink tools) and
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
`<project>/api-check.{txt,json}`); `--variant` picks one.
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

## Expected (Phase 9, `summaries/`)

All 14 projects: exit 0 everywhere except `api` (exit 1: every project has
findings), no traceback or duplicate object, the rerun changes nothing, and
Windows and Linux give the same pages, warnings and api-check findings
(`compare.py` on the two summaries: `0 of 14 projects differ`; the `conf`
and `all` variants also match Phase 8).
matpower's serial and `-j` builds differ (13 pages, 65 `ref.equation`
warnings; for `api` only the warnings, the reports are identical): its
symlinked copies define each equation label twice, and Sphinx's math
domain merges them per worker. A file that is not valid UTF-8
decodes as ISO-8859-1 on Linux and Windows ANSI on Windows, so its warnings
may differ between the two.
