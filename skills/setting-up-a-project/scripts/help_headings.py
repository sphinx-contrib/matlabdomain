"""Survey the section headings in the help of a MATLAB project.

Counts the comment lines that are a heading alone (``% Inputs:``), with the
number of files, so the project's headings can go into
``napoleon_custom_sections``. Spellings that differ only in case are counted
together (napoleon ignores case). Marks napoleon's built-in sections and the
headings napoleon can never match (only letters, digits, ``_`` and spaces
work: ``Name-Value Pairs`` does not). Also counts lines that start with a
capital label and a colon followed by text (``% Note: ...``), which are
usually not headings. Changes nothing.

The files are those of the extension's index, so ``--exclude`` takes the
patterns of ``matlab_src_exclusion_patterns`` (it replaces the defaults, as
the configuration value does). Only help blocks are read: comment blocks
right before or right after a ``function`` or ``classdef`` line, and the
first comment block of a file; ``--all-comments`` reads every comment.

Usage:
    python help_headings.py ROOT [--exclude PATTERN ...] [--all-comments]
"""

import argparse
import collections
import logging
import os
import re

from sphinxcontrib.mat_types import (
    DEFAULT_EXCLUSION_PATTERNS,
    IndexSettings,
    build_index,
)

parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
parser.add_argument("root")
parser.add_argument("--exclude", nargs="*", default=list(DEFAULT_EXCLUSION_PATTERNS))
parser.add_argument("--all-comments", action="store_true")
args = parser.parse_args()

NAPOLEON = {
    "args", "arguments", "attention", "attributes", "caution", "danger",
    "error", "example", "examples", "hint", "important", "keyword args",
    "keyword arguments", "methods", "note", "notes", "other parameters",
    "parameters", "receive", "receives", "return", "returns", "raise",
    "raises", "references", "see also", "tip", "todo", "warning", "warnings",
    "warn", "warns", "yield", "yields",
}  # fmt: skip
alone = re.compile(r"^\s*%+\s*([A-Za-z][A-Za-z0-9 /&()_-]{0,40}?)\s*:{1,2}\s*$")
inline = re.compile(r"^\s*%+\s*([A-Z][A-Za-z ]{0,30}?)\s*:\s+\S")
comment = re.compile(r"^\s*%(?![{}])")
declaration = re.compile(r"^\s*(function|classdef)\b")
matchable = re.compile(r"^(\s|\w)+$")


def help_lines(lines):
    """Return help-block comment lines (all comments with --all-comments)."""
    if args.all_comments:
        return [line for line in lines if comment.match(line)]
    out, block, before, seen_code = [], [], "", False
    for line in [*lines, ""]:
        if comment.match(line):
            block.append(line)
            continue
        if block:
            first_block = not seen_code
            if first_block or declaration.match(before) or declaration.match(line):
                out.extend(block)
            block = []
        if line.strip():
            seen_code = True
        before = line
    return out


logging.getLogger("sphinx").addHandler(logging.NullHandler())  # inventory.py shows them
settings = IndexSettings(root=os.path.abspath(args.root), exclude=tuple(args.exclude))
headings = collections.defaultdict(collections.Counter)
files = collections.defaultdict(set)
labels = collections.Counter()
for path in build_index(settings).index:
    if not path.endswith(".m"):
        continue
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for line in help_lines(lines):
        if m := alone.match(line):
            heading = m.group(1)
            headings[heading.lower()][heading] += 1
            files[heading.lower()].add(path)
        elif m := inline.match(line):
            labels[m.group(1)] += 1


def note(key):
    if key in NAPOLEON:
        return "  [napoleon built-in]"
    if not matchable.match(key):
        return "  [napoleon cannot match: rename it in the code]"
    return ""


print("== Headings alone on a line: lines / files, spellings")
for key, spellings in sorted(headings.items(), key=lambda kv: -kv[1].total()):
    shown = ", ".join(f"{s!r} {n}" for s, n in spellings.most_common())
    print(f"  {spellings.total()} / {len(files[key])}: {shown}{note(key)}")
print("== 'Label: text' lines (top 30)")
for label, count in labels.most_common(30):
    print(f"  {label!r}: {count}")
