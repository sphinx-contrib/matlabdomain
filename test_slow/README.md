# Slow tests

Checks too slow or too large for the test suite (`tests/`); pytest does not
collect them.

| Folder | Purpose |
|---|---|
| `gauntlet/` | The real-project gauntlet: `scmd apidoc` and `sphinx-build` on real MATLAB projects. Details: [gauntlet/README.md](gauntlet/README.md). |
| `repos/` | The gauntlet's checkouts (`fetch.py` creates it; ignored by Git). |
| `profiling/` | The profiling harness (a parse sweep and a `sphinx-build` of vhlab-toolbox-matlab, from the gauntlet's checkouts). |
| `naming/` | `compare_render.py`: snapshots the rendered anchors, links, inventories and warnings of the test roots and docs, and compares two code versions. |
| `integrations/` | Probes with sphinx-multiproject, one search over several sites (Pagefind) and sphinx-multiversion. Details: [integrations/README.md](integrations/README.md). |
| `simulink/` | The Simulink file survey, corpus check and naming probe, run for each new MATLAB release. Details: [simulink/README.md](simulink/README.md). |

## Run the gauntlet

**Needs:** Git; network access the first time (it clones 14 open-source
MATLAB projects at pinned commits); about 4 GB of disk for the checkouts in
`repos/`; the project's environment (`uv sync`). No MATLAB.

**One command**, from the `matlabdomain` repo root:

```bash
uv run python test_slow/gauntlet/gauntlet.py --fetch --jobs
```

`--fetch` clones the missing projects and moves each checkout to the commit
in `gauntlet/projects.lock.toml` (later runs reuse the checkouts). `--jobs`
also builds each project with `-j auto` and compares. NAME arguments limit
the projects (`... gauntlet.py matpower chebfun --trials 1`).

**Time:** about 20 minutes on Linux and 10 on Windows (the saved
baselines), plus the first clone. Output: `gauntlet/runs/latest`.

**Reading the result:** exit 0 means no crash, traceback, duplicate object,
rerun that changes pages, serial vs `-j` difference (except matpower,
expected), or checkout off its commit. Exit 1 lists each problem at the end,
as `project: problem`. Then compare with the saved baseline for your
platform; the run prints the command:

```bash
uv run python test_slow/gauntlet/compare.py test_slow/gauntlet/summaries/linux.json test_slow/gauntlet/runs/latest
```

It lists, per project, changes in pages, exit codes and warnings by
subtype. A change is not a failure: decide whether it is intended. When
it is, replace `summaries/<platform>.json` with the run's `results.json`
(one baseline per platform). More options and what is expected:
[gauntlet/README.md](gauntlet/README.md).
