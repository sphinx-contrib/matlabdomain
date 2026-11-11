"""sphinxcontrib.mat_naming
~~~~~~~~~~~~~~~~~~~~~~~~~~

MATLAB naming helpers.

This module is the single contract point for:
- MATLAB identifier validation (including namelengthmax variants)
- path references, the identity of every documented object
- stable target-id generation for cross-reference anchors
- file-to-name mapping for callable MATLAB files (``form_matlab_name``)

Reference and anchor contract (stable; changing it breaks deep links and
intersphinx):

- A path reference is the path relative to the project root, with ``/``
  separators, Unicode NFC and the file extension kept
  (``target/+package/ClassBar.m``). Folders end with ``/``; the root folder
  is ``./``. Members follow the file with ``.``
  (``target/+package/ClassBar.m.myMethod``). A block of a Simulink file
  follows it with ``/`` and its Simulink path below the file, a ``/``
  inside a block name doubled (``src/lib.slx/Group/Gain//Bias``); a
  folder whose name ends in such an extension is not a source folder.
- An object's HTML anchor is ``make_target_id(reference)``: ``mat-``
  followed by the reference, where every ASCII character other than letters,
  digits and ``- . _ ! $ & ' ( ) * + , ; = : @ /`` becomes ``~XX`` per UTF-8
  byte (uppercase hex). Non-ASCII characters are kept. ``~`` is escaped too,
  so distinct references never share an anchor.
"""

from __future__ import annotations

import os
import re
import string
from dataclasses import dataclass
from pathlib import Path

from . import mat_handlers

# Path reference of the project root folder.
ROOT_REFERENCE = "./"

_ANCHOR_SAFE = frozenset(string.ascii_letters + string.digits + "-._!$&'()*+,;=:@/")

# Oldest supported MATLAB release and the default target release.
MATLAB_VERSION_FLOOR = "R2024a"
DEFAULT_MATLAB_VERSION = "R2026a"

# Version-dependent MATLAB behavior: rule -> first release with the new behavior.
# Every row needs MATLAB evidence (see plan.md, "matlab_version").
MATLAB_VERSION_RULES = {
    # namelengthmax went from 63 to 2048 (R2025a release notes).
    "namelengthmax_2048": "R2025a",
    # Scripts/functions in a subfolder of a class folder (@C/sub/x.m) stopped
    # being callable (callable via cd in R2024a, R2024b and R2025b, not in R2026a).
    "class_subfolder_not_callable": "R2026a",
}

_MATLAB_RELEASE = re.compile(r"^R(\d{4})([ab])$")

# MATLAB language keywords. Top-level package names cannot use these.
# https://www.mathworks.com/help/releases/R2026a/matlab/ref/iskeyword.html
MATLAB_KEYWORDS = frozenset(
    {
        "break",
        "case",
        "catch",
        "classdef",
        "continue",
        "else",
        "elseif",
        "end",
        "for",
        "function",
        "global",
        "if",
        "otherwise",
        "parfor",
        "persistent",
        "return",
        "spmd",
        "switch",
        "try",
        "while",
    }
)


@dataclass(frozen=True)
class MatlabName:
    pseudo_name: str
    pseudo_package: str
    pseudo_fullname: str
    parent_folder: str
    is_private: bool = False


def _release_key(release: str) -> tuple[int, str]:
    match = _MATLAB_RELEASE.match(release) if isinstance(release, str) else None
    if match is None:
        raise ValueError(
            f"matlab_version must look like 'R2026a' or 'R2025b'; got {release!r}."
        )
    return int(match.group(1)), match.group(2)


def validate_matlab_version(matlab_version: str) -> str:
    if _release_key(matlab_version) < _release_key(MATLAB_VERSION_FLOOR):
        raise ValueError(
            f"matlab_version {matlab_version} is older than the oldest supported "
            f"release {MATLAB_VERSION_FLOOR}."
        )
    return matlab_version


