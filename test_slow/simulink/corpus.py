"""Read every Simulink file below some folders and report what the reader does.

    python test_slow/simulink/corpus.py FOLDER [FOLDER ...] [--csv OUT]

Use it on the models that ship with a new MATLAB release
(``<matlabroot>/toolbox``) and on real projects (the gauntlet's
``test_slow/repos/``). Files are read once per content (SHA-256). It prints the
kinds and layouts, the mask forms, the average time to classify and to
read a file, the slowest files and every error; ``--csv`` writes one row
per file. Exit 1 if the reader crashed (an exception other than
``SimulinkFileError``).
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import os
import re
import time
import zipfile
from pathlib import Path

from sphinxcontrib.mat_simulink import SimulinkFileError, classify, read_diagram

SUFFIXES = (".slx", ".mdl")
_FORMS = [
    ("element", rb"<Mask[ >]"),
    ("object", rb'ClassName="Simulink\.Mask"|\$ClassName\s+"Simulink\.Mask"'),
    ("parameters", rb'(?m)^\s*MaskPromptString\s|<P Name="MaskPromptString">'),
]


def files(folders):
    for folder in folders:
        for top, dirs, names in os.walk(folder, onerror=lambda _: None):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in names:
                if name.lower().endswith(SUFFIXES):
                    yield Path(top, name)


def mask_forms(path: Path, data: bytes) -> str:
    texts = [data]
    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(path) as z:
                texts = [
                    z.read(i)
                    for i in z.infolist()
                    if i.filename.lower().startswith("simulink/")
                    and i.filename.lower().endswith(".xml")
                    and i.file_size < 256 * 1024 * 1024
                ]
        except (zipfile.BadZipFile, OSError):
            return ""
    return "+".join(
        label for label, rx in _FORMS if any(re.search(rx, t) for t in texts)
    )


def _attempt(step, path):
    """Return ``(result, error)`` of ``step(path)``."""
    try:
        return step(path), ""
    except SimulinkFileError as err:
        return None, str(err)
    except Exception as err:  # the point of the run: report, do not stop
        return None, f"CRASH {type(err).__name__}: {err}"


def check(path: Path, data: bytes) -> dict:
    row = {"path": str(path), "size": len(data), "mask_forms": mask_forms(path, data)}
    t0 = time.perf_counter()
    row["classified"], error = _attempt(classify, path)
    t1 = time.perf_counter()
    diagram = None
    if not error:
        diagram, error = _attempt(read_diagram, path)
    t2 = time.perf_counter()
    row["kind"] = diagram.kind if diagram else ""
    row["layout"] = diagram.layout if diagram else ""
    row["release"] = diagram.release if diagram else ""
    row["error"] = error
    row["classify_ms"] = round(1000 * (t1 - t0), 2)
    row["read_ms"] = round(1000 * (t2 - t1), 2)
    return row


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Read every Simulink file below FOLDERs."
    )
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--csv", type=Path, help="write one row per file")
    args = parser.parse_args(argv)
    rows, seen = [], set()
    start = time.perf_counter()
    for path in files(args.folders):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest not in seen:
            seen.add(digest)
            rows.append(check(path, data) | {"sha256": digest})
    if not rows:
        print("no Simulink files")
        return 0
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    ok = [r for r in rows if not r["error"]]
    print(f"{len(rows)} unique files in {time.perf_counter() - start:.0f} s")
    n = len(rows)
    print(
        f"classify {sum(r['classify_ms'] for r in rows) / n:.1f} ms, "
        f"read {sum(r['read_ms'] for r in rows) / n:.1f} ms on average"
    )
    for key, count in sorted(
        collections.Counter((r["kind"], r["layout"]) for r in ok).items()
    ):
        print(f"  {count:6} {key[0]} ({key[1]})")
    print("mask forms:", dict(collections.Counter(r["mask_forms"] for r in rows)))
    for row in sorted(rows, key=lambda r: r["read_ms"])[-3:]:
        print(f"  slow {row['read_ms']:.0f} ms {row['path']}")
    errors = [r for r in rows if r["error"]]
    for row in errors:
        print(f"  ERROR {row['path']}: {row['error'][:160]}")
    return 1 if any(r["error"].startswith("CRASH") for r in errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
