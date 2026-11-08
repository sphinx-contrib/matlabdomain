"""sphinxcontrib.matlab_apidoc._names.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Output file names of ``scmd apidoc`` (plan.md Section 2.8). Pure
functions of path references: the same names on every OS.

- The output tree mirrors the folder tree: the page of folder ``a/+p/`` is
  ``a/+p/index``, the root folder's page is the toc file, and with
  ``separate`` the page of ``a/+p/Cls.m`` is ``a/+p/Cls.m``. A block
  reference keeps its block path in the file's name (``a/lib.slx/G/B`` ->
  ``a/lib.slx~2FG~2FB``), as a member does (``a/Cls.m.meth``).
- Each path segment keeps ``A-Z a-z 0-9 _ . + @ -``; every other character
  becomes ``~XX`` per UTF-8 byte (uppercase hex). ``~`` is escaped too, so
  the mapping is injective.
- Windows device names (``CON``, ``AUX``, ``COM1``, ... in any case, before
  the first ``.``) get their first character escaped; a trailing ``.`` is
  escaped. A folder's leading ``_`` is escaped (``_util/`` -> ``~5Futil/``):
  output folders never start with ``_``, which Sphinx and static site hosts
  treat as their own.
- Siblings whose output names differ only by case get the uppercase letters
  of all of them escaped (``Utils`` -> ``~55tils``).
- A folder named exactly like a sibling page file gets its last dot
  escaped (``guide-md.rst/`` -> ``guide-md~2Erst/``); the page keeps its
  name. Names that differ only by case follow the rule above.
"""

from __future__ import annotations

import string

from ..mat_naming import ROOT_REFERENCE, parse_reference

SAFE_CHARS = frozenset(string.ascii_letters + string.digits + "_.+@-")
DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"{name}{i}" for name in ("COM", "LPT") for i in range(10)}
)
#: longest path Windows accepts without the long-path setting (MAX_PATH - 1)
WINDOWS_MAX_PATH = 259
_DIR, _FILE = "dir", "file"


def _escape_char(char: str) -> str:
    return "".join(f"~{byte:02X}" for byte in char.encode("utf-8"))


def escape_segment(segment: str) -> str:
    """Return the output name of one path segment (a folder or file name)."""
    out = "".join(c if c in SAFE_CHARS else _escape_char(c) for c in segment)
    if out.split(".", 1)[0].upper() in DEVICE_NAMES:
        out = _escape_char(out[0]) + out[1:]
    if out.endswith("."):
        out = out[:-1] + _escape_char(".")
    return out


def escape_upper(name: str) -> str:
    """Escape the uppercase ASCII letters of an output name."""
    return "".join(_escape_char(c) if c in string.ascii_uppercase else c for c in name)


def too_long(path: str, limit: int = WINDOWS_MAX_PATH) -> bool:
    """Return True if ``path`` is longer than Windows accepts by default."""
    return len(path) > limit


def _split(reference: str) -> tuple[tuple[str, ...], str | None]:
    """``(folders, file)`` of a folder (``file`` None) or file reference."""
    if reference == ROOT_REFERENCE:
        return (), None
    parts = reference.rstrip("/").split("/")
    if reference.endswith("/"):
        return tuple(parts), None
    file, _ = parse_reference(reference)
    if file is not None and reference.startswith(f"{file}/"):
        head, sep, _ = file.rpartition("/")
        return tuple(head.split("/")) if head else (), reference[len(head + sep) :]
    return tuple(parts[:-1]), parts[-1]


def docnames(references, suffix="rst", tocfile="index"):
    """Return ``(names, collisions)`` for the pages of ``references``.

    A folder reference (``a/+p/``, ``./``) stands for its folder page, a file
    reference for its object page. ``names`` maps each reference to its
    docname (``/``-separated, relative to the output folder, without the
    suffix). ``collisions`` lists ``(folder, names)``, sorted: the sibling
    names in an output folder (``""`` at the top; folders end with ``/``)
    whose output paths were equal or differed only by case.
    """
    split = {ref: _split(ref) for ref in references}
    children = {}
    for folders, file in split.values():
        for i, name in enumerate(folders):
            children.setdefault(folders[:i], set()).add((_DIR, name))
        if file is not None:
            children.setdefault(folders, set()).add((_FILE, file))

    names, groups = {}, []
    for parent, kids in children.items():
        page = f"{tocfile if not parent else 'index'}.{suffix}"
        files: dict[str, list[str]] = {}
        for kind, raw in kids:
            if kind == _FILE:
                full = f"{escape_segment(raw)}.{suffix}"
                files.setdefault(full, []).append(raw)
        by_name: dict[str, list[tuple[str, str] | None]] = {page.lower(): [None]}
        for kind, raw in sorted(kids):
            out = escape_segment(raw)
            if kind == _DIR and out.startswith("_"):
                out = _escape_char("_") + out[1:]
            # Exact only: case-only clashes keep their earlier names.
            if kind == _DIR and out in files:
                clash = [(_FILE, file) for file in files[out]]
                groups.append((parent, [*clash, (kind, raw)]))
                base, _, extension = out.rpartition(".")
                out = f"{base}{_escape_char('.')}{extension}"
            names[parent, kind, raw] = out
            full = out if kind == _DIR else f"{out}.{suffix}"
            by_name.setdefault(full.lower(), []).append((kind, raw))
        for group in by_name.values():
            members = [m for m in group if m is not None]
            if len(group) > 1 and members:
                for kind, raw in members:
                    out = escape_upper(names[parent, kind, raw])
                    full = out if kind == _DIR else f"{out}.{suffix}"
                    if full.lower() == page.lower():
                        # all lowercase, like the page itself
                        out = _escape_char(out[0]) + out[1:]
                    names[parent, kind, raw] = out
                groups.append((parent, members))

    def path(folders):
        return [names[folders[:i], _DIR, name] for i, name in enumerate(folders)]

    collisions = sorted(
        (
            "/".join(path(parent)),
            sorted(raw + ("/" if kind == _DIR else "") for kind, raw in members),
        )
        for parent, members in groups
    )
    out = {}
    for ref, (folders, file) in split.items():
        if file is None:
            leaf = tocfile if not folders else "index"
        else:
            leaf = names[folders, _FILE, file]
        out[ref] = "/".join([*path(folders), leaf])
    return out, collisions