def has_matlab_behavior(rule: str, matlab_version: str) -> bool:
    """Return True if ``matlab_version`` includes the behavior change ``rule``."""
    return _release_key(matlab_version) >= _release_key(MATLAB_VERSION_RULES[rule])


def default_namelengthmax(matlab_version: str) -> int:
    return 2048 if has_matlab_behavior("namelengthmax_2048", matlab_version) else 63


def _identifier_pattern(namelengthmax: int) -> re.Pattern[str]:
    return re.compile(rf"^[A-Za-z][A-Za-z0-9_]{{0,{namelengthmax - 1}}}$")


def is_valid_identifier(
    name: str,
    namelengthmax: int,
    *,
    allow_keywords: bool,
) -> bool:
    if not isinstance(name, str) or not name:
        return False
    if not _identifier_pattern(namelengthmax).match(name):
        return False
    if allow_keywords:
        return True
    return name not in MATLAB_KEYWORDS


def has_line_break(text: str) -> bool:
    """Tell whether ``text`` has a line break an ``objects.inv`` line cannot."""
    return "\n" in text or "\r" in text


def collapse_space(text: str) -> str:
    """Return ``text`` with each run of white space as one space, as a role
    writes a target (a block name with a line break has this form there).
    """
    return " ".join(text.split())


def make_target_id(reference: str) -> str:
    """Anchor for a path reference (see the module docstring)."""
    out = ["mat-"]
    for char in reference:
        if char in _ANCHOR_SAFE or ord(char) > 0x7F:
            out.append(char)
        else:
            out.extend(f"~{byte:02X}" for byte in char.encode("utf-8"))
    return "".join(out)


def parse_reference(
    reference: str, extensions=None, block_extensions=None
) -> tuple[str | None, list[str]]:
    """Split a path reference into ``(file or folder, members)``.

    The file part ends at the first registered extension (``extensions``
    defaults to the handler registry's) in the last path
    segment that is followed by ``.`` or the end:
    ``"a/Cls.m.meth"`` -> ``("a/Cls.m", ["meth"])``; folders
    (``"a/+pkg/"``) have no members. A segment that ends in an extension of
    a file with blocks (``block_extensions``, default from the registry) and
    is followed by ``/`` ends the file; the rest is one member, the block
    path: ``"a/lib.slx/G/B"`` -> ``("a/lib.slx", ["G/B"])``. Returns
    ``(None, [])`` for anything else, e.g. a MATLAB name or a folder without
    its trailing ``/``.
    """
    if extensions is None:
        extensions = mat_handlers.extensions()
    if block_extensions is None:
        block_extensions = mat_handlers.block_extensions()
    if reference.endswith("/"):
        return reference, []
    start = 0
    while (slash := reference.find("/", start)) >= 0:
        segment = reference[reference.rfind("/", 0, slash) + 1 : slash]
        if is_block_container(segment, block_extensions):
            return reference[:slash], [reference[slash + 1 :]]
        start = slash + 1
    head, sep, last = reference.rpartition("/")
    for i, char in enumerate(last):
        if char != "." or i == 0:
            continue
        for ext in extensions:
            end = i + len(ext)
            if last.startswith(ext, i) and (end == len(last) or last[end] == "."):
                members = last[end + 1 :].split(".") if end < len(last) else []
                if not all(members):
                    return None, []
                return head + sep + last[:end], members
    return None, []


def is_block_container(name: str, block_extensions=None) -> bool:
    """Return True if the file or folder name ``name`` ends in the extension
    of a file with blocks (``block_extensions``, default from the registry).
    """
    if block_extensions is None:
        block_extensions = mat_handlers.block_extensions()
    return any(len(name) > len(ext) and name.endswith(ext) for ext in block_extensions)


def split_folder(folder: str) -> list[str]:
    """Split a folder reference: ``"a/b/"`` -> ``["a", "b"]``, ``"./"`` -> ``[]``."""
    return [] if folder == ROOT_REFERENCE else folder.rstrip("/").split("/")


