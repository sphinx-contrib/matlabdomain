"""Profile the parse of every ``.m`` file of a tree (tree-sitter cost).

Usage::

    python test_slow/profiling/profile_build.py [SRC_DIR]

``SRC_DIR`` defaults to the gauntlet's ``vhlab-toolbox-matlab`` checkout
(``test_slow/gauntlet/fetch.py``). Each file is parsed on its own, with
failures tallied instead of stopping the sweep. Writes cProfile stats to
``parse.prof`` (ignored by Git) and prints the top functions by cumulative
time; inspect with ``uvx snakeviz test_slow/profiling/parse.prof``.

The Phase 1 baseline and its findings are in ``plan-history.md`` (Phase 1).
"""

from __future__ import annotations

import cProfile
import pstats
import sys
import time
from pathlib import Path

from sphinxcontrib.mat_types import MatObject

HERE = Path(__file__).resolve().parent
DEFAULT_SRC = HERE / ".." / "repos" / "vhlab-toolbox-matlab"
PROFILE_OUT = HERE / "parse.prof"

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
        print(f"First {min(10, len(_failures))} parse failures:")
        for path, err in _failures[:10]:
            print(f"  - {path}\n      {err}")
        print()

    print("Top 20 by cumulative time:")
    pstats.Stats(str(PROFILE_OUT)).strip_dirs().sort_stats("cumulative").print_stats(20)


if __name__ == "__main__":
    main()
