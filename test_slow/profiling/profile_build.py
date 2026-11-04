"""Profiling harness for SCM's eager parse cost (Phase 1 "before" baseline).

The current extension parses **every** ``.m`` file up front on ``builder-inited``
(``analyze()`` -> ``MatObject.parse_mfile`` -> tree-sitter). On a large tree this
is the lock-up we intend to fix (Phase 6, lazy parsing).

Why a direct parse-sweep instead of a full ``sphinx-build``: on the bundled
``vhlab-toolbox-matlab`` tree the current code **crashes** on at least one
unparsable ``.m`` file (``AttributeError: 'NoneType' ... 'text'`` in
``mat_tree_sitter_parser``), aborting the whole ``builder-inited`` handler. That
fault-intolerance is exactly what Phase 5 fixes, but it also means a
Sphinx-driven build cannot complete today. So we profile the eager parse
directly, wrapping each file in try/except to (a) measure the true parse cost
across all files and (b) tally the files that crash the current parser as a
seed for the Phase 5 bug list.

Usage
-----
    python test_slow/profiling/profile_build.py [SRC_DIR]

Defaults ``SRC_DIR`` to the largest bundled fixture
(``../gauntlet/repos/vhlab-toolbox-matlab``). Writes cProfile stats to
``before.prof`` and prints top cumulative-time functions plus a parse-failure
summary. Inspect interactively with::

    pip install snakeviz
    snakeviz test_slow/profiling/before.prof

After the Phase 6 lazy rework, re-profile a real ``sphinx-build`` (see the
``conf.py`` beside this file) to capture ``after.prof`` and quantify the speedup.

Baseline captured (Phase 1 — TRUE baseline)
-------------------------------------------
Env: git worktree at commit 0ce8fa0 (../scm-baseline), uv, standard (GIL)
CPython 3.14.6, tree-sitter 0.22.3, tree-sitter-matlab 1.0.4, Sphinx 9.1.0.
Suite rerun (2026-10-23): 137 passed, 4 xfailed, 85% coverage, ~12.6 s.
The plan's earlier 80% coverage figure was not reproduced; reconcile the
coverage-tool/settings difference before using coverage as a comparison target.
Tree: vhlab-toolbox-matlab/repo, 1726 .m files
(https://github.com/VH-Lab/vhlab-toolbox-matlab.git @ ac85cf5cb233).
  * Eager parse wall time: ~6.1-6.7 s (3.5-3.9 ms/file), 0 parse failures.
  * Dominant avoidable overhead (motivates Phase 4/6):
      - tree-sitter ``Language.query`` recompiled on EVERY isFunction/isClass
        call (~2.66 s). Should be module-level compiled queries.
      - ``importlib.metadata.version("tree_sitter")`` called once PER FILE inside
        parse_mfile (~1.7 s in package-metadata parsing). Should be cached once.

Current branch (tree-sitter 0.26.0 / tree-sitter-matlab 1.3.0)
--------------------------------------------------------------
``before.prof`` (2026-10-24): project ``.venv`` rebuilt with ``uv venv --clear``
and ``uv sync --locked --all-extras`` (free-threaded CPython 3.14.3, Sphinx
9.1.0), command ``.venv/bin/python test_slow/profiling/profile_build.py`` from
the repo root: ~17-19 s across captures, 1725 OK, 1 failure. Metadata, logs and
the reproduction scripts are in ``results/`` (``capture.py`` documents usage).

* Native crash (exit 139 / SIGSEGV), fixed: tree-sitter 0.26.0's ``Point.row``
  getter returns a borrowed reference, corrupting the heap on standard (GIL)
  CPython builds. ``get_row`` now indexes ``point[0]``.
* +vlt/+plot/hist2d.m (AttributeError: 'NoneType' has no attribute 'text'):
  tree-sitter-matlab >=1.2.3 parses the dotted name ``vlt.plot.hist2d`` as
  ``property_name``, which the function query's ``name: (identifier)`` misses.
  Grammar-driven; deferred to the Phase 5 bug list.
* Slowdown, same workload on CPython 3.14.6 (GIL), harness wall: reference
  6.5 s; current code + matlab 1.0.4 10.0 s (QueryCursor.captures and a
  per-call query compile from the 0.26 port); + matlab 1.3.0 17.6 s (query
  compilation ~2.6-3.4x slower with the new grammar). The tree-sitter core
  upgrade alone is neutral; free-threaded .venv is within noise. Phases 4/6.
"""

from __future__ import annotations

import cProfile
import pstats
import sys
import time
from pathlib import Path

from sphinxcontrib.mat_types import MatObject

HERE = Path(__file__).resolve().parent
DEFAULT_SRC = HERE / ".." / "gauntlet" / "repos" / "vhlab-toolbox-matlab"
PROFILE_OUT = HERE / "before.prof"

_failures: list[tuple[str, str]] = []
_ok = 0


def _sweep(src_dir: Path) -> None:
    global _ok
    for mfile in sorted(src_dir.rglob("*.m")):
        name = mfile.stem
        path = str(mfile.parent)
        try:
            MatObject.parse_mfile(str(mfile), name, path)
            _ok += 1
        except Exception as exc:
            _failures.append((str(mfile), f"{type(exc).__name__}: {exc}"))


def main() -> None:
    src_dir = (
        Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SRC.resolve()
    )
    total = sum(1 for _ in src_dir.rglob("*.m"))
    print(f"Profiling eager parse of {total} .m files under:\n  {src_dir}\n")

    profiler = cProfile.Profile()
    start = time.perf_counter()
    profiler.enable()
    _sweep(src_dir)
    profiler.disable()
    elapsed = time.perf_counter() - start

    profiler.dump_stats(str(PROFILE_OUT))

    print(f"Parsed OK : {_ok}")
    print(f"Failed    : {len(_failures)}")
    print(f"Wall time : {elapsed:.2f}s  ({elapsed / max(total, 1) * 1000:.2f} ms/file)")
    print(f"Profile   : {PROFILE_OUT}\n")

    if _failures:
        print(
            f"First {min(10, len(_failures))} parse failures (Phase 5 bug-list seed):"
        )
        for path, err in _failures[:10]:
            print(f"  - {path}\n      {err}")
        print()

    print("Top 20 by cumulative time:")
    pstats.Stats(str(PROFILE_OUT)).strip_dirs().sort_stats("cumulative").print_stats(20)


if __name__ == "__main__":
    main()
