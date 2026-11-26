"""Combine the coverage of several runs of gauntlet.py and scenarios.py.

Usage, from the matlabdomain repo root:
  python test_slow/gauntlet/combine_coverage.py RUN [RUN ...] --out DIR

Each RUN is the --out folder of a run made with --coverage (its data is in
RUN/coverage/.coverage). Writes DIR/report.txt, DIR/coverage.json and
DIR/htmlcov, and prints the totals of each run and of all together.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import gauntlet as G


def totals(folder):
    """Return the totals line of the coverage report in ``folder``."""
    data = json.loads((folder / "coverage.json").read_text(encoding="utf-8"))
    t = data["totals"]
    return (
        f"lines {t['percent_statements_covered']:.1f}%, branches "
        f"{t['percent_branches_covered']:.1f}%, total {t['percent_covered']:.1f}%"
    )


def main():
    """Combine the runs' data and write the reports."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    rcfile = out / "coverage.toml"
    data = []
    for run in args.runs:
        cov = run.resolve() / "coverage"
        if not (cov / ".coverage").is_file():
            sys.exit(f"{run}: no coverage data (run it with --coverage)")
        data.append(str(cov / ".coverage"))
        print(f"{run}: {totals(cov)}")
    # the settings of the first run, with this folder as the data file
    text = (Path(data[0]).parent / "coverage.toml").read_text(encoding="utf-8")
    old = json.dumps(data[0])
    rcfile.write_text(
        text.replace(old, json.dumps(str(out / ".coverage"))), encoding="utf-8"
    )
    (out / ".coverage").unlink(missing_ok=True)
    subprocess.run(
        [
            G.PY,
            "-m",
            "coverage",
            "combine",
            "-q",
            "--keep",
            f"--rcfile={rcfile}",
            *data,
        ],
        cwd=G.REPO,
        check=True,
    )
    G.report_coverage(rcfile)


if __name__ == "__main__":
    main()