def join_folder(parts) -> str:
    """Join folder names into a folder reference (the inverse of ``split_folder``)."""
    return "/".join(parts) + "/" if parts else ROOT_REFERENCE


def join_reference(folder: str, relative: str) -> str:
    """Return the reference of ``relative`` below the folder reference ``folder``."""
    return relative if folder == ROOT_REFERENCE else f"{folder}{relative}"


def folder_of(reference: str) -> str:
    """Folder reference of a file or member reference; folders map to themselves."""
    file, _ = parse_reference(reference)
    path = reference if file is None else file
    if path.endswith("/"):
        return path
    head = path.rpartition("/")[0]
    return f"{head}/" if head else ROOT_REFERENCE


def is_private_reference(reference: str) -> bool:
    """Return True if the object lives below a ``private/`` folder."""
    return "private" in folder_of(reference).split("/")


def split_display(display: str) -> tuple[str, str]:
    """Split a display name into (qualifier, last part) for signatures.

    MATLAB names split at the last ``.``; path references at the last ``/``.
    """
    sep = "/" if "/" in display.rstrip("/") else "."
    head, found, _ = display.rstrip("/").rpartition(sep)
    if not found or not head:
        return "", display
    return head + sep, display[len(head) + 1 :]


def folder_namespace(
    folder: str, namelengthmax: int, matlab_version: str = DEFAULT_MATLAB_VERSION
) -> str | None:
    """MATLAB namespace name of a ``+`` folder, or None for any other folder."""
    parts = _split_folder(folder)
    if not parts or not parts[-1].startswith("+"):
        return None
    location = _location(parts, namelengthmax, matlab_version)
    return location[1] if location and location[0] == "package" else None


def canonical_name(name: MatlabName) -> str:
    """Documentation name of a file.

    ``pseudo_fullname``, except that class-folder methods are qualified by
    their class (``pkg.C.helper``, not the callable ``helper``).
    """
    package, fullname = name.pseudo_package, name.pseudo_fullname
    if not package or fullname == package or fullname.startswith(f"{package}."):
        return fullname
    return f"{package}.{name.pseudo_name}"


def _split_folder(folder: str) -> list[str]:
    return list(Path(os.path.normpath(str(folder))).parts)


def _join_parts(parts: list[str]) -> str:
    if not parts:
        return ""
    out = parts[0]
    for part in parts[1:]:
        out = os.path.join(out, part)
    return out


def _package_chain(
    folder_parts: list[str], namelengthmax: int
) -> tuple[list[str], int] | None:
    """Collect trailing '+pkg' folders. Returns (segments, index below chain)."""
    segments: list[str] = []
    idx = len(folder_parts) - 1
    while idx >= 0 and folder_parts[idx].startswith("+"):
        segments.append(folder_parts[idx][1:])
        idx -= 1
    segments.reverse()
    if not segments:
        return None
    if not is_valid_identifier(segments[0], namelengthmax, allow_keywords=False):
        return None
    if not all(
        is_valid_identifier(seg, namelengthmax, allow_keywords=True)
        for seg in segments[1:]
    ):
        return None
    return segments, idx


