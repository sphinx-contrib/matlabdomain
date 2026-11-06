"""Rewrite 0.x matlabdomain pages to 1.0 syntax, or list what needs a hand fix.

Usage: python rewrite_pages.py --root ROOT [--write] PATH...

ROOT is the MATLAB project root (the folder ``matlab_src_dir`` pointed at).
PATH is a page (``.rst``, ``.md``) or a folder searched for them. Without
``--write`` it prints a diff and changes nothing.

It rewrites module directives and roles to their folder forms, dotted names
in auto directives and roles to path references (when they name a file
below ROOT), ``modindex`` references to ``mat-folderindex`` and
``:friend-members:`` to ``:access-list-members:``, and removes
``:special-members:`` and ``:inherited-members:``. Everything it cannot
rewrite is listed under "check by hand". Help text in ``.m`` files is not
changed.
"""

import argparse
import difflib
import re
import sys
from collections import Counter
from pathlib import Path

AUTO = (
    r"auto(?:class|function|method|script|application|attribute|property|staticmethod)"
)
MODULE = r"(?:auto|current)?module"
# The prefix allows Markdown block quotes ("> ") around eval-rst blocks.
RST_DIRECTIVE = re.compile(rf"^([\s>]*)\.\. (mat:)?({AUTO}|{MODULE})::[ \t]*(\S*)(.*)$")
MD_DIRECTIVE = re.compile(
    rf"^([\s>]*)```\{{(mat:)?({AUTO}|{MODULE})\}}[ \t]*(\S*)(.*)$"
)
REMOVED_OPTION = re.compile(r"^[\s>]*:(special-members|inherited-members):")
FRIEND_OPTION = re.compile(r"^([\s>]*):friend-members:")
MODINDEX = re.compile(r"(:ref:`(?:[^`<]*<)?)modindex(>?`)")
REMOVED_DIRECTIVE = re.compile(
    r"^[\s>]*(?:\.\. |```\{)(?:mat:)?"
    r"(?:(?:auto)?(?:exception|decorator|decoratormethod)|classmethod)\b"
)
ROLE = re.compile(
    r":(mat:)?(class|func|meth|attr|mod|obj|script|app|prop|exc):`([^`]+)`"
)
MD_ROLE = re.compile(
    r"\{(mat:)?(class|func|meth|attr|mod|obj|script|app|prop|exc)\}`([^`]+)`"
)


def walk(root, base, segs):
    """Path reference for dotted segments below ``root/base``, or None."""
    cur = root.joinpath(*base)
    parts = list(base)
    for i, seg in enumerate(segs):
        for ext in (".m", ".mlapp"):
            if (cur / f"{seg}{ext}").is_file():
                ref = "/".join([*parts, f"{seg}{ext}"])
                rest = segs[i + 1 :]
                return ".".join([ref, *rest]) if rest else ref
        for folder in (seg, f"+{seg}", f"@{seg}"):
            if (cur / folder).is_dir():
                cur = cur / folder
                parts.append(folder)
                break
        else:
            return None
    return "/".join(parts) + "/" if parts else "./"


def resolve(root, current, name):
    """Path reference for a 0.x name, relative to the current module first."""
    if name in (".", ""):
        return "./"
    segs = name.rstrip("()").split(".")
    if current:
        found = walk(root, current, segs)
        if found:
            return found
    return walk(root, [], segs)


def folder_parts(ref):
    return [p for p in ref.rstrip("/").split("/") if p not in ("", ".")]


def rewrite_target(root, current, text):
    """Rewrite a role target (``~x``, ``title <x>``); None if unchanged."""
    m = re.fullmatch(r"(.*<)([^<>]+)(>)", text)
    head, target, tail = (m[1], m[2], m[3]) if m else ("", text, "")
    tilde = "~" if target.startswith("~") else ""
    target = target.lstrip("~")
    if target.startswith(".") or "/" in target:
        return None
    ref = resolve(root, current, target)
    if ref is None or ref == target:
        return None
    return f"{head}{tilde}{ref}{tail}"


