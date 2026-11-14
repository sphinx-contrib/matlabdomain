"""Count the objects of a Sphinx build by kind, or compare a 0.x and a 1.0 build.

Usage:
  python compare_inventories.py NEW_INV
  python compare_inventories.py OLD_INV NEW_INV --root ROOT [--show N]
  python compare_inventories.py NEW_INV_A NEW_INV_B [--show N]

An INV is the ``objects.inv`` of an HTML build. With two and ``--root``,
the 0.x dotted names in OLD_INV are mapped to path references through ROOT
(the MATLAB project root; 0.x modules to 1.0 folders, the module index label
to the folder index). Without ``--root``, two 1.0 builds are compared as
they are. The objects only one side has are listed by kind.
Needs Sphinx (run it in either environment).
"""

import argparse
from collections import Counter
from pathlib import Path
from typing import Any, cast

from sphinx.util.inventory import InventoryFile


def load(path):
    """Return role -> set of object names of the ``objects.inv`` at ``path``."""
    with open(path, "rb") as f:
        inv = InventoryFile.load(cast(Any, f), "", lambda _base, uri: uri)
    inv = getattr(inv, "data", inv)
    return {role: set(entries) for role, entries in inv.items()}


def to_path_ref(root, dotted):
    """Path reference of a 0.x dotted name, or None (see rewrite_pages.py)."""
    cur, parts = root, []
    segs = dotted.split(".")
    for i, seg in enumerate(segs):
        for ext in (".m", ".mlapp"):
            if (cur / f"{seg}{ext}").is_file():
                ref = "/".join([*parts, f"{seg}{ext}"])
                return ".".join([ref, *segs[i + 1 :]]) if segs[i + 1 :] else ref
        for folder in (seg, f"+{seg}", f"@{seg}"):
            if (cur / folder).is_dir():
                cur, parts = cur / folder, [*parts, folder]
                break
        else:
            return None
    return "/".join(parts) + "/"


def map_old_names(old, root):
    """Map the 0.x dotted names of ``old`` (role -> names) to path references
    through ``root``, in place; return the names not found below it.
    """
    unmapped = []
    for role, names in list(old.items()):
        if role == "mat:module":
            # 0.x modules are 1.0 folders; class folders and the root get no object.
            folders = old.setdefault("mat:folder", set())
            for name in names:
                ref = "./" if name == "." else to_path_ref(root, name)
                if ref is None or not ref.endswith("/"):
                    unmapped.append(f"{role} {name}")
                elif ref != "./" and not ref.rstrip("/").split("/")[-1].startswith("@"):
                    folders.add(ref)
            del old[role]
        elif role.startswith("mat:"):
            mapped = set()
            for name in names:
                ref = to_path_ref(root, name)
                if ref is None:
                    unmapped.append(f"{role} {name}")
                mapped.add(ref or name)
            old[role] = mapped
    return unmapped


def print_comparison(old, new, show):
    """Print the object counts of ``old`` and ``new`` by kind, the objects only
    one side has (``show`` per kind and side) and the objects whose kind changed.
    """
    print(f"{'kind':20} {'old':>6} {'new':>6} {'old only':>9} {'new only':>9}")
    details = []
    for role in sorted(set(old) | set(new)):
        o, n = old.get(role, set()), new.get(role, set())
        print(f"{role:20} {len(o):6} {len(n):6} {len(o - n):9} {len(n - o):9}")
        for side, names in (("old only", o - n), ("new only", n - o)):
            if names:
                shown = sorted(names)[:show]
                more = (
                    f" (+{len(names) - len(shown)} more)"
                    if len(names) > len(shown)
                    else ""
                )
                details.append(f"\n{role} {side}{more}:\n  " + "\n  ".join(shown))
    where_old = {x: r for r, xs in old.items() for x in xs}
    where_new = {x: r for r, xs in new.items() for x in xs}
    moved = Counter(
        f"{where_old[x]} -> {where_new[x]}"
        for x in where_old.keys() & where_new.keys()
        if where_old[x] != where_new[x]
    )
    if moved:
        print("\nkind changed:", dict(moved))
    print("".join(details))


def main():
    """Print the object counts of one inventory, or compare two (see the module
    docstring).
    """
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("inventories", nargs="+", type=Path)
    parser.add_argument(
        "--root", type=Path, help="the MATLAB project root (to map 0.x names)"
    )
    parser.add_argument(
        "--show",
        type=int,
        default=10,
        help="objects to list per kind and side (default 10)",
    )
    args = parser.parse_args()
    first, *rest = args.inventories
    if not rest:
        for role, names in sorted(load(first).items()):
            print(f"{role:20} {len(names):6}")
        return
    if len(rest) > 1:
        parser.error("give one inventory, or two to compare")
    old, new = load(first), load(rest[0])
    unmapped = map_old_names(old, args.root.resolve()) if args.root else []
    if "mat-modindex" in old.get("std:label", set()):
        old["std:label"] = (old["std:label"] - {"mat-modindex"}) | {"mat-folderindex"}
    print_comparison(old, new, args.show)
    if unmapped:
        print(
            f"\n0.x names not found below the root ({len(unmapped)}):\n  "
            + "\n  ".join(unmapped[: args.show])
        )


if __name__ == "__main__":
    main()
