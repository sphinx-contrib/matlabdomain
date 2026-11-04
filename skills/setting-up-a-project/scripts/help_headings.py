"""Survey the section headings in the help of a MATLAB project.

Counts the comment lines that are a heading alone (``% Inputs:``), with the
number of files, so the project's headings can go into
``napoleon_custom_sections``. Also counts lines that start with a capital
label and a colon followed by text (``% Note: ...``), which are usually not
headings. Changes nothing.

Usage:
    python help_headings.py ROOT [--skip FOLDER ...]
"""

import argparse
import collections
import os
import re

parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
parser.add_argument("root")
parser.add_argument("--skip", nargs="*", default=["docs", "node_modules"])
args = parser.parse_args()

alone = re.compile(r"^\s*%+\s*([A-Za-z][A-Za-z0-9 /&()-]{0,40}?)\s*:{1,2}\s*$")
inline = re.compile(r"^\s*%+\s*([A-Z][A-Za-z ]{0,30}?)\s*:\s+\S")
headings = collections.Counter()
files = collections.defaultdict(set)
labels = collections.Counter()
for folder, subfolders, names in os.walk(args.root):
    subfolders[:] = [
        d for d in subfolders if d not in args.skip and not d.startswith(".")
    ]
    for name in names:
        if not name.endswith(".m"):
            continue
        path = os.path.join(folder, name)
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if m := alone.match(line):
                    headings[m.group(1)] += 1
                    files[m.group(1)].add(path)
                elif m := inline.match(line):
                    labels[m.group(1)] += 1

print("== Headings alone on a line: lines / files")
for heading, count in headings.most_common():
    print(f"  {heading!r}: {count} / {len(files[heading])}")
print("== 'Label: text' lines (top 30)")
for label, count in labels.most_common(30):
    print(f"  {label!r}: {count}")
