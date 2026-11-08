"""sphinxcontrib.matlab_quickstart._detect.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The project facts ``scmd quickstart`` reads (plan.md Section
2.13): uv, the MATLAB release, the git submodules, the MATLAB project path,
sidecar doc candidates, how matlabdomain itself is installed, and, from the
index, the inventory, the help headings and the copyright blocks that run
into help. Nothing here writes.
"""

from __future__ import annotations

import collections
import configparser
import importlib.util
import json
import os
import re
import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from .. import mat_naming
from ..mat_classify import UNKNOWN, is_hidden
from ..mat_handlers import extensions, handler_by_extension
from ..mat_simulink import KINDS

DISTRIBUTION = "sphinxcontrib-matlabdomain"
#: a heading used in at least this many files becomes a napoleon section
SECTION_FILES = 10
#: napoleon's own sections (``GoogleDocstring._sections``): no entry needed
NAPOLEON_SECTIONS = frozenset(
    {
        "args", "arguments", "attention", "attributes", "caution", "danger",
        "error", "example", "examples", "hint", "important", "keyword args",
        "keyword arguments", "methods", "note", "notes", "other parameters",
        "parameters", "receive", "receives", "return", "returns", "raise",
        "raises", "references", "see also", "tip", "todo", "warning",
        "warnings", "warn", "warns", "yield", "yields",
    }
)  # fmt: skip
#: headings whose ``name - text`` items are parameters
_PARAMS = re.compile(
    r"(inputs?|outputs?|(input|output) arguments?|name value( pairs| arguments)?"
    r"|options?)"
)
_RELEASE = re.compile(r"\bR(20\d\d)([ab])\b", re.IGNORECASE)
#: files that name the MATLAB release the project targets
_VERSION_FILES = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
    ".circleci/config.yml",
    ".travis.yml",
    "azure-pipelines.yml",
    "Jenkinsfile",
    "matlab.toml",
)
_COMMENT = re.compile(r"^\s*%(?![{}])")
_DECLARATION = re.compile(r"^\s*(function|classdef)\b")
_HEADING = re.compile(r"^\s*%+\s*([A-Za-z][A-Za-z0-9 /&()_-]{0,40}?)\s*:{1,2}\s*$")
#: napoleon matches only headings of letters, digits, ``_`` and spaces
_MATCHABLE = re.compile(r"^[\w ]+$")
_LEGAL = re.compile(r"^\s*%.*\b(copyright|licen[cs]e|restrictions)\b", re.IGNORECASE)
_INFO = re.compile(r"<Info\b([^>]*)>")
_ATTRIBUTE = re.compile(r'(\w+)="([^"]*)"')


@dataclass(frozen=True)
class Install:
    """How matlabdomain is installed (PEP 610 ``direct_url.json``).

    ``kind`` is ``"vcs"`` (a git URL and commit), ``"editable"`` (a folder,
    in ``requirement``), ``"url"`` (an archive or a folder) or
    ``"version"`` (from an index).
    """

    kind: str
    requirement: str


def _distribution():
    dists = list(metadata.distributions(name=DISTRIBUTION))
    # A checkout's egg-info, found through the working folder, has no INSTALLER.
    installed = [d for d in dists if d.read_text("INSTALLER") is not None]
    return (installed or dists or [None])[0]


def matlabdomain_install(dist=None):
    """Return the ``Install`` of matlabdomain (``dist``: the distribution)."""
    dist = dist or _distribution()
    if dist is None:
        return Install("version", DISTRIBUTION)
    text = dist.read_text("direct_url.json")
    if text is None:
        # A requirement cannot name a local version (+g<sha>).
        return Install("version", f"{DISTRIBUTION}>={dist.version.split('+')[0]}")
    info = json.loads(text)
    url = info["url"]
    if "vcs_info" in info:
        vcs = info["vcs_info"]
        return Install("vcs", f"{DISTRIBUTION} @ {vcs['vcs']}+{url}@{vcs['commit_id']}")
    if info.get("dir_info", {}).get("editable"):
        return Install("editable", url2pathname(urlparse(url).path))
    return Install("url", f"{DISTRIBUTION} @ {url}")


