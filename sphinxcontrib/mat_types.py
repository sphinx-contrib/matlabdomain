"""sphinxcontrib.mat_types
~~~~~~~~~~~~~~~~~~~~~~~

Types for MATLAB.

:copyright: Copyright 2014-2024 by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import copy
import difflib
import ntpath
import os
import stat
import sys
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, cast
from zipfile import ZipFile

from sphinx.environment import CONFIG_OK
from sphinx.errors import ConfigError
from sphinx.util.build_phase import BuildPhase
from sphinx.util.logging import getLogger, suppress_logging
from sphinx.util.matching import Matcher
from tree_sitter import Node, Parser, Tree

from sphinxcontrib.mat_tree_sitter_parser import (
    ML_LANG,
    MatClassParser,
    MatFunctionParser,
    MatScriptParser,
    declaration,
    first_error,
    get_row,
    parsed_type,
)

from . import mat_naming
from .mat_classify import (
    FUNCTION,
    SCRIPT,
    UNKNOWN,
    classify,
    decode_source,
    first_line_of_code,
    has_mex_file,
    is_help_only,
    is_hidden,
)
from .mat_handlers import handler_by_extension, handler_for, handlers
from .mat_naming import (
    ROOT_REFERENCE,
    folder_of,
    is_private_reference,
    join_reference,
    parse_reference,
)
from .mat_simulink import read_diagram

logger = getLogger("matlab-domain")

__all__ = [
    "MatApplication",
    "MatBlock",
    "MatClass",
    "MatEnumeration",
    "MatEvent",
    "MatFunction",
    "MatLibrary",
    "MatMethod",
    "MatModel",
    "MatModule",
    "MatModuleAnalyzer",
    "MatObject",
    "MatProperty",
    "MatScript",
    "MatSimulinkFile",
    "MatSubsystemFile",
]


# MATLAB attribute type dictionaries.

# From:
#  - http://www.mathworks.com/help/matlab/matlab_oop/class-attributes.html
MATLAB_CLASS_ATTRIBUTE_TYPES = {
    "Abstract": bool,
    "AllowedSubclasses": list,
    "ConstructOnLoad": bool,
    "HandleCompatible": bool,
    "Hidden": bool,
    "InferiorClasses": list,
    "Sealed": bool,
    "SharedTestFixtures": list,
    "TestTags": list,
}

# From:
#  - https://mathworks.com/help/matlab/matlab_oop/property-attributes.html
#  - https://mathworks.com/help/matlab/matlab_prog/define-property-attributes-1.htm
#  - https://mathworks.com/help/matlab/ref/matlab.unittest.testcase-class.html
MATLAB_PROPERTY_ATTRIBUTE_TYPES = {
    "AbortSet": bool,
    "Abstract": bool,
    "Access": list,
    "ClassSetupParameter": bool,
    "Constant": bool,
    "Dependent": bool,
    "DiscreteState": bool,
    "GetAccess": list,
    "GetObservable": bool,
    "Hidden": bool,
    "MethodSetupParameter": bool,
    "NonCopyable": bool,
    "Nontunable": bool,
    "PartialMatchPriority": bool,
    "SetAccess": list,
    "SetObservable": bool,
    "TestParameter": bool,
    "Transient": bool,
}

# From
#  - https://mathworks.com/help/matlab/matlab_oop/method-attributes.html
#  - https://mathworks.com/help/matlab/ref/matlab.unittest.testcase-class.html
MATLAB_METHOD_ATTRIBUTE_TYPES = {
    "Abstract": bool,
    "Access": list,
    "Hidden": bool,
    "ParameterCombination": bool,
    "Sealed": list,
    "Static": bool,
    "Test": bool,
    "TestClassSetup": bool,
    "TestClassTeardown": bool,
    "TestMethodSetup": bool,
    "TestMethodTeardown": bool,
    "TestTags": list,
}

# The parsed-source model lives in ``env.domaindata['mat']`` and is pickled
# with the environment (plan.md Sections 2.1 and 2.2):
#
#   index: source path -> index-stage record (reference, type, mtime, size,
#     warnings, unreadable; matlab_name, private, scope from naming).
#   entities_table: path reference -> object. The index stage creates the
#     folders (the project root is ``./``); files are parsed on first use
#     (``resolve``).
#   parse_cache / parse_warnings: (path, mtime_ns, size) -> parsed object /
#     its parse-stage warnings, kept while the key is unchanged.
#   matlab_names: MATLAB name -> path references of the files and namespace
#     folders with that name (class-folder methods are reached through their
#     class).
#   doc_sources: docname -> {path: (mtime_ns, size)} of the files a document
#     used while it was read (incremental builds, parse-stage warnings).
#
# Tree-sitter objects are never pickled (see ``MatObject.__reduce_ex__``).


class _DetachedEntityStore:
    """Fallback for parsing outside a Sphinx build (unit tests that call
    ``MatObject.matlabify``): no index; files are parsed on every lookup.
    """

    def __init__(self):
        self.entities_table = {}
        self.data = {"matlab_names": {}, "index": {}}

    def source_paths(self):
        return {}

    def resolve(self, ref):
        parts = [] if ref == ROOT_REFERENCE else ref.rstrip("/").split("/")
        path = os.path.join(cast(str, MatObject.basedir), *parts)
        if ref.endswith("/"):
            top = os.path.join(cast(str, MatObject.basedir), parts[0]) if parts else ""
            if not os.path.isdir(path) or (parts and skipped_folder(top, parts[0])):
                return None
            return MatModule(os.path.basename(path), path, ref)
        handler = handler_for(path)
        if handler is None:
            return None
        stem = os.path.splitext(parts[-1])[0]
        obj = _parse(handler, path, stem, folder_of(ref), handler.classify(path))
        obj.ref = ref
        return obj


_detached_store = _DetachedEntityStore()


def _domain(env=None):
    """Return the owner of the transient entity model: the live ``mat`` domain
    when a Sphinx build is active, else a detached fallback store.
    """
    env = env or MatObject.sphinx_env
    if env is None:
        return _detached_store
    return env.get_domain("mat")


def _is_class_folder(folder):
    return folder.rstrip("/").rpartition("/")[2].startswith("@")


def class_file_reference(folder):
    """Return the reference of the class file of the class folder ``folder``
    (``a/@Cls/`` -> ``a/@Cls/Cls.m``). Only if that file is a classdef is the
    folder a class, with its function files as methods.
    """
    name = folder.rstrip("/").rpartition("/")[2][1:]
    return join_reference(folder, f"{name}.m")


def _reading_docname(dom):
    """Return the document being read, or None outside the read phase."""
    if isinstance(dom, _DetachedEntityStore):
        return None
    # ``app.phase``, not ``builder.phase``: the latter exists from Sphinx 9.0 only.
    if getattr(MatObject.sphinx_app, "phase", None) != BuildPhase.READING:
        return None
    return dom.env.docname or None


def _note_lookup(dom):
    """Mark the document being read as depending on the index; return its
    used files (``{path: (mtime_ns, size)}``) or None.
    """
    docname = _reading_docname(dom)
    if docname is None:
        return None
    return dom.data["doc_sources"].setdefault(docname, {})


def _note_use(dom, ref):
    """Record a file (with its class-folder siblings) as used by the document
    being read. A file that could not be read makes it re-read every build.
    """
    used = _note_lookup(dom)
    if used is None:
        return
    folder = folder_of(ref)
    refs = [ref]
    if _is_class_folder(folder):
        refs = [r for _, r in dom.entities_table[folder].members if r[-1:] != "/"]
    for r in refs:
        path = dom.source_paths()[r]
        record = dom.data["index"][path]
        used[path] = (record["mtime"], record["size"])
        if getattr(dom.entities_table.get(r), "unreadable", False):
            dom.env.note_reread()


def resolve(dom, ref) -> Any:
    """Object of a file or folder reference (without members), or None.

    Folders come from the index stage. A file is parsed on first use in this
    process, or taken from the parse cache, and recorded as used by the
    document being read.
    """
    if isinstance(dom, _DetachedEntityStore):
        return dom.resolve(ref)
    if ref[-1:] == "/":
        return dom.entities_table.get(ref)
    obj = dom.entities_table.get(ref)
    if obj is None:
        if ref not in dom.source_paths():
            return None
        folder = folder_of(ref)
        if _is_class_folder(folder):
            _load_class_folder(dom, folder)
        else:
            _load(dom, ref)
        obj = dom.entities_table[ref]
    _note_use(dom, ref)
    return obj


def _resolve_path(dom, rel):
    """Object for a path below the root, given without its extension or the
    trailing ``/`` of a folder (``.m`` before ``.mlapp``), or None.
    """
    for ref in (f"{rel}/", rel, *(rel + h.extension for h in handlers())):
        obj = resolve(dom, ref)
        if obj is not None:
            return obj
    return None


def _parse(handler, path, stem, folder, kind, text=None) -> Any:
    """Parse one file; a failure gives an empty placeholder of the type ``kind``."""
    try:
        if text is None:
            obj = handler.parse(path, stem, folder, MatObject.encoding)
        else:
            obj = handler.parse(path, stem, folder, MatObject.encoding, text=text)
    except Exception as err:  # one bad file must not stop the build
        obj = placeholder(kind, stem, folder)
        obj.source_warnings = [("parse_error", failure_message(err), None)]
        obj.unreadable = isinstance(err, OSError)
    if obj is None:
        obj = placeholder(kind, stem, folder)
    if obj.source_type is None:
        obj.source_type = kind
    return obj


def _load(dom, ref):
    """Parse (or reuse) the file ``ref`` and add it to the entities table."""
    data = dom.data
    path = dom.source_paths()[ref]
    record = data["index"][path]
    key = (path, record["mtime"], record["size"])
    obj = data["parse_cache"].get(key)
    if obj is not None and obj.source_type != record["type"]:
        # a help file whose MEX file was added or removed
        obj = None
    if obj is None:
        stem = os.path.splitext(os.path.basename(path))[0]
        if record["unreadable"]:
            # The index stage warned already.
            obj = placeholder(record["type"], stem, folder_of(ref))
            obj.source_type, obj.unreadable = record["type"], True
        else:
            handler = handler_by_extension(path)
            text = dom.text_cache.pop(key, None)
            obj = _parse(handler, path, stem, folder_of(ref), record["type"], text)
            if warnings := parse_warnings(path, ref, obj):
                data["parse_warnings"][key] = warnings
            # A read failure may go away without changing the key (permissions).
            if not obj.unreadable:
                data["parse_cache"][key] = obj
    else:
        logger.debug("[sphinxcontrib-matlabdomain] reusing parsed %s", path)
    obj.ref = ref
    obj.matlab_name = record["matlab_name"]
    obj.private, obj.scope = record["private"], record["scope"]
    dom.entities_table[ref] = obj
    return obj


def _load_class_folder(dom, folder):
    """Load the files of the class folder ``folder``. If its class file
    (``class_file_reference``) is a classdef, its function files become
    methods of that class; otherwise (no class file, an old-style
    constructor, a classdef named differently) none is a method.
    """
    cf_entity = dom.entities_table[folder]
    entities = {ref: _load(dom, ref) for _, ref in cf_entity.members if ref[-1:] != "/"}
    class_ref = class_file_reference(folder)
    cls = entities.get(class_ref)
    record = dom.data["index"].get(dom.source_paths().get(class_ref))
    if not isinstance(cls, MatClass) or record is None or record["type"] != "class":
        return
    # Drop folder methods attached to a class reused from the parse cache.
    cls.methods = {
        n: m
        for n, m in cls.methods.items()
        if not getattr(m, "from_class_folder", False)
    }
    for ref, func in entities.items():
        if not isinstance(func, MatFunction):
            continue
        # A copy: the parse cache keeps the function for a later build in
        # which the folder is no class.
        method = copy.copy(func)
        method.__class__ = MatMethod
        method = cast(MatMethod, method)
        method.cls = cls
        # The attributes of its signature in the classdef; none if undeclared.
        method.attrs = cls.declarations.get(method.name, {})
        method.from_class_folder = True
        cls.methods[method.name] = method
        dom.entities_table[ref] = method


def _attrs(dom, ref):
    """``(matlab_name, private, scope)`` of a discovered file or folder
    reference, without parsing; None if it is not discovered.
    """
    if ref[-1:] == "/":
        entity = dom.entities_table.get(ref)
        if entity is None:
            return None
        return (
            getattr(entity, "matlab_name", None),
            getattr(entity, "private", False),
            getattr(entity, "scope", None),
        )
    record = dom.data["index"].get(dom.source_paths().get(ref))
    if record is None:
        return None
    return record.get("matlab_name"), record.get("private", False), record.get("scope")


def source_scope(dom, reference):
    """Folder from which the MATLAB name of ``reference`` is visible."""
    file, _ = parse_reference(reference)
    attrs = _attrs(dom, reference if file is None else file)
    return folder_of(reference) if attrs is None else attrs[2]


def _member(entity, members):
    obj = entity
    for name in members:
        if obj is None or isinstance(obj, MatModule):
            return None
        obj = obj.getter(name)
    return obj


def lookup_reference(dom, reference):
    """Discovered object with the exact path reference, or None."""
    file, members = parse_reference(reference)
    if file is None:
        return None
    return _member(resolve(dom, file), members)


def _named(dom, name):
    """Return ``(reference, file or folder reference)`` for a MATLAB name.

    The longest known prefix of ``name`` is the file or folder; the rest are
    members (``pkg.Cls.method``).
    """
    parts = name.split(".")
    for i in range(len(parts), 0, -1):
        refs = dom.data["matlab_names"].get(".".join(parts[:i]))
        if refs:
            return [(".".join([ref, *parts[i:]]), ref) for ref in refs]
    return []


def is_source_object(obj):
    """Return True for anything but a folder."""
    return not isinstance(obj, MatModule)


def is_folder_object(obj):
    """Return True for a folder."""
    return isinstance(obj, MatModule)


# ``find_source`` tests these on the reference, so it need not parse files.
is_source_object.folders = False
is_folder_object.folders = True


def is_code_object(obj):
    """Return True for anything but a folder or a Simulink file."""
    return is_source_object(obj) and not isinstance(obj, MatSimulinkFile)


is_code_object.folders = False
# Directives that document code never take a Simulink file.
is_code_object.refs = lambda file: (
    not mat_naming.is_block_container(file.rpartition("/")[2])
)


def simulink_accepts(cls):
    """Return a ``find_source`` predicate for the Simulink objects of ``cls``."""

    def accept(obj):
        return isinstance(obj, cls)

    accept.refs = lambda file: mat_naming.is_block_container(file.rpartition("/")[2])
    return accept


def _match(dom, ref, accept):
    """``(ref, object)`` if ``ref`` names an accepted object, else None.

    The object is None (resolved later) when ``accept`` only asks for a file
    or a folder.
    """
    file, members = parse_reference(ref)
    if file is None:
        return None
    refs = getattr(accept, "refs", None)
    if refs is not None and not refs(file):
        return None
    folders = getattr(accept, "folders", None)
    if folders is not None and not members:
        if file[-1:] == "/":
            exists = file in dom.entities_table
        else:
            exists = file in dom.source_paths()
        return (ref, None) if exists and (file[-1:] == "/") == folders else None
    obj = _member(resolve(dom, file), members)
    return (ref, obj) if obj is not None and accept(obj) else None


def _resolved(dom, matches):
    return [(ref, resolve(dom, ref) if obj is None else obj) for ref, obj in matches]


def find_source(dom, target, folder=None, accept=is_source_object):
    """Resolve ``target`` to discovered objects (plan.md Section 2.3).

    1. exact path reference; 2. relative to ``folder`` (a path below it, or a
    MATLAB name visible from it, including its ``private/``); 3. a MATLAB name,
    excluding private files. Only objects for which ``accept(obj)`` is true
    count. A folder path without its trailing ``/`` is tried last, so it
    never shadows a MATLAB name. Returns ``[(reference, object)]``: empty if
    nothing matches, several if the MATLAB name is ambiguous. Only the files
    of the returned objects (and of members looked up) are parsed.
    """
    _note_lookup(dom)
    target = unicodedata.normalize("NFC", target.strip())
    if target == ".":
        target = ROOT_REFERENCE
    exact = [target]
    if folder:
        exact.append(join_reference(folder, target))
    for ref in exact:
        if match := _match(dom, ref, accept):
            return _resolved(dom, [match])

    named = [
        (match, cast(tuple[str, bool, str], _attrs(dom, base)))
        for ref, base in _named(dom, target)
        if (match := _match(dom, ref, accept))
    ]
    if folder:
        local = [match for match, attrs in named if attrs[2] == folder]
        if local:
            return _resolved(dom, local)
    public = [match for match, attrs in named if not attrs[1]]
    if public:
        return _resolved(dom, public)

    for ref in (f"{r}/" for r in exact if not r.endswith("/")):
        if match := _match(dom, ref, accept):
            return _resolved(dom, [match])
    return []


def folder_reference(dom, target, location=None):
    """Folder reference for a folder argument (path or namespace name)."""
    target = target.strip()
    if target in (".", ROOT_REFERENCE):
        return ROOT_REFERENCE
    found = find_source(dom, target, accept=is_folder_object)
    if len(found) == 1:
        return found[0][0]
    if found:
        logger.warning(
            "[sphinxcontrib-matlabdomain] %r matches several folders: %s; "
            "use a path reference",
            target,
            ", ".join(sorted(ref for ref, _ in found)),
            type="mat",
            subtype="ambiguous",
            location=location,
        )
    return target if target.endswith("/") else f"{target}/"


def display_name(dom, reference):
    """MATLAB name of a reference, or the reference if it has none. A block
    of a Simulink file follows the file's name with its Simulink path.
    """
    file, members = parse_reference(reference)
    attrs = _attrs(dom, file if file is not None else reference)
    if attrs is None or attrs[0] is None:
        return reference
    if members and mat_naming.is_block_container(cast(str, file).rpartition("/")[2]):
        return "/".join([attrs[0], *members])
    return ".".join([attrs[0], *members])


# Warnings hidden files (``is_hidden``) do not get.
_HIDDEN_QUIET = ("invalid_matlab", "empty_code_file")
# Warnings the index stage reports; a parse does not repeat them.
_INDEX_SUBTYPES = ("encoding",)


def file_like_folder(name):
    """Return the extension of a supported file type (source or sidecar
    doc, any case) that the folder name ``name`` ends in, else None.
    """
    lowered = name.lower()
    for extension in (*(h.extension for h in handlers()), *SIDECAR_SUFFIXES):
        if len(lowered) > len(extension) and lowered.endswith(extension):
            return extension
    return None


#: files Sphinx writes into its output folders: HTML builders and doctrees
SPHINX_OUTPUT_MARKERS = frozenset((".buildinfo", "environment.pickle"))
#: the build folder of the Makefile and make.bat of a Sphinx source folder
BUILD_FOLDER = "_build"


def sphinx_output(path, names):
    """Return True if the folder ``path`` with the entries ``names`` is Sphinx
    output, which holds copies of MATLAB files (``_downloads``): it has a
    marker file, or a ``doctrees`` or ``.doctrees`` folder with one (the
    output folder of any builder, ``_build`` of ``make``).
    """
    if not SPHINX_OUTPUT_MARKERS.isdisjoint(names):
        return True
    return any(
        name in names and os.path.isfile(os.path.join(path, name, "environment.pickle"))
        for name in ("doctrees", ".doctrees")
    )


def skipped_folder(path, name):
    """Return True if the folder ``path`` (named ``name``) is never searched:
    a hidden folder (``.git``) or Sphinx output.
    """
    if name.startswith("."):
        return True
    try:
        return sphinx_output(path, os.listdir(path))
    except OSError:
        return False


def _warn(subtype, message, location=None):
    logger.warning(
        "[sphinxcontrib-matlabdomain] %s",
        message,
        type="mat",
        subtype=subtype,
        location=location,
    )


def _warn_file(ref, path, subtype, message, row):
    if not (is_hidden(ref) and subtype in _HIDDEN_QUIET):
        _warn(subtype, f"{ref} {message}", None if row is None else f"{path}:{row + 1}")


def parse_warnings(path, ref, obj):
    """Parse-stage warnings of a parsed file, ``[(subtype, message, location)]``:
    problems recorded while parsing it (``source_warnings``) and
    ``classify()`` disagreeing with tree-sitter.
    """
    hidden = is_hidden(ref)
    out = [
        (subtype, f"{ref} {message}", None if row is None else f"{path}:{row + 1}")
        for subtype, message, row in obj.source_warnings
        if subtype not in _INDEX_SUBTYPES and not (hidden and subtype in _HIDDEN_QUIET)
    ]
    if (
        not hidden
        and obj.parsed_type is not None
        and obj.source_type != obj.parsed_type
    ):
        out.append(
            (
                "invalid_matlab",
                f"{ref}: its first line of code makes it a {obj.source_type}, but "
                f"tree-sitter parsed a {obj.parsed_type}; the file may be invalid "
                "MATLAB.",
                None,
            )
        )
    return out


def project_root(config, srcdir):
    """Absolute project root, or ``None`` if none is configured.

    A relative ``matlab_src_code_project_root`` is relative to ``srcdir``
    (keeps sphinx-multiversion working).
    """
    root = config.matlab_src_code_project_root
    if root is None:
        return None
    if not isinstance(root, str):
        raise ConfigError(
            f"matlab_src_code_project_root must be a str or None, not {root!r}."
        )
    return os.path.normpath(os.path.join(srcdir, root))


DEFAULT_INCLUDE_PATTERNS = ["**/*"]
#: root files that are neither code nor sidecar docs (plan.md Section 2.11)
DEFAULT_EXCLUSION_PATTERNS = [
    "README.*",
    "CHANGES.*",
    "CHANGELOG.*",
    "LICENSE.*",
    "CONTRIBUTING.*",
    "CODE_OF_CONDUCT.*",
    "SECURITY.*",
]
#: suffixes ``matlab_src_sidecar_suffixes`` accepts, in a fixed order
SIDECAR_SUFFIXES = (".md", ".rst")
_GLOB_CHARS = frozenset("*?[")


def _normalize_pattern(pattern, option):
    """``pattern`` relative to the project root, ``..`` resolved; a
    ConfigError for a pattern that is not relative or leaves the root.
    """
    if not isinstance(pattern, str) or not pattern:
        raise ConfigError(f"{option}: {pattern!r} is not a glob pattern.")
    if "\\" in pattern:
        raise ConfigError(f"{option}: {pattern!r} must use '/' as the separator.")
    if pattern.startswith("/") or ntpath.splitdrive(pattern)[0]:
        raise ConfigError(
            f"{option}: {pattern!r} must be relative to matlab_src_code_project_root."
        )
    parts, wildcard = [], False
    for part in pattern.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            # ``..`` after a wildcard cannot be resolved.
            if wildcard or not parts:
                raise ConfigError(
                    f"{option}: {pattern!r} leaves matlab_src_code_project_root."
                )
            parts.pop()
            continue
        wildcard = wildcard or not _GLOB_CHARS.isdisjoint(part)
        parts.append(part)
    if not parts:
        raise ConfigError(
            f"{option}: {pattern!r} names nothing below matlab_src_code_project_root."
        )
    return "/".join(parts) + ("/" if pattern.endswith("/") else "")


def _literal_folder(pattern):
    """``(folder, deep)``: the literal folders a pattern starts with (``''``
    for none), and whether it can match files in folders below them.
    """
    parts = pattern.rstrip("/").split("/")
    out = ""
    for part in parts[:-1]:
        if not _GLOB_CHARS.isdisjoint(part):
            return out, True
        out += f"{part}/"
    return out, "**" in parts[-1]


class SourceFilter:
    """Include and exclusion patterns below the project root (plan.md Section
    2.4), matched like Sphinx's ``exclude_patterns`` against path references
    (case-sensitive on every OS).
    """

    def __init__(self, include, exclude):
        #: the normalized ``(include, exclude)`` patterns
        self.patterns = (tuple(include), tuple(exclude))
        self.include = Matcher(include)
        self.exclude = Matcher(exclude)
        #: ``(folder, deep)`` the include patterns can reach
        self.reach = sorted({_literal_folder(p) for p in include})
        self.prefixes = sorted({folder for folder, _ in self.reach})

    def includes(self, ref):
        """Return True for a file reference to index."""
        return self.include(ref) and not self.exclude(ref)

    def walks(self, folder):
        """Return True for a folder reference (``a/b/``) to list."""
        if self.exclude(folder) or self.exclude(folder[:-1]):
            return False
        return any(
            prefix.startswith(folder) or (deep and folder.startswith(prefix))
            for prefix, deep in self.reach
        )


def pattern_list(value, option):
    """Normalize the patterns of a config list (or raise ConfigError)."""
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ConfigError(f"{option} must be a list of glob patterns.")
    return [_normalize_pattern(p, option) for p in value]


def check_config_names(names, known):
    """ConfigError naming each ``matlab_*`` name in ``names`` (those of
    ``conf.py``) that is not in ``known``: a typo, or a value this version
    does not have.
    """
    unknown = sorted(n for n in names if n.startswith("matlab_") and n not in known)
    if not unknown:
        return
    ours = sorted(k for k in known if k.startswith("matlab_"))
    problems = []
    for name in unknown:
        close = difflib.get_close_matches(name, ours, n=1)
        hint = f" (did you mean {close[0]}?)" if close else ""
        problems.append(f"{name} is not a configuration value{hint}")
    raise ConfigError(
        f"{'; '.join(problems)}. Correct or delete these names in conf.py (a "
        "helper variable must not start with matlab_)."
    )


def check_text_encoding(encoding, option):
    """ConfigError unless ``encoding`` is None or a known text codec."""
    if encoding is not None:
        try:
            # not b"".decode(): it skips the check for non-text codecs (rot13)
            "a".encode(encoding)
        except (LookupError, TypeError) as err:
            raise ConfigError(
                f"{option} {encoding!r} is not a known text encoding."
            ) from err


def sidecar_suffix_list(value, option="matlab_src_sidecar_suffixes"):
    """Normalize sidecar suffixes in ``SIDECAR_SUFFIXES`` order (or raise
    ConfigError).
    """
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ConfigError(f"{option} must be a list of suffixes such as ['.md'].")
    for suffix in value:
        if suffix not in SIDECAR_SUFFIXES:
            raise ConfigError(
                f"{option}: {suffix!r} is not a sidecar suffix; use "
                f"{', '.join(map(repr, SIDECAR_SUFFIXES))}."
            )
    return tuple(s for s in SIDECAR_SUFFIXES if s in value)


def simulink_doc_suffix_list(value):
    """Normalize ``matlab_simulink_doc_suffixes``, keeping its order: the
    first suffix that exists wins (or raise ConfigError).
    """
    option = "matlab_simulink_doc_suffixes"
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ConfigError(f"{option} must be a list of suffixes such as ['.md'].")
    for suffix in value:
        if suffix not in SIDECAR_SUFFIXES:
            raise ConfigError(
                f"{option}: {suffix!r} is not a documentation suffix; use "
                f"{', '.join(map(repr, SIDECAR_SUFFIXES))}."
            )
    return tuple(dict.fromkeys(value))


def sidecar_layout_error(root, srcdir):
    """ConfigError if sidecar docs cannot be told from the documentation: the
    project root is the Sphinx source folder.
    """
    if os.path.normcase(os.path.normpath(root)) == os.path.normcase(
        os.path.normpath(srcdir)
    ):
        raise ConfigError(
            "matlab_src_sidecar_suffixes needs matlab_src_code_project_root to differ "
            "from the Sphinx source folder."
        )


def source_filter(config):
    """Return the validated ``SourceFilter`` of the config (or ConfigError)."""
    include = pattern_list(
        config.matlab_src_include_patterns, "matlab_src_include_patterns"
    )
    exclude = pattern_list(
        config.matlab_src_exclude_patterns, "matlab_src_exclude_patterns"
    )
    customized = list(config.matlab_src_include_patterns) != DEFAULT_INCLUDE_PATTERNS
    customized |= bool(exclude) and exclude != DEFAULT_EXCLUSION_PATTERNS
    if customized and config.matlab_src_code_project_root is None:
        raise ConfigError(
            "matlab_src_include_patterns and matlab_src_exclude_patterns need "
            "matlab_src_code_project_root."
        )
    return SourceFilter(include, exclude)


def _within(path, root, pathmod=os.path):
    """Return True if the (resolved) ``path`` is ``root`` or below it."""
    try:
        common = pathmod.commonpath([path, root])
    except ValueError:  # another drive
        return False
    return pathmod.normcase(common) == pathmod.normcase(root)


def check_pattern_folders(sources, root, option="matlab_src_include_patterns"):
    """ConfigError if a literal folder of an include pattern resolves (through
    a link or junction) outside the project root.
    """
    real_root = os.path.realpath(root)
    for prefix in sources.prefixes:
        path = os.path.join(root, *prefix.split("/"))
        if prefix and os.path.exists(path):
            real = os.path.realpath(path)
            if not _within(real, real_root):
                raise ConfigError(
                    f"{option}: {prefix} resolves to {real}, "
                    "outside matlab_src_code_project_root."
                )


def _is_link(path):
    """Return True for a symbolic link or a Windows junction."""
    try:
        st = os.lstat(path)
    except OSError:  # pragma: no cover - defensive: the entry vanished after stat
        return False
    junction = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", None)
    return stat.S_ISLNK(st.st_mode) or (
        junction is not None and getattr(st, "st_reparse_tag", None) == junction
    )


@dataclass(frozen=True)
class IndexSettings:
    """What the index stage reads (plan.md Section 2.8), without a Sphinx app.

    ``root`` is the absolute project root; ``include`` and ``exclude`` are
    patterns normalized by ``_normalize_pattern``. ``sidecar_suffixes`` selects the
    sidecar docs (plan.md Section 2.11); files with them below
    ``source_dir`` (the Sphinx source folder) are not sidecar docs when that
    folder is inside the root.
    """

    root: str
    include: tuple[str, ...] = tuple(DEFAULT_INCLUDE_PATTERNS)
    exclude: tuple[str, ...] = tuple(DEFAULT_EXCLUSION_PATTERNS)
    encoding: str | None = None
    matlab_version: str = mat_naming.DEFAULT_MATLAB_VERSION
    sidecar_suffixes: tuple[str, ...] = ()
    source_dir: str | None = None
    #: suffixes of Simulink documentation files, in priority order
    simulink_doc_suffixes: tuple[str, ...] = ()

    @classmethod
    def from_config(cls, config, srcdir):
        """Return the settings of a Sphinx build, or None without a project root."""
        root = project_root(config, srcdir)
        if root is None:
            return None
        include, exclude = source_filter(config).patterns
        return cls(
            root=root,
            include=include,
            exclude=exclude,
            encoding=config.matlab_src_encoding,
            matlab_version=config.matlab_version,
            sidecar_suffixes=sidecar_suffix_list(config.matlab_src_sidecar_suffixes),
            source_dir=os.path.normpath(os.fspath(srcdir)),
            simulink_doc_suffixes=simulink_doc_suffix_list(
                config.matlab_simulink_doc_suffixes
            ),
        )


@dataclass
class SourceIndex:
    """Result of the index stage (``build_index``).

    - ``index``: source path -> record ``{reference, type, mtime, size,
      warnings, unreadable, matlab_name, private, scope}``, in walk order;
    - ``entities``: folder reference -> ``MatModule`` with its ``members``;
    - ``matlab_names``: MATLAB name -> path references;
    - ``text_cache``: ``(path, mtime_ns, size)`` -> decoded text;
    - ``sidecars``: sidecar doc path -> ``{reference, mtime, size}``, in walk
      order. Sidecar docs are not read, named or members of their folder, so
      they never shadow code (plan.md Section 2.11).
    - ``simulink_docs``: Simulink documentation file path -> ``{reference,
      mtime, size}``: a file with a suffix of ``simulink_doc_suffixes`` and
      the exact name of a Simulink file next to it. It is not a sidecar doc.
    """

    settings: IndexSettings
    index: dict = field(default_factory=dict)
    entities: dict = field(default_factory=dict)
    matlab_names: dict = field(default_factory=dict)
    text_cache: dict = field(default_factory=dict)
    sidecars: dict = field(default_factory=dict)
    simulink_docs: dict = field(default_factory=dict)


def build_index(settings, old_index=None):
    """Run the index stage for ``settings`` without a Sphinx app.

    Walks the root, reads and classifies each selected file once and names
    files and folders the MATLAB way. Records in ``old_index`` (``{path:
    record}`` of an earlier run) are reused for files whose ``(mtime, size)``
    did not change. Warnings go through ``sphinx.util.logging``
    (``type="mat"``).
    """
    out = SourceIndex(settings)
    if os.path.isdir(settings.root):
        try:
            _Indexer(out, old_index or {}).run()
        except Exception as e:  # pragma: no cover - defensive: log an indexer bug
            import traceback

            logger.error(f"[sphinxcontrib-matlabdomain] ERROR in analyze: {e}")
            logger.error(
                f"[sphinxcontrib-matlabdomain] Traceback: {traceback.format_exc()}"
            )
            raise
    name_sources(out)
    return out


def sidecar_paths(settings):
    """Paths of the sidecar docs below the root, in walk order: the walk of
    ``build_index`` without reading files or warning.
    """
    return list(_documentation_files(settings).sidecars)


def _documentation_files(settings):
    out = SourceIndex(settings)
    if (settings.sidecar_suffixes or settings.simulink_doc_suffixes) and (
        os.path.isdir(settings.root)
    ):
        # The index stage warns about the walk.
        with suppress_logging():
            _Indexer(out, {}, sidecars_only=True).run()
    return out


class _Indexer:
    """The index stage (plan.md Section 2.1): walk the project root and read,
    decode and classify each source file once. Records of files whose
    ``(path, mtime, size)`` did not change are reused without reading.
    Sidecar docs (plan.md Section 2.11) are recorded, not read. With
    ``sidecars_only`` the walk records sidecar docs only.
    """

    def __init__(self, out, old_index, sidecars_only=False):
        settings = out.settings
        self.out = out
        self.basedir = settings.root
        self.old_index = old_index
        self.sources = SourceFilter(settings.include, settings.exclude)
        self.real_root = os.path.realpath(self.basedir)
        self.encoding = settings.encoding
        self.pending = {}
        self.sidecars_only = sidecars_only
        self.sidecar_suffixes = frozenset(settings.sidecar_suffixes)
        self.simulink_doc_suffixes = frozenset(settings.simulink_doc_suffixes)
        # The Sphinx source folder inside the root holds the documentation.
        docs = settings.source_dir
        if docs is not None and not (
            _within(docs, self.basedir)
            and os.path.normcase(docs) != os.path.normcase(self.basedir)
        ):
            docs = None
        self.docs = docs
        # make's build folder (BUILDDIR = _build) exists before the first build
        self.build_dir = None
        if settings.source_dir is not None:
            self.build_dir = os.path.normcase(
                os.path.join(settings.source_dir, BUILD_FOLDER)
            )

    def run(self):
        root = MatModule(os.path.basename(self.basedir), self.basedir, ROOT_REFERENCE)
        self.out.entities[ROOT_REFERENCE] = root
        self.list(root)
        self.descend(root)

    def descend(self, mod):
        kept = []
        for name, ref in mod.members:
            if ref[-1:] == "/":
                child = self.pending.pop(ref)
                if not self.list(child):  # a Sphinx output folder
                    continue
                self.out.entities[ref] = child
                self.descend(child)
            kept.append((name, ref))
        mod.members = kept

    def outside(self, path, ref):
        real = os.path.realpath(path)
        if _within(real, self.real_root):
            return False
        _warn(
            "outside_root",
            f"{ref} links to {real}, outside matlab_src_code_project_root; it is "
            "not documented.",
        )
        return True

    def list(self, mod):
        """List the folder ``mod`` into its members; return False, with no
        members, if it is a Sphinx output folder.
        """
        mod.members = []
        try:
            keys = os.listdir(mod.path)
        except OSError as err:  # one bad folder must not stop the build
            _warn(
                "parse_error",
                f"{mod.ref} cannot be read ({err.strerror or err}); its contents "
                "are not documented.",
            )
            return True
        if mod.ref != ROOT_REFERENCE and sphinx_output(mod.path, keys):
            return False
        sidecars = bool(self.sidecar_suffixes) and not (
            self.docs is not None and _within(mod.path, self.docs)
        )
        denied = []
        # documentation file candidates, and the stems of Simulink files
        loose, simulink_stems = [], set()
        for key in keys:
            if _undecodable(key):
                _warn(
                    "parse_error",
                    f"{mod.ref}: the name {os.fsencode(key)!r} is not valid UTF-8; "
                    "it is not documented.",
                )
                continue
            path = os.path.join(mod.path, key)
            ref = join_reference(mod.ref, unicodedata.normalize("NFC", key))
            try:
                st = os.stat(path)
            except PermissionError as err:  # e.g. a folder listed but not entered
                if not key.startswith("."):  # skipped folders stay quiet
                    denied.append(err)
                continue
            except OSError:  # e.g. a broken link
                continue
            if stat.S_ISDIR(st.st_mode):
                # VCS and editors; Sphinx output (more in list())
                if key.startswith(".") or os.path.normcase(path) == self.build_dir:
                    continue
                ref += "/"
                if not self.sources.walks(ref):
                    continue
                if (extension := file_like_folder(key)) is not None:
                    logger.error(
                        "[sphinxcontrib-matlabdomain] %s: a folder must not be "
                        "named like a %s file; its contents are not documented.",
                        ref,
                        extension,
                        type="mat",
                        subtype="folder_name",
                    )
                    continue
                if _is_link(path) and self.outside(path, ref):
                    continue
                self.pending[ref] = MatModule(key, path, ref)
                mod.members.append((key, ref))
                continue
            handler = handler_for(path)
            if handler is None:
                suffix = os.path.splitext(key)[1]
                if suffix in self.sidecar_suffixes | self.simulink_doc_suffixes:
                    loose.append((key, path, ref, st))
                continue
            if handler.blocks and self.sources.includes(ref):
                simulink_stems.add(os.path.splitext(key)[0])
            if self.sidecars_only or not self.sources.includes(ref):
                continue
            if _is_link(path) and self.outside(path, ref):
                continue
            self.index_file(handler, path, ref, st)
            mod.members.append((os.path.splitext(key)[0], ref))
        for key, path, ref, st in loose:
            stem, suffix = os.path.splitext(key)
            simulink_doc = (
                suffix in self.simulink_doc_suffixes and stem in simulink_stems
            )
            if not (simulink_doc or (sidecars and suffix in self.sidecar_suffixes)):
                continue
            if not self.sources.includes(ref) or (
                _is_link(path) and self.outside(path, ref)
            ):
                continue
            record = {"reference": ref, "mtime": st.st_mtime_ns, "size": st.st_size}
            if simulink_doc:
                self.out.simulink_docs[path] = record
            else:
                self.out.sidecars[path] = record
        if denied:
            _warn(
                "parse_error",
                f"{mod.ref}: {len(denied)} entries cannot be accessed "
                f"({denied[0].strerror or denied[0]}); they are not documented.",
            )
        return True

    def index_file(self, handler, path, ref, st):
        key = (path, st.st_mtime_ns, st.st_size)
        old = self.old_index.get(path)
        if (
            old is not None
            and (old["mtime"], old["size"]) == key[1:]
            and not old["unreadable"]
        ):
            kind, problems, unreadable = old["type"], old["warnings"], False
            help_only = old["help_only"]
            if help_only:
                # A MEX file may have been added or removed since.
                kind = FUNCTION if has_mex_file(path) else SCRIPT
        else:
            text = None
            try:
                kind, text, problems = handler.read(path, self.encoding)
                unreadable = False
            except OSError as err:
                kind, unreadable = UNKNOWN, True
                problems = [("parse_error", failure_message(err), None)]
            help_only = kind in (SCRIPT, FUNCTION) and text is not None
            help_only = help_only and is_help_only(cast(str, text))
            if text is not None:
                self.out.text_cache[key] = text
        self.out.index[path] = {
            "reference": ref,
            "type": kind,
            "mtime": key[1],
            "size": key[2],
            "warnings": problems,
            "unreadable": unreadable,
            "help_only": help_only,
        }
        for subtype, message, row in problems:
            _warn_file(ref, path, subtype, message, row)


def _index_shape(data):
    """Return what names and lookups depend on: the folders, each file's
    reference and type, and which Simulink documentation files exist.
    """
    files = {path: (r["reference"], r["type"]) for path, r in data["index"].items()}
    folders = frozenset(r for r in data["entities_table"] if r[-1:] == "/")
    return files, folders, frozenset(data["simulink_docs"])


def analyze(app):
    """Index stage (``builder-inited``): find, read and classify the sources.

    Files are parsed later, when a document needs them (``resolve``).
    """
    env = app.env
    dom = env.get_domain("mat")
    data = dom.data
    # Records and parses of the previous build are reused for unchanged files
    # unless the config changed.
    reuse = env.config_status == CONFIG_OK
    old_index = dict(data["index"]) if reuse else {}
    old_shape = _index_shape(data) if reuse else None
    if not reuse:
        data["parse_cache"].clear()
        data["parse_warnings"].clear()
    data["index"].clear()
    data["sidecars"].clear()
    data["simulink_docs"].clear()
    data["matlab_names"].clear()
    dom.entities_table.clear()
    dom.reset_sources()
    MatModuleAnalyzer.cache.clear()
    MatObject.encoding = env.config.matlab_src_encoding
    MatObject.sphinx_env = env
    MatObject.sphinx_app = app

    settings = IndexSettings.from_config(env.config, env.srcdir)
    if settings is None:
        logger.debug("[sphinxcontrib-matlabdomain] no project root, skipping parsing.")
    else:
        MatObject.basedir = settings.root
        source_index = build_index(settings, old_index)
        data["index"].update(source_index.index)
        data["sidecars"].update(source_index.sidecars)
        data["simulink_docs"].update(source_index.simulink_docs)
        if "myst_parser" not in app.extensions and any(
            path.endswith(".md") for path in source_index.simulink_docs
        ):
            raise ConfigError(
                "Simulink documentation files in Markdown (.md) need myst_parser in "
                "extensions, or leave '.md' out of matlab_simulink_doc_suffixes."
            )
        data["matlab_names"].update(source_index.matlab_names)
        dom.entities_table.update(source_index.entities)
        dom.text_cache.update(source_index.text_cache)

    keys = {(path, r["mtime"], r["size"]) for path, r in data["index"].items()}
    for cache in (data["parse_cache"], data["parse_warnings"]):
        for key in [k for k in cache if k not in keys]:
            del cache[key]
    dom.index_changed = old_shape is not None and old_shape != _index_shape(data)


def outdated_docs(app, env, added, changed, removed):  # noqa: ARG001
    """``env-get-outdated``: documents that used a source file that changed,
    and, when files or folders were added, removed or changed type, every
    document that looked up sources.
    """
    dom = env.get_domain("mat")
    index = dom.data["index"]

    def stale(used):
        return any(
            (record := index.get(path)) is None
            or (record["mtime"], record["size"]) != key
            for path, key in used.items()
        )

    return [
        docname
        for docname, used in dom.data["doc_sources"].items()
        if dom.index_changed or stale(used)
    ]


def note_read_docs(app, env, docnames):  # noqa: ARG001
    """``env-before-read-docs``: remember the documents this build reads."""
    env.get_domain("mat").read_docnames = list(docnames)


def warn_parsed_sources(app, env):  # noqa: ARG001
    """``env-updated``: parse-stage warnings, once per file that a document
    read in this build used, in index order (serial and parallel builds).
    """
    dom = env.get_domain("mat")
    data = dom.data
    used = set()
    for docname in dom.read_docnames:
        used.update(data["doc_sources"].get(docname, ()))
    for path, record in data["index"].items():
        if path in used:
            key = (path, record["mtime"], record["size"])
            for warning in data["parse_warnings"].get(key, ()):
                _warn(*warning)


def _scope(folder):
    """Folder a MATLAB name in ``folder`` (a folder reference) is visible from.

    The folder above its ``@class`` and ``+namespace`` folders; for
    ``private/`` the folder holding it.
    """
    parts = [] if folder == ROOT_REFERENCE else folder.rstrip("/").split("/")
    if parts and parts[-1] == "private":
        parts.pop()
    else:
        parts = parts[: next((i for i, p in enumerate(parts) if p[:1] == "@"), None)]
        while parts and parts[-1][:1] == "+":
            parts.pop()
    return "/".join(parts) + "/" if parts else ROOT_REFERENCE


# Stands in for the project root (a plain folder), so folders above the root
# never change a MATLAB name.
_ROOT_PART = "root"


def _naming_folder(reference):
    return os.path.normpath(os.path.join(_ROOT_PART, folder_of(reference)))


def name_sources(source_index):
    """Name every discovered file and folder the MATLAB way (``form_matlab_name``).

    Sets ``matlab_name`` (``None`` if MATLAB cannot call it), ``private`` and
    ``scope`` (see ``_scope``) on each ``index`` record and folder entity, and
    fills ``matlab_names``. Files MATLAB cannot call, except below
    ``private/``, get one ``mat.not_callable`` warning each.
    """
    settings = source_index.settings
    version = settings.matlab_version
    mat_naming.validate_matlab_version(version)
    namelengthmax = mat_naming.default_namelengthmax(version)
    matlab_names = source_index.matlab_names
    for path, record in source_index.index.items():
        ref = record["reference"]
        naming = getattr(handler_by_extension(path), "naming", "code")
        # a .slx that is no Simulink file (an LFS pointer) is nothing to call
        if naming is None or (naming == "model" and record["type"] == UNKNOWN):
            record.update(matlab_name=None, private=False, scope=None)
            continue
        filename = os.path.basename(path)
        if naming == "model":
            name = mat_naming.form_model_name(
                _naming_folder(ref), filename, namelengthmax, version
            )
        else:
            name = mat_naming.form_matlab_name(
                _naming_folder(ref),
                filename,
                record["type"] == "class",
                namelengthmax,
                version,
            )
        matlab_name = mat_naming.canonical_name(name) if name else None
        private = is_private_reference(ref)
        scope = _scope(folder_of(ref)) if name is not None else None
        record.update(matlab_name=matlab_name, private=private, scope=scope)
        if name is None:
            if naming == "model":
                reason = mat_naming.model_not_callable_reason(
                    _naming_folder(ref), filename, namelengthmax
                )
            elif not private and not is_hidden(ref):
                reason = mat_naming.not_callable_reason(
                    _naming_folder(ref),
                    filename,
                    record["type"] == "class",
                    namelengthmax,
                    version,
                )
            else:
                continue
            logger.warning(
                "[sphinxcontrib-matlabdomain] %s is not callable in MATLAB %s "
                "(%s); it is documented by its path reference.",
                ref,
                version,
                reason,
                type="mat",
                subtype="not_callable",
            )
            continue
        if matlab_name == name.pseudo_fullname:
            matlab_names.setdefault(matlab_name, []).append(ref)

    # ``entities`` holds the folders only (files are parsed on first use).
    for ref, entity in source_index.entities.items():
        namespace = mat_naming.folder_namespace(
            _naming_folder(ref), namelengthmax, version
        )
        entity.matlab_name = namespace
        entity.private = is_private_reference(ref)
        entity.scope = _scope(ref) if namespace is not None else None
        if namespace is not None:
            matlab_names.setdefault(namespace, []).append(ref)


_TREE_SITTER_TYPES = (Node, Tree, Parser)


def _undecodable(name):
    """Return True for a file name ``os.listdir`` could not decode (POSIX bytes)."""
    try:
        name.encode("utf-8")
    except UnicodeEncodeError:
        return True
    return False


def placeholder(kind, name, folder) -> Any:
    """Empty object of the index type ``kind`` for a file that failed to parse."""
    if kind == "application":
        return MatApplication(name, folder, "")
    if kind in SIMULINK_TYPES:
        return SIMULINK_TYPES[kind](name, folder, None)
    cls = {"class": MatClass, "function": MatFunction}.get(kind, MatScript)
    obj = cls.__new__(cls)
    MatObject.__init__(obj, name)
    obj.module = folder
    obj.docstring = None
    obj.line = None
    if cls is MatClass:
        obj.attrs, obj.bases, obj.properties = {}, [], {}
        obj.methods, obj.enumerations, obj.rem_tks = {}, {}, None
        obj.declarations, obj.events = {}, {}
    elif cls is MatFunction:
        obj.retv, obj.args, obj.rem_tks = {}, {}, None
        obj.name_value = {}
    else:
        obj.tokens = None
    return obj


def failure_message(err):
    """Warning text for a file that could not be read or parsed."""
    if isinstance(err, OSError):
        return (
            f"cannot be read ({err.strerror or err}); it is documented without content."
        )
    return (
        f"cannot be parsed ({type(err).__name__}: {err}); it is documented "
        "without content."
    )


def _restore_matobject(class_name):
    cls = globals()[class_name]
    return cls.__new__(cls)


class MatObject:
    """Base MATLAB object to which all others are subclassed.

    :param name: Name of MATLAB object.
    :type name: str

    MATLAB objects can be :class:`MatModule`, :class:`MatFunction`,
    :class:`MatApplication` or :class:`MatClass`.
    :class:`MatModule` are just folders that define a pseudo
    namespace for :class:`MatFunction`, :class:`MatApplication`
    and :class:`MatClass` in that folder.
    :class:`MatFunction` and :class:`MatClass` must begin with either
    ``function`` or ``classdef`` keywords.
    :class:`MatApplication` must be a ``.mlapp`` file.
    """

    basedir: str | None = None
    encoding = None
    sphinx_env = None
    sphinx_app: Any = None
    #: index type (the handler's ``classify()``), tree-sitter's type (``.m``
    #: only) and whether the file has code
    source_type: str | None = None
    parsed_type: str | None = None
    has_code = True
    #: ``(subtype, message, row or None)`` found while parsing; the build
    #: warns them through ``parse_warnings``
    source_warnings: list[tuple[str, str, int | None]] | tuple = ()
    #: the file could not be read (an empty placeholder that is not cached)
    unreadable = False
    #: one-based file line of the first line of the help in a code file (None:
    #: no help, or help that is not on a file line)
    docstring_line: int | None = None
    ref: str
    matlab_name: str
    private: bool
    scope: str

    def __init__(self, name):
        #: name of MATLAB object
        self.name = name

    def ref_role(self):
        """Return the role used for references and automatic links"""
        return "ref"

    def __reduce_ex__(self, protocol):
        # The ``__module__`` property breaks pickle's default class lookup, so
        # restore by class name. Live tree-sitter objects are dropped.
        state = {
            k: None if isinstance(v, _TREE_SITTER_TYPES) else v
            for k, v in self.__dict__.items()
        }
        return (_restore_matobject, (type(self).__name__,), state)

    @property
    def __name__(self):
        return self.name

    def __repr__(self):
        # __str__() method not required, if not given, then __repr__() used
        return f'<{self.__class__.__name__}: "{self.name}">'

    def getter(self, name, *defargs) -> Any:
        if name == "__name__":
            return self.__name__
        if defargs:
            return defargs[0]
        logger.debug(
            '[sphinxcontrib-matlabdomain] Warning attribute "%s" was not found in %s.',
            name,
            self,
        )
        return None

    @staticmethod
    def matlabify(objname) -> Any:
        """Make a MatObject.

        :param objname: Path of the object below the project root
            (:attr:`MatObject.basedir`) with ``/`` separators: a folder
            (``"target/+package"``), a file (``"target/+package/ClassBar.m"``)
            or a file without its extension (``.m`` is tried before
            ``.mlapp``). ``""`` is the project root.
        :type objname: str

        Every object gets its path reference as ``ref``. In a build, only
        discovered objects are found; files are parsed on first use.
        """
        if objname is None:
            return None
        rel = unicodedata.normalize("NFC", objname.strip("/"))
        if rel in ("", "."):
            return resolve(_domain(), ROOT_REFERENCE)
        return _resolve_path(_domain(), rel)

    @staticmethod
    def parse_mfile(mfile, name, path, encoding=None, text=None) -> Any:
        """Parse an ``.m`` file with tree-sitter.

        :param mfile: Full path of mfile.
        :type mfile: str
        :param name: Name of :class:`MatObject`.
        :type name: str
        :param path: Folder reference of the folder containing :class:`MatObject`.
        :type path: str
        :param encoding: ``matlab_src_encoding``; ``None`` follows MATLAB
            (see ``decode_source``).
        :type encoding: str
        :param text: The decoded file content, if already read (the index
            stage reported its decoding problems); ``None`` reads the file.
        :type text: str
        :returns: :class:`MatObject` that represents the type of mfile.

        The type is ``classify()`` of the text (``source_type``). The object is
        built from what tree-sitter parsed (``parsed_type``); the two differ
        only for invalid MATLAB (see ``parse_warnings``). If the parser fails,
        the object is an empty ``placeholder`` of the ``classify()`` type.
        Problems are recorded in ``source_warnings``.
        """
        problem = None
        if text is None:
            with open(mfile, "rb") as code_f:
                text, problem = decode_source(code_f.read(), encoding)
        warnings: list[tuple[str, str, int | None]] = (
            [] if problem is None else [("encoding", *problem)]
        )
        source_type = classify(mfile, text)

        # tree-sitter reads UTF-8; help text and line numbers assume LF, and
        # MATLAB also ends lines at CRLF and a lone CR
        code = text.encode("utf-8").replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        tree = Parser(ML_LANG).parse(code)

        modname = path  # folder reference

        parsed = parsed_type(tree.root_node)
        try:
            if parsed == "class":
                logger.debug(
                    "[sphinxcontrib-matlabdomain] parsing classdef %s from %s.",
                    name,
                    modname,
                )
                obj = MatClass(name, modname, tree.root_node, "utf-8")
            elif parsed == "function":
                logger.debug(
                    "[sphinxcontrib-matlabdomain] parsing function %s from %s.",
                    name,
                    modname,
                )
                obj = MatFunction(name, modname, tree.root_node, "utf-8")
            else:
                obj = MatScript(name, modname, tree.root_node, "utf-8")
        except Exception as err:  # one bad file must not stop the build
            obj = placeholder(source_type, name, modname)
            error = first_error(tree.root_node)
            message = failure_message(err)
            row = None
            if error is not None:
                row, column = error
                message += f" First syntax error: line {row + 1}, column {column + 1}."
            warnings.append(("parse_error", message, row))
            parsed = None
        else:
            decl_name = None
            if parsed == "function":
                decl_name = cast(Node, declaration(tree.root_node)).child_by_field_name(
                    "name"
                )
            if decl_name is not None and decl_name.type == "property_name":
                warnings.append(
                    (
                        "invalid_matlab",
                        f"declares the dotted function name "
                        f"{cast(bytes, decl_name.text).decode('utf-8', 'replace')}; "
                        "MATLAB allows dotted names only in a classdef file. It is "
                        "documented under its file name.",
                        get_row(decl_name.start_point),
                    )
                )
            parsed = parsed or "script"
        if source_type == "function" and parsed == "script" and is_help_only(text):
            # a help file of a MEX function: its comments are the help
            func = placeholder("function", name, modname)
            func.docstring = obj.docstring
            func.docstring_line = obj.docstring_line
            obj, parsed = func, "function"
        obj.source_type = source_type
        obj.parsed_type = parsed
        obj.has_code = source_type != "script" or bool(first_line_of_code(text))
        obj.source_warnings = warnings
        return obj

    @staticmethod
    def parse_mlappfile(mlappfile, name, path):
        """Use ZipFile to read the metadata/appMetadata.xml file and
        the metadata/coreProperties.xml file description tags.
        Parses XML content using ElementTree.

        :param mlappfile: Full path of ``.mlapp`` file.
        :type mlappfile: str
        :param name: Name of :class:`MatApplication`.
        :type name: str
        :param path: Folder reference of the folder containing :class:`MatApplication`.
        :type path: str
        :returns: :class:`MatApplication` representing the application.
        """
        # Read contents of meta-data file
        # This might change in different Matlab versions
        # Note: `code` is a verbatim copy of the MATLAB source inside the App
        #       Variable `codeText` will contain the source.
        with ZipFile(mlappfile, "r") as mlapp:
            meta = ET.fromstring(mlapp.read("metadata/appMetadata.xml"))
            core = ET.fromstring(mlapp.read("metadata/coreProperties.xml"))

        metaNs = {"ns": "http://schemas.mathworks.com/appDesigner/app/2017/appMetadata"}
        coreNs = {
            "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcmitype": "http://purl.org/dc/dcmitype/",
            "dcterms": "http://purl.org/dc/terms/",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }

        coreDesc = core.find("dc:description", coreNs)
        metaDesc = meta.find("ns:description", metaNs)

        doc = []
        if coreDesc is not None and coreDesc.text is not None:
            doc.append(coreDesc.text)
        if metaDesc is not None and metaDesc.text is not None:
            doc.append(metaDesc.text)
        docstring = "\n\n".join(doc)

        modname = path  # folder reference

        return MatApplication(name, modname, docstring)

    @staticmethod
    def parse_simulink(path, name, folder) -> Any:
        """Read a Simulink file (``.slx``, ``.mdl``, exported ``.xml``).

        :returns: :class:`MatModel`, :class:`MatLibrary` or
            :class:`MatSubsystemFile`.
        :raises SimulinkFileError: for a file that is not a readable
            Simulink file.
        """
        diagram = read_diagram(path)
        return SIMULINK_TYPES[diagram.kind](name, folder, diagram)


# TODO: get docstring and __all__ from contents.m if exists
class MatModule(MatObject):
    """All MATLAB modules are packages. A package is a folder that serves as the
    namespace for any :class:`MatObjects` in the package folder. Sphinx will
    treats objects without a namespace as builtins, so all MATLAB projects
    should be packaged in a folder so that they will have a namespace. This
    can also be accomplished by using the MATLAB +folder package scheme.

    :param name: Name of :class:`MatObject`.
    :type name: str
    :param path: Path of folder containing :class:`MatObject`.
    :type path: str
    :param package: Folder reference (``target/+package/``; ``./`` for the root).
    :type package: str
    """

    def __init__(self, name, path, package):
        super().__init__(name)
        #: Path to module on disk, path to package's __init__.py
        self.path = path
        #: folder reference
        self.package = package
        self.ref = package
        #: ``(name, reference)`` of its files (name without extension) and
        #: folders in listing order, set by the index stage
        self.members = None

    def ref_role(self):
        """Return the role used for references and automatic links"""
        return "folder"

    def member_refs(self):
        """``(name, reference)`` of the files and folders in the folder."""
        if self.members is None:  # detached use: no index stage
            self.members = []
            try:
                keys = os.listdir(self.path)
            except OSError:
                keys = []
            for key in keys:
                path = os.path.join(self.path, key)
                ref = join_reference(self.ref, unicodedata.normalize("NFC", key))
                if os.path.isdir(path):
                    if not skipped_folder(path, key) and not file_like_folder(key):
                        self.members.append((key, f"{ref}/"))
                elif handler_for(path) is not None:
                    self.members.append((os.path.splitext(key)[0], ref))
        return self.members

    def safe_getmembers(self):
        """``(name, object)`` of the files and folders in the folder; every
        file is parsed (or taken from the parse cache).
        """
        dom = _domain()
        return [(name, resolve(dom, ref)) for name, ref in self.member_refs()]

    @property
    def __doc__(self):
        return None

    @property
    def __all__(self):
        return self.safe_getmembers()

    @property
    def __path__(self):
        return [self.path]

    @property
    def __file__(self):
        return self.path

    @property
    def __package__(self):
        return self.package

    def getter(self, name, *_defargs) -> Any:
        """:class:`MatModule` ``getter`` method to get attributes."""
        if name == "__name__":
            return self.__name__
        elif name == "__doc__":
            return self.__doc__
        elif name == "__all__":
            return self.__all__
        elif name == "__file__":
            return self.__file__
        elif name == "__path__":
            return self.__path__
        elif name == "__package__":
            return self.__package__
        elif name == "__module__":
            logger.debug(
                "[sphinxcontrib-matlabdomain] mod %s is a package "
                "and does not have __module__.",
                self,
            )
            return None
        else:
            # A file before a same-named folder.
            refs = [ref for n, ref in self.member_refs() if n == name]
            dom = _domain()
            if refs:
                return resolve(dom, next((r for r in refs if r[-1:] != "/"), refs[0]))
            # A path below the folder, e.g. with its extension (``f.m``).
            return _resolve_path(dom, join_reference(self.ref, name))


class MatFunction(MatObject):
    """A MATLAB function.

    :param name: Name of :class:`MatObject`.
    :type name: str
    :param modname: Name of folder containing :class:`MatObject`.
    :type modname: str
    :param tokens: List of tokens parsed from mfile by Pygments.
    :type tokens: list
    """

    def __init__(self, name, modname, tokens, encoding):
        super().__init__(name)
        parsed_function = MatFunctionParser(tokens, encoding)
        #: Path of folder containing :class:`MatObject`.
        self.module = modname
        #: docstring
        self.docstring = parsed_function.docstring
        self.docstring_line = parsed_function.docstring_line
        #: output args
        self.retv = parsed_function.retv
        #: input args
        self.args = parsed_function.args
        #: ``opts.Name`` -> help of each name-value argument
        self.name_value = parsed_function.name_value
        #: line of the declaration (one-based)
        self.line = parsed_function.line
        #: remaining tokens after main function is parsed
        self.rem_tks = None

    def ref_role(self):
        """Return the role used for references and automatic links"""
        return "func"

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __module__(self):
        return self.module

    def getter(self, name, *defargs) -> Any:
        if name == "__name__":
            return self.__name__
        elif name == "__doc__":
            return self.__doc__
        elif name == "__module__":
            return self.__module__
        else:
            return super().getter(name, *defargs)


class MatClass(MatObject):
    """A MATLAB class definition.

    :param name: Name of :class:`MatObject`.
    :type name: str
    :param path: Path of folder containing :class:`MatObject`.
    :type path: str
    :param tokens: List of tokens parsed from mfile by Pygments.
    :type tokens: list
    """

    def __init__(self, name, modname, tokens, encoding):
        super().__init__(name)
        parsed_class = MatClassParser(tokens, encoding)
        #: Path of folder containing :class:`MatObject`.
        self.module = modname
        #: dictionary of class attributes
        self.attrs = parsed_class.attrs
        #: list of class superclasses
        self.bases = parsed_class.supers
        #: docstring
        self.docstring = parsed_class.docstring
        self.docstring_line = parsed_class.docstring_line
        #: line of the declaration (one-based)
        self.line = parsed_class.line
        #: dictionary of class properties
        self.properties = parsed_class.properties
        #: dictionary of class methods
        self.methods = {
            name: MatMethod(name, parsed_fun, modname, self)
            for (name, parsed_fun) in parsed_class.methods.items()
        }
        #: attributes of the methods declared without a body, by name
        self.declarations = parsed_class.declarations
        #:
        self.enumerations = parsed_class.enumerations
        #: ``{name: {"attrs", "docstring", "line"}}`` of the events
        self.events = parsed_class.events
        #: remaining tokens after main class definition is parsed
        self.rem_tks = None

    def ref_role(self):
        """Return the role used for references and automatic links"""
        return "class"

    def fullname(self, env):  # noqa: ARG002
        """Return the path reference of the class, for use as a link target"""
        return self.ref

    def link(self, env, name=None):  # noqa: ARG002
        """Return a link for the class object"""
        title = name or getattr(self, "matlab_name", None) or self.ref
        return f":mat:class:`{title} <{self.ref}>`"

    @property
    def __module__(self):
        return self.module

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __bases__(self):
        bases_ = dict.fromkeys(list(self.bases))  # make copy of bases
        dom = _domain()
        folder = folder_of(self.ref) if getattr(self, "ref", None) else None
        for base in bases_:
            found = find_source(
                dom, base, folder, accept=lambda obj: isinstance(obj, MatClass)
            )
            if len(found) == 1:
                bases_[base] = found[0][1]

        return bases_

    def getter(self, name, *defargs) -> Any:
        """:class:`MatClass` ``getter`` method to get attributes."""
        if name == "__name__":
            return self.__name__
        elif name == "__doc__":
            return self.__doc__
        elif name == "__module__":
            return self.__module__
        elif name == "__bases__":
            return self.__bases__
        elif name in self.properties:
            return MatProperty(name, self, self.properties[name])
        elif name in self.enumerations:
            return MatEnumeration(name, self, self.enumerations[name])
        elif name in self.methods:
            return self.methods[name]
        elif name in self.events:
            return MatEvent(name, self, self.events[name])
        elif name == "__dict__":
            objdict = {pn: self.getter(pn) for pn in self.properties}
            objdict.update(self.methods)
            objdict.update({en: self.getter(en) for en in self.enumerations})
            objdict.update({ev: self.getter(ev) for ev in self.events})
            return objdict
        else:
            return super().getter(name, *defargs)


class MatProperty(MatObject):
    def __init__(self, name, cls, attrs):
        super().__init__(name)
        self.cls = cls
        self.attrs = attrs["attrs"]
        self.default = attrs["default"]
        self.docstring = attrs["docstring"]
        self.docstring_line = attrs.get("docstring_line")
        self.size = attrs["size"]
        self.type = attrs["type"]
        self.validators = attrs["validators"]

    def ref_role(self):
        """Return the role used for references and automatic links"""
        return "attr"

    @property
    def __module__(self):
        return self.cls.module

    @property
    def __doc__(self):
        return self.docstring


class MatEnumeration(MatObject):
    def __init__(self, name, cls, attrs):
        super().__init__(name)
        self.cls = cls
        self.docstring = attrs["docstring"]
        self.docstring_line = attrs.get("docstring_line")
        #: constructor arguments (``Red (1, 0, 0)``), or None
        self.args = attrs.get("args")

    def ref_role(self):
        """Return the role used for references and automatic links"""
        return "enum"

    @property
    def __module__(self):
        return self.cls.module

    @property
    def __doc__(self):
        return self.docstring


class MatEvent(MatObject):
    def __init__(self, name, cls, attrs):
        super().__init__(name)
        self.cls = cls
        self.attrs = attrs["attrs"]
        self.docstring = attrs["docstring"]
        self.docstring_line = attrs.get("docstring_line")

    def ref_role(self):
        """Return the role used for references and automatic links"""
        return "event"

    @property
    def __module__(self):
        return self.cls.module

    @property
    def __doc__(self):
        return self.docstring


class MatMethod(MatFunction):
    from_class_folder: bool

    def __init__(self, name, parsed_function, modname, cls):
        self.name = name
        #: Path of folder containing :class:`MatObject`.
        self.module = modname
        #: docstring
        self.docstring = parsed_function.docstring
        self.docstring_line = parsed_function.docstring_line
        #: output args
        self.retv = parsed_function.retv
        #: input args
        self.args = parsed_function.args
        self.name_value = parsed_function.name_value
        self.line = parsed_function.line
        self.cls = cls
        self.attrs = parsed_function.attrs

    def ref_role(self):
        """Return the role used for references and automatic links"""
        return "meth"

    @property
    def __module__(self):
        return self.module

    @property
    def __doc__(self):
        return self.docstring


class MatScript(MatObject):
    def __init__(self, name, modname, tks, encoding):
        super().__init__(name)
        parsed_script = MatScriptParser(tks, encoding)
        #: Path of folder containing :class:`MatScript`.
        self.module = modname
        #: List of tokens parsed from mfile by Pygments.
        self.tokens = tks
        #: docstring
        self.docstring = parsed_script.docstring
        self.docstring_line = parsed_script.docstring_line

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __module__(self):
        return self.module


class MatApplication(MatObject):
    """Representation of the documentation in a Matlab Application.

    :param name: Name of :class:`MatObject`.
    :type name: str
    :param modname: Name of folder containing :class:`MatObject`.
    :type modname: str
    :param desc: Summary and description string.
    :type desc: str
    """

    def __init__(self, name, modname, desc):
        super().__init__(name)
        #: Path of folder containing :class:`MatApplication`.
        self.module = modname
        #: docstring
        self.docstring = desc

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __module__(self):
        return self.module


class MatSimulinkFile(MatObject):
    """A Simulink file: model, library or subsystem file (S5 documents them).

    :param name: File name without extension.
    :param modname: Folder reference of its folder.
    :param diagram: What ``mat_simulink.read_diagram`` read; None for a
        placeholder.
    """

    def __init__(self, name, modname, diagram):
        super().__init__(name)
        self.module = modname
        self.diagram = diagram
        #: the description saved in the file, else the system mask's
        self.docstring = None
        if diagram is not None:
            mask = diagram.system_mask
            self.docstring = diagram.description or (mask.description if mask else "")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # a subclass's own ``__doc__`` and ``__module__`` hide the properties
        for name in ("__doc__", "__module__"):
            type.__setattr__(cls, name, MatSimulinkFile.__dict__[name])

    #: object type: the directive and role
    objtype = ""

    def ref_role(self):
        return self.objtype

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __module__(self):
        return self.module


class MatModel(MatSimulinkFile):
    """A Simulink model file."""

    objtype = "simulink_model"


class MatSubsystemFile(MatSimulinkFile):
    """A Simulink subsystem file (the target of a Subsystem Reference)."""

    objtype = "simulink_subsystem_reference"


class MatLibrary(MatSimulinkFile):
    """A Simulink library; its members are the blocks of the library walk,
    by their path below the library.
    """

    objtype = "simulink_library"

    def getter(self, name, *defargs) -> Any:
        blocks = self.diagram.library_blocks if self.diagram is not None else ()
        for block in blocks:
            if block.path == name:
                return MatBlock(block, self)
        return super().getter(name, *defargs)


class MatBlock(MatObject):
    """A block of a library found by the library walk.

    :param block: The ``mat_simulink.LibraryBlock``.
    :param library: The :class:`MatLibrary` that holds it.
    """

    def __init__(self, block, library):
        super().__init__(block.path)
        self.block = block
        self.library = library
        #: it has a section in the library's documentation file
        self.has_doc_section = False
        self.module = library.module
        self.docstring = block.description or (
            block.mask.description if block.mask else ""
        )
        if hasattr(library, "ref"):
            self.ref = f"{library.ref}/{block.path}"

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __module__(self):
        return self.module


#: Simulink index type -> object class
SIMULINK_TYPES = {
    "model": MatModel,
    "library": MatLibrary,
    "subsystem": MatSubsystemFile,
}
#: object type (directive and role name) -> object class
SIMULINK_CLASSES = {
    "simulink_model": MatModel,
    "simulink_library": MatLibrary,
    "simulink_subsystem_reference": MatSubsystemFile,
    "simulink_library_block": MatBlock,
}


class MatcodeError(Exception):
    """A folder reference that names no discovered folder."""


class MatModuleAnalyzer:
    """Stands in for Sphinx's ``ModuleAnalyzer`` in autodoc: the source order
    of a folder's files and of its classes' members (``tagorder``).
    """

    # folder reference -> analyzer, or the MatcodeError of an unknown folder
    cache = {}

    @classmethod
    def for_module(cls, modname):
        entry = cls.cache.get(modname)
        if entry is None:
            mod = resolve(_domain(), modname)
            if isinstance(mod, MatModule):
                entry = cls(mod)
            else:
                entry = MatcodeError(f"error importing {modname!r}")
            cls.cache[modname] = entry
        if isinstance(entry, MatcodeError):
            raise entry
        return entry

    def __init__(self, mod):
        self.modname = mod.ref
        # autodoc's ``get_sourcename`` names the source with it
        self.srcname = mod.path
        self.tagorder = _TagOrder(mod)


class _TagOrder:
    """Order of a folder's files (``name``, by name: a folder has no source
    order) and source order of a class's members (``Class.member``), for
    ``:member-order: bysource``. A class is parsed only when one of its
    members is asked for.
    """

    def __init__(self, mod):
        self.files = sorted(
            (name, ref) for name, ref in mod.member_refs() if ref[-1:] != "/"
        )
        #: file name -> position (the last file with that name)
        self.order = {name: i for i, (name, _) in enumerate(self.files)}
        self._classes = {}

    def class_members(self, stem):
        """Member names (``__dict__``) of the classes in the files named ``stem``."""
        if stem not in self._classes:
            members = {}
            for name, ref in self.files:
                if name == stem:
                    obj = resolve(_domain(), ref)
                    if isinstance(obj, MatClass):
                        members.update(obj.getter("__dict__"))
            self._classes[stem] = list(members)
        return self._classes[stem]

    def get(self, tag, default=None):
        if tag in self.order:
            return self.order[tag]
        stem, dot, member = tag.partition(".")
        names = self.class_members(stem) if dot else []
        return names.index(member) if member in names else default

    def __len__(self):
        # The default position for members without one: after all others.
        return sys.maxsize
