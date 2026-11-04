"""List MATLAB files with comments above their function or classdef line.

Usage: python find_help_before_declaration.py ROOT [--exclude GLOB ...]

MATLAB's help, and matlabdomain 1.0, take a comment block above the
declaration as the help, before the block below it. That catches licence
headers, ``%#ok`` pragmas, ``%%`` section titles and commented-out
signatures. For each file it prints the first comment line; move the
comments below the help, or put the help first.
"""

import argparse
import fnmatch
import re
from pathlib import Path

DECLARATION = re.compile(r"^\s*(function|classdef)\b")


def first_lines(path):
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    for line in text.splitlines():
        if line.strip():
            yield line


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="fnmatch glob relative to ROOT, such as 'tests/*' (repeatable)",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    found = 0
    for path in sorted(root.rglob("*.m")):
        rel = path.relative_to(root).as_posix()
        if any(fnmatch.fnmatch(rel, g) for g in args.exclude):
            continue
        first = None
        for line in first_lines(path):
            if line.lstrip().startswith("%"):
                first = first or line.strip()
                continue
            if first and DECLARATION.match(line):
                print(f"{rel}: {first[:100]}")
                found += 1
            break
    print(f"\n{found} file(s)")


if __name__ == "__main__":
    main()