def read_pyproject(root):
    """Return the parsed ``pyproject.toml`` of ``root``, or None."""
    try:
        with open(os.path.join(root, "pyproject.toml"), "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def uv_project(root):
    """Return why ``root`` is a uv project (``uv.lock``, ``[tool.uv]``), or None."""
    if os.path.isfile(os.path.join(root, "uv.lock")):
        return "uv.lock"
    if "uv" in (read_pyproject(root) or {}).get("tool", {}):
        return "[tool.uv]"
    return None


def _version_files(root):
    root = Path(root)
    for pattern in _VERSION_FILES:
        yield from sorted(root.glob(pattern))
    yield from sorted(p for p in root.iterdir() if p.name.lower().startswith("readme"))


def matlab_versions(root):
    """Return ``{release: {file: count}}`` of the releases (``R2024b``) named in the
    CI files, ``matlab.toml`` and the README of ``root``.
    """
    found = collections.defaultdict(collections.Counter)
    for path in _version_files(root):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for year, half in _RELEASE.findall(text):
            found[f"R{year}{half.lower()}"][path.relative_to(root).as_posix()] += 1
    return dict(found)


def most_frequent_release(found):
    """Return the release named most often (the newest of a tie), or None."""
    if not found:
        return None
    return max(found, key=lambda r: (sum(found[r].values()), r))


def matlab_version_default(found):
    """Return ``(version, note)``: the release to use, and why when it is not the
    detected one.
    """
    release = most_frequent_release(found)
    floor = mat_naming.MATLAB_VERSION_FLOOR
    if release is None:
        return mat_naming.DEFAULT_MATLAB_VERSION, "the default; none is named"
    try:
        mat_naming.validate_matlab_version(release)
    except ValueError:
        return floor, f"the oldest supported release; {release} is named"
    return release, None


def submodule_paths(root):
    """Return the paths of the git submodules in ``root/.gitmodules`` (as ``conf.py``
    reads them).
    """
    parser = configparser.ConfigParser()
    try:
        parser.read(os.path.join(root, ".gitmodules"), encoding="utf-8")
    except (configparser.Error, UnicodeDecodeError):
        return []
    return [parser[s]["path"] for s in parser.sections() if "path" in parser[s]]


@dataclass(frozen=True)
class ProjectPath:
    """The MATLAB project path: ``folders`` (relative, ``/``, ``""`` for the
    root) and the start-up and shut-down files (``hooks``).
    """

    source: str
    folders: frozenset[str]
    hooks: tuple[str, ...]


def _relative(path):
    """Return ``path`` of a project file, relative to the root with ``/``, or None
    for a path outside the root.
    """
    path = path.replace("\\", "/").strip("/")
    parts = [p for p in path.split("/") if p not in ("", ".")]
    if ".." in parts or re.match(r"[A-Za-z]:", path):
        return None
    return "/".join(parts)


def _strings(value):
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _table(data, key):
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _project_toml(root):
    with open(os.path.join(root, "matlab.toml"), "rb") as f:
        data = tomllib.load(f)
    project = _table(data, "project")
    hooks = [
        *_strings(project.get("startup-files")),
        *_strings(project.get("shutdown-files")),
    ]
    return _strings(_table(data, "folders").get("path")), hooks


def _project_xml(root):
    """Path entries and hooks of the three ``.prj`` layouts (single file,
    multi-file, fixed-path multi-file): ``<Info Ref="src" Type="Relative"/>``
    and ``<Info File=... Type="StartUp"/>`` (checked in R2026a).
    """
    folders, hooks = [], []
    for path in sorted(Path(root, "resources", "project").rglob("*.xml")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for tag in _INFO.findall(text):
            attributes = dict(_ATTRIBUTE.findall(tag))
            kind = attributes.get("Type")
            if kind == "Relative" and "Ref" in attributes:
                folders.append(attributes["Ref"])
            elif kind in ("StartUp", "Shutdown") and "File" in attributes:
                hooks.append(attributes["File"])
    return folders, hooks


def project_path(root):
    """Return the ``ProjectPath`` of ``matlab.toml`` or of a ``.prj``
    project's ``resources/project`` files, or None (none, unreadable, or no
    path folder): then nothing is suggested.
    """
    if os.path.isfile(os.path.join(root, "matlab.toml")):
        source = "matlab.toml"
        try:
            folders, hooks = _project_toml(root)
        except (OSError, tomllib.TOMLDecodeError):
            return None
    elif os.path.isdir(os.path.join(root, "resources", "project")):
        source = "resources/project"
        folders, hooks = _project_xml(root)
    else:
        return None
    folders = {f for f in map(_relative, folders) if f is not None}
    if not folders:
        return None
    hooks = tuple(h for h in map(_relative, hooks) if h)
    return ProjectPath(source, frozenset(folders), hooks)


def path_suggestions(references, path):
    """Return exclusion suggestions: the highest folders with code that are not on
    the MATLAB project ``path`` and hold no folder of it, and its start-up and
    shut-down files.
    """
    out = set()
    for ref in references:
        parts = ref.split("/")[:-1]
        # MATLAB puts the folder above the first +, @ or private folder on the path.
        cut = next(
            (i for i, p in enumerate(parts) if p[:1] in "+@" or p == "private"),
            len(parts),
        )
        folder = parts[:cut]
        if "/".join(folder) in path.folders:
            continue
        if not folder:
            out.add(parts[0] if parts else ref)
            continue
        for i in range(1, len(folder) + 1):
            candidate = "/".join(folder[:i])
            if not any(
                f == candidate or f.startswith(f"{candidate}/") for f in path.folders
            ):
                out.add(candidate)
                break
    out.update(h for h in path.hooks if h in references)
    return sorted(out)


def code_next_to(paths):
    """Return the sidecar doc ``paths`` in a folder with a MATLAB code file."""
    suffixes = extensions()
    out = []
    for path in paths:
        folder = os.path.dirname(path)
        if any(os.path.splitext(name)[1] in suffixes for name in os.listdir(folder)):
            out.append(path)
    return out


def is_importable(name):
    """Return True if the module ``name`` can be imported."""
    return importlib.util.find_spec(name) is not None


# --- from the index ----------------------------------------------------------


def help_blocks(lines):
    """Return the comment blocks that can be help, as lists of
    ``(row, line)``: the first block of the file and the blocks right before or after a
    ``function`` or ``classdef`` line.
    """
    out, block, before, seen_code = [], [], "", False
    for row, line in enumerate([*lines, ""]):
        if _COMMENT.match(line):
            block.append((row, line))
            continue
        if block:
            if not seen_code or _DECLARATION.match(before) or _DECLARATION.match(line):
                out.append(block)
            block = []
        if line.strip():
            seen_code = True
            before = line
    return out


def _texts(source_index):
    """Yield ``(reference, lines)`` of the indexed ``.m`` files with text."""
    for path, record in source_index.index.items():
        key = (path, record["mtime"], record["size"])
        text = source_index.text_cache.get(key)
        if path.endswith(".m") and text is not None:
            yield record["reference"], text.splitlines()


@dataclass
class Survey:
    """The help headings (``% Inputs:``) of a project: by casefolded key,
    the spellings and the files using it; and the copyright blocks that run
    into help (``reference:line``).
    """

    spellings: dict
    files: dict
    legal: list


def survey(source_index):
    """Return the ``Survey`` of the help blocks of ``source_index``."""
    spellings = collections.defaultdict(collections.Counter)
    files = collections.defaultdict(set)
    legal = []
    for ref, lines in _texts(source_index):
        hit = None
        for block in help_blocks(lines):
            for _row, line in block:
                if m := _HEADING.match(line):
                    heading = m.group(1)
                    spellings[heading.casefold()][heading] += 1
                    files[heading.casefold()].add(ref)
            later = (row for row, line in block[1:] if _LEGAL.match(line))
            hit = hit or next(later, None)
        if hit is not None:
            legal.append(f"{ref}:{hit + 1}")
    return Survey(dict(spellings), dict(files), sorted(legal))


def _spelling(found, key):
    """Return the most common spelling of a heading (the first of a tie)."""
    counts = found.spellings[key]
    return min(counts, key=lambda s: (-counts[s], s))


def _partner(key, sections):
    """Return the section that ``key`` is the plural or singular of, or None."""
    for other in (f"{key}s", key.removesuffix("s")):
        if other != key and other in sections:
            return other
    return None


@dataclass
class Headings:
    """What the survey gives ``napoleon_custom_sections``: the ``entries``,
    and the headings by fate (``(spelling, files)`` lists).
    """

    entries: list
    used: list
    builtin: list
    unmatchable: list
    unused: list


#: lowercase words that make a colon-ended help line a sentence, not a heading
_PROSE_WORDS = frozenset(
    {
        "a", "an", "the", "of", "to", "for", "in", "on", "at", "by", "with",
        "is", "are", "be", "this", "that", "these", "those", "which", "it",
    }
)  # fmt: skip


def _prose(spelling):
    """Return True if a heading ``spelling`` reads as a sentence: over three words,
    or a lowercase function word.
    """
    words = spelling.split()
    return len(words) > 3 or any(w in _PROSE_WORDS for w in words)


def napoleon_headings(found, threshold=SECTION_FILES):
    """Return the ``Headings`` of a ``Survey``: a heading in ``threshold`` or more
    files becomes a section (parameter-like headings ``params_style``); its
    plural or singular an alias; built-ins and headings napoleon cannot
    match are skipped.
    """
    keys = sorted(found.files, key=lambda k: (-len(found.files[k]), k))
    sections, aliases = {}, []
    out = Headings([], [], [], [], [])
    for key in keys:
        row = (_spelling(found, key), len(found.files[key]))
        if key in NAPOLEON_SECTIONS:
            out.builtin.append(row)
        elif not _MATCHABLE.match(key):
            out.unmatchable.append(row)
        elif partner := _partner(key, sections):
            aliases.append((row[0], sections[partner]))
            out.used.append(row)
        elif row[1] >= threshold:
            sections[key] = row[0]
            params = _PARAMS.fullmatch(key)
            out.entries.append((row[0], "params_style") if params else row[0])
            out.used.append(row)
        elif not _prose(row[0]):
            out.unused.append(row)
    # An alias follows its section: napoleon looks the section up when it reads it.
    out.entries.extend(aliases)
    return out


def has_simulink(source_index):
    """Return True if the index has a Simulink model, library or subsystem file."""
    return any(r["type"] in KINDS for r in source_index.index.values())


def inventory(source_index):
    """Return counts and lists of the index for the report."""
    kinds = collections.Counter()
    namespaces = set()
    not_callable, encoding = [], []
    for path, record in source_index.index.items():
        ref = record["reference"]
        kinds[record["type"]] += 1
        if record["matlab_name"] is None:
            # as the mat.not_callable warnings
            naming = getattr(handler_by_extension(path), "naming", "code")
            if (naming == "model" and record["type"] != UNKNOWN) or (
                naming == "code" and not record["private"] and not is_hidden(ref)
            ):
                not_callable.append(ref)
        else:
            parts = ref.split("/")[:-1]
            stop = next(
                (i for i, p in enumerate(parts) if p[:1] == "@" or p == "private"),
                len(parts),
            )
            run = []
            for part in parts[:stop]:
                run = [*run, part[1:]] if part[:1] == "+" else []
            if run:
                namespaces.add(".".join(run))
        if any(w[0] == "encoding" for w in record["warnings"]):
            encoding.append(ref)
    duplicates = {
        name: files
        for name, refs in sorted(source_index.matlab_names.items())
        if len(
            files := sorted(r for r in refs if not r.endswith("/") and not is_hidden(r))
        )
        > 1
    }
    return {
        "kinds": kinds,
        "unknown": kinds.pop(UNKNOWN, 0),
        "namespaces": sorted(namespaces),
        "duplicates": duplicates,
        "not_callable": sorted(not_callable),
        "encoding": sorted(encoding),
    }
