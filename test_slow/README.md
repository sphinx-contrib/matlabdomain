# Slow tests

Checks too slow or too large for the test suite (`tests/`); pytest does not
collect them.

| Folder | Purpose |
|---|---|
| `gauntlet/` | The real-project gauntlet: `sphinx-matlab-apidoc` and `sphinx-build` on real MATLAB projects. Details: [gauntlet/README.md](gauntlet/README.md). |
| `repos/` | The gauntlet's checkouts (`fetch.py` creates it; ignored by Git). |
| `profiling/` | The profiling harness (a parse sweep and a `sphinx-build` of vhlab-toolbox-matlab, from the gauntlet's checkouts) and its recorded results. |
| `naming/` | `compare_render.py`: snapshots the rendered anchors, links, inventories and warnings of the test roots and docs, and compares two code versions. |
| `integrations/` | Probes with sphinx-multiproject, one search over several sites (Pagefind) and sphinx-multiversion. Details: [integrations/README.md](integrations/README.md). |
| `simulink/` | The Simulink file survey, corpus check and naming probe, run for each new MATLAB release. Details: [simulink/README.md](simulink/README.md). |

## Run the gauntlet

Needs Git, network access for the first fetch, and disk space for the
checkouts (about 5 GB for the 14 projects). Run from the `matlabdomain`
repo root in the project's environment (`uv sync --all-extras`; on Windows
use `.venv\Scripts\python` for `python`).

1. Fetch the projects in `gauntlet/projects.toml` into `repos/`.
   Existing checkouts are reused; nothing is cloned twice.

   ```bash
   python test_slow/gauntlet/fetch.py
   ```

2. Run the gauntlet. Output goes to `gauntlet/runs/latest` (`--out` picks
   another folder); NAME arguments limit the projects.

   ```bash
   python test_slow/gauntlet/gauntlet.py --jobs
   python test_slow/gauntlet/gauntlet.py matpower chebfun --trials 1
   ```

   Exit 0: no crash, traceback, duplicate object, changed rerun, serial vs
   `-j` difference, or checkout off its commit. Otherwise the problems are
   listed at the end.

3. Compare with a saved summary (or another run folder):

   ```bash
   python test_slow/gauntlet/compare.py test_slow/gauntlet/summaries/phase8-linux.json test_slow/gauntlet/runs/latest
   ```

   It lists, per project, changes in the commit, pages, exit codes and
   warnings by subtype; for two run folders also the generated pages and
   the warnings themselves.

To test other projects, edit `gauntlet/projects.toml` (a project without
`commit` stays on the commit of its first fetch, recorded in
`gauntlet/projects.lock.toml`; `fetch.py --update` moves it to the newest)
and run `fetch.py` again. To keep a run's summary, copy its `results.json`
to `gauntlet/summaries/`.
