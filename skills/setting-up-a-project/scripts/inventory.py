"""Read-only inventory of a MATLAB project, with the extension's index stage.

Lists the files by top folder and kind, the namespaces, duplicate MATLAB
names, private files, files that are not callable, plain folders with code
inside namespaces, the Markdown and reST files that would be sidecar docs,
and the warnings of the index (encoding, unreadable files). Changes nothing.

Usage:
    python inventory.py ROOT [--version R2024b] [--docs DOCS]
                             [--exclude PATTERN ...]

ROOT is the project root (the future ``matlab_src_code_project_root``);
``--exclude`` replaces the default exclusion patterns, as the configuration
value does; ``--docs`` is the Sphinx source folder (default ``ROOT/docs``;
its files are never sidecar docs).
"""

import argparse
import collections
import logging
import os

from sphinxcontrib.mat_types import (
    DEFAULT_EXCLUSION_PATTERNS,
    IndexSettings,
    build_index,
)

parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
parser.add_argument("root")
parser.add_argument("--version", default="R2026a")
parser.add_argument("--docs")
parser.add_argument("--exclude", nargs="*", default=list(DEFAULT_EXCLUSION_PATTERNS))
args = parser.parse_args()
root = os.path.abspath(args.root)

warnings = []


class Collect(logging.Handler):
    def emit(self, record):
        warnings.append(record.getMessage())


logger = logging.getLogger("sphinx")
logger.addHandler(Collect())
logger.setLevel(logging.WARNING)

docs = os.path.abspath(args.docs) if args.docs else os.path.join(root, "docs")
settings = IndexSettings(
    root=root,
    exclude=tuple(args.exclude),
    matlab_version=args.version,
    sidecar_suffixes=(".md", ".rst"),
    source_dir=docs,
)
index = build_index(settings)


def rel(path):
    return os.path.relpath(path, root).replace(os.sep, "/")


kinds = collections.defaultdict(collections.Counter)
namespaces = collections.Counter()
plain_in_ns = collections.Counter()
private, not_callable = [], []
for path, record in index.index.items():
    parts = rel(path).split("/")
    top = parts[0] if len(parts) > 1 else "(root)"
    kinds[top][record.get("type")] += 1
    name = record.get("matlab_name")
    if name is None:
        not_callable.append(rel(path))
    elif "." in name:
        namespaces[name.rsplit(".", 1)[0]] += 1
    if record.get("private"):
        private.append(rel(path))
    in_ns = False
    for i, part in enumerate(parts[:-1]):
        if part.startswith("+"):
            in_ns = True
        elif in_ns and not part.startswith("@") and part != "private":
            plain_in_ns["/".join(parts[: i + 1])] += 1
            break

print(f"== Sphinx source folder (--docs): {docs}")
print("== Files by top folder and kind")
for top, counts in sorted(kinds.items()):
    print(f"  {top}: {dict(counts)}")
print(f"== Namespaces and class folders ({len(namespaces)}), files in each")
for name, count in sorted(namespaces.items()):
    print(f"  {name}: {count}")
print("== Duplicate MATLAB names (exclude a copy, or keep both: listed by path)")
for name, refs in sorted(index.matlab_names.items()):
    files = sorted(ref for ref in refs if not ref.endswith("/"))
    # Namespace folders in several places merge; only files clash.
    if len(files) > 1:
        print(f"  {name}: {files}")
print(f"== Plain folders with code inside a namespace ({len(plain_in_ns)})")
print("   Their files are global names when the folder is on the MATLAB path.")
for folder, count in sorted(plain_in_ns.items()):
    print(f"  {folder}: {count}")
print(f"== private/ files ({len(private)}; left off apidoc pages by default)")
for path in private[:40]:
    print(f"  {path}")
print(f"== Not callable ({len(not_callable)})")
for path in not_callable[:40]:
    print(f"  {path}")
print(f"== Sidecar candidates, .md and .rst ({len(index.sidecars)})")
for path in sorted(index.sidecars):
    print(f"  {rel(path)}")
print(f"== Index warnings ({len(warnings)})")
for message in warnings[:80]:
    print(f"  {message}")