def rewrite(root, text, notes, where):
    out = []
    current = []
    for lineno, line in enumerate(text.splitlines(keepends=True), 1):
        body = line.rstrip("\r\n")
        eol = line[len(body) :]
        if REMOVED_OPTION.match(body):
            option = body.strip(" \t>")
            notes.append(f"{where}:{lineno}: removed {option}")
            continue
        if REMOVED_DIRECTIVE.match(body):
            notes.append(
                f"{where}:{lineno}: check by hand (removed directive): {body.strip()}"
            )
        body = FRIEND_OPTION.sub(r"\1:access-list-members:", body)
        body = MODINDEX.sub(r"\1mat-folderindex\2", body)
        m = RST_DIRECTIVE.match(body) or MD_DIRECTIVE.match(body)
        if m:
            indent, prefix, kind, name, rest = m.groups()
            prefix = prefix or ""
            md = body.lstrip(" \t>").startswith("```")
            # 0.x module names start at the root; other names may be relative.
            ref = resolve(root, [] if kind.endswith("module") else current, name)
            if kind.endswith("module"):
                if ref is None or not ref.endswith("/"):
                    notes.append(
                        f"{where}:{lineno}: check by hand (folder not found): "
                        f"{body.strip()}"
                    )
                else:
                    current = folder_parts(ref)
                    class_folder = bool(current) and current[-1].startswith("@")
                    if ref == "./" or class_folder or kind == "currentmodule":
                        new = "mat:currentfolder"
                        if kind == "automodule":
                            notes.append(
                                f"{where}:{lineno}: check by hand (automodule of a "
                                "class folder or the root; document its class or "
                                f"files): {body.strip()}"
                            )
                    else:
                        new = "mat:autofolder" if kind == "automodule" else "mat:folder"
                    target = "." if ref == "./" else ref
                    body = (
                        f"{indent}```{{{new}}} {target}{rest}"
                        if md
                        else f"{indent}.. {new}:: {target}{rest}"
                    )
            elif ref is not None and ref != name and not ref.endswith("/"):
                directive = f"{{{prefix}{kind}}}" if md else f"{prefix}{kind}::"
                body = (
                    f"{indent}```{directive} {ref}{rest}"
                    if md
                    else f"{indent}.. {directive} {ref}{rest}"
                )
            elif ref is None and "." in name:
                notes.append(
                    f"{where}:{lineno}: check by hand (not found below the root): "
                    f"{body.strip()}"
                )
            elif ref is None and name:
                notes.append(
                    f"{where}:{lineno}: check by hand (kept as a MATLAB name): "
                    f"{body.strip()}"
                )

        def role(m, md_role=False, lineno=lineno, current=current):
            prefix, kind, target = m.groups()
            prefix = prefix or ""

            def form(kind, target):
                return (
                    f"{{{prefix}{kind}}}`{target}`"
                    if md_role
                    else f":{prefix}{kind}:`{target}`"
                )

            if kind == "mod":
                ref = resolve(root, [], target.lstrip("~"))
                if ref and ref.endswith("/"):
                    prefix = "mat:"
                    return form("folder", ref)
                notes.append(f"{where}:{lineno}: check by hand (module role): {m[0]}")
                return m[0]
            if kind == "exc":
                notes.append(
                    f"{where}:{lineno}: check by hand (use :mat:class:): {m[0]}"
                )
            new = rewrite_target(root, current, target)
            return form(kind, new) if new else m[0]

        body = ROLE.sub(role, body)
        body = MD_ROLE.sub(lambda m: role(m, md_role=True), body)
        out.append(body + eol)
    return "".join(out)


def pages(paths):
    for path in paths:
        if path.is_dir():
            yield from sorted(
                p
                for p in path.rglob("*")
                if p.suffix in (".rst", ".md") and "_build" not in p.parts
            )
        else:
            yield path


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--root", required=True, type=Path, help="the MATLAB project root"
    )
    parser.add_argument(
        "--write", action="store_true", help="change the files (default: print a diff)"
    )
    parser.add_argument(
        "--summary", action="store_true", help="no diff: only the pages and the notes"
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    notes, changed = [], []
    for page in pages(args.paths):
        raw = page.read_bytes()
        text = raw.decode("utf-8")
        new = rewrite(root, text, notes, page)
        if new == text:
            continue
        changed.append(page)
        if args.write:
            page.write_bytes(new.encode("utf-8"))
        elif not args.summary:
            # Without \r, so CRLF pages do not print double-spaced on Windows.
            old_lines = text.replace("\r\n", "\n").splitlines(True)
            new_lines = new.replace("\r\n", "\n").splitlines(True)
            sys.stdout.writelines(
                difflib.unified_diff(old_lines, new_lines, str(page), str(page))
            )
    if args.summary:
        print("\n".join(str(p) for p in changed))
    print(f"\n{len(changed)} page(s) {'changed' if args.write else 'would change'}")
    removed = Counter(n.split(": removed ", 1)[1] for n in notes if ": removed " in n)
    for option, count in sorted(removed.items()):
        print(f"removed {option} {count} time(s)")
    by_hand = [n for n in notes if ": removed " not in n]
    if by_hand:
        print("\nCheck by hand:")
        print("\n".join(by_hand))


if __name__ == "__main__":
    main()