def _location(
    folder_parts: list[str],
    namelengthmax: int,
    matlab_version: str = DEFAULT_MATLAB_VERSION,
) -> tuple[str, str, str] | None:
    """Classify a folder as (kind, qualified prefix, parent folder).

    kind is "plain", "package", "class" or "class_subfolder"; the prefix is the
    package name or the qualified class name. Returns None for folders that hold
    no callable files (invalid packages, subfolders of class folders on
    R2026a+, ...).
    """
    last = folder_parts[-1]
    folder = _join_parts(folder_parts)

    if last.startswith("@"):
        class_name = last[1:]
        if not is_valid_identifier(class_name, namelengthmax, allow_keywords=False):
            return None
        chain = _package_chain(folder_parts[:-1], namelengthmax)
        if chain is None:
            # A class folder directly under an invalid package is not callable.
            if len(folder_parts) >= 2 and folder_parts[-2].startswith("+"):
                return None
            if any(part.startswith("@") for part in folder_parts[:-1]):
                return None
            return "class", class_name, folder
        segments, idx = chain
        if any(part.startswith("@") for part in folder_parts[: idx + 1]):
            return None
        return (
            "class",
            ".".join([*segments, class_name]),
            _join_parts(folder_parts[: idx + 1]),
        )

    if last.startswith("+"):
        chain = _package_chain(folder_parts, namelengthmax)
        if chain is None:
            return None
        segments, idx = chain
        # Packages below a class folder are not callable.
        if any(part.startswith("@") for part in folder_parts[: idx + 1]):
            return None
        return "package", ".".join(segments), _join_parts(folder_parts[: idx + 1])

    # Plain folder below a class folder: scripts/functions were callable before
    # R2026a; classes never were.
    if any(part.startswith("@") for part in folder_parts[:-1]):
        if has_matlab_behavior("class_subfolder_not_callable", matlab_version):
            return None
        return "class_subfolder", "", folder
    return "plain", "", folder


def _private_name(
    folder_parts: list[str], stem: str, is_class: bool, namelengthmax: int
) -> MatlabName | None:
    if is_class or not is_valid_identifier(stem, namelengthmax, allow_keywords=False):
        return None
    parent_parts = folder_parts[:-1]
    if not parent_parts or parent_parts[-1] == "private":
        return None
    # Default (R2026a) rules on purpose: private folders below a class subfolder
    # were never verified as callable in older releases.
    if _location(parent_parts, namelengthmax) is None:
        return None
    return MatlabName(
        pseudo_name=stem,
        pseudo_package="",
        pseudo_fullname=stem,
        parent_folder=_join_parts(folder_parts),
        is_private=True,
    )


def _name_problem(name: str, namelengthmax: int) -> str:
    """Why the invalid ``name`` is no MATLAB identifier."""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
        return "is not a valid MATLAB identifier"
    if len(name) > namelengthmax:
        return f"is longer than {namelengthmax} characters"
    return "is a MATLAB keyword"


def not_callable_reason(
    folder: str,
    filename: str,
    is_class: bool,
    namelengthmax: int,
    matlab_version: str = DEFAULT_MATLAB_VERSION,
) -> str:
    """Says why ``form_matlab_name`` returns None for a file outside ``private/``."""
    parts = _split_folder(folder)
    in_class = False
    for i, part in enumerate(parts):
        if part[:1] in ("+", "@"):
            kind = "namespace" if part[0] == "+" else "class"
            if in_class:
                return f"{kind} folder {part} is inside a class folder"
            first = part[0] == "@" or i == 0 or not parts[i - 1].startswith("+")
            if not is_valid_identifier(
                part[1:], namelengthmax, allow_keywords=not first
            ):
                problem = _name_problem(part[1:], namelengthmax)
                return f"folder name {part[1:]!r} {problem}"
            in_class = part[0] == "@"
        elif in_class:
            if is_class:
                return "classes in subfolders of a class folder are not callable"
            if has_matlab_behavior("class_subfolder_not_callable", matlab_version):
                return (
                    "files in subfolders of a class folder are not callable since "
                    + MATLAB_VERSION_RULES["class_subfolder_not_callable"]
                )
    stem = Path(filename).stem
    last = parts[-1] if parts else ""
    if is_class and last.startswith("@") and stem != last[1:]:
        return f"a class in {last} must be named {last[1:]}"
    if not is_valid_identifier(stem, namelengthmax, allow_keywords=last[:1] == "@"):
        return f"its name {stem!r} {_name_problem(stem, namelengthmax)}"
    return "MATLAB cannot form a name for it"


def form_matlab_name(
    folder: str,
    filename: str,
    is_class: bool,
    namelengthmax: int,
    matlab_version: str = DEFAULT_MATLAB_VERSION,
) -> MatlabName | None:
    """Forms the callable MATLAB name for a single file.

    Pure string/path function; returns None for non-callable/invalid entries.
    ``matlab_version`` selects version-dependent rules (MATLAB_VERSION_RULES).
    """
    validate_matlab_version(matlab_version)

    folder_parts = _split_folder(folder)
    if not folder_parts:
        return None

    stem = Path(filename).stem
    if folder_parts[-1] == "private":
        return _private_name(folder_parts, stem, is_class, namelengthmax)

    location = _location(folder_parts, namelengthmax, matlab_version)
    if location is None:
        return None
    kind, prefix, parent_folder = location

    if kind == "class":
        class_name = folder_parts[-1][1:]
        if is_class:
            if stem != class_name:
                return None
            return MatlabName(stem, prefix, prefix, parent_folder)
        if not is_valid_identifier(stem, namelengthmax, allow_keywords=True):
            return None
        return MatlabName(stem, prefix, stem, parent_folder)

    if not is_valid_identifier(stem, namelengthmax, allow_keywords=False):
        return None

    if kind == "class_subfolder":
        if is_class:
            return None
        return MatlabName(stem, "", stem, parent_folder)
    if is_class:
        qualified = f"{prefix}.{stem}" if prefix else stem
        return MatlabName(stem, qualified, qualified, parent_folder)
    if kind == "package":
        return MatlabName(stem, prefix, f"{prefix}.{stem}", parent_folder)
    return MatlabName(stem, "", stem, parent_folder)


def _model_folder_problem(parts: list[str]) -> str | None:
    # Simulink:Commands:UnsuitableModelFileLocation (R2024a-R2026b) checks the
    # file's own folder only: private/sub/ and @C/sub/ load.
    last = parts[-1] if parts else ""
    if last == "private" or last.startswith("@"):
        return "Simulink cannot load models in private or class folders"
    if "*" in last:
        return "Simulink cannot load models in folders with * in their names"
    return None


def form_model_name(
    folder: str,
    filename: str,
    namelengthmax: int,
    matlab_version: str = DEFAULT_MATLAB_VERSION,
) -> MatlabName | None:
    """Form the name that ``load_system`` takes for a Simulink file (model,
    library or subsystem file), or None.

    Probed in R2024a-R2026b: the name is the file name, a MATLAB identifier
    that is no keyword and at most ``namelengthmax`` long, in the global
    namespace only: Simulink cannot run or reference a model in a namespace
    folder by name (R2026a and R2026b load ``pkg.model``, but ``sim`` and
    Model blocks refuse it). Nothing directly in ``private/`` or a class
    folder loads, even by path; their subfolders are plain folders in every
    release (``.m`` files in ``@C/sub/`` are not callable from R2026a,
    models there still load).
    """
    validate_matlab_version(matlab_version)
    parts = _split_folder(folder)
    if not parts or _model_folder_problem(parts) is not None:
        return None
    stem = Path(filename).stem
    if not is_valid_identifier(stem, namelengthmax, allow_keywords=False):
        return None
    if parts[-1].startswith("+"):
        # A release that runs namespace models would name them pkg.model here.
        return None
    return MatlabName(stem, "", stem, _join_parts(parts))


def model_not_callable_reason(
    folder: str,
    filename: str,
    namelengthmax: int,
) -> str:
    """Says why ``form_model_name`` returns None."""
    parts = _split_folder(folder)
    problem = _model_folder_problem(parts)
    if problem is not None:
        return problem
    stem = Path(filename).stem
    if not is_valid_identifier(stem, namelengthmax, allow_keywords=False):
        return f"its name {stem!r} {_name_problem(stem, namelengthmax)}"
    return (
        "in a namespace folder, Simulink cannot reference it by name and loads "
        "it reliably only by its full path; keep Simulink files in the global "
        "namespace"
    )
