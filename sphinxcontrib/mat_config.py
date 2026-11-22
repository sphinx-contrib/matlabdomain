"""The ``matlab_*`` configuration values in one table.

The build registers them (``setup``) and ``scmd apidoc`` reads ``conf.py``
with the same defaults and the same checks, so the two always agree. Each
row says which runs use the value and how to check it; ``check_values``
checks the values of a run.
"""

from __future__ import annotations

import copy
import os
import re
from collections.abc import Callable
from typing import Any, NamedTuple

from sphinx.errors import ConfigError

from . import mat_api_check, mat_naming, mat_types

_NONE = type(None)
_LIST = (list, tuple)

#: the runs that use a value: every sphinx-build (``PAGES``), HTML builds
#: (``HTML``), ``-b matlab-api-check`` (``API_CHECK``), ``scmd apidoc``
#: (``APIDOC``)
PAGES, HTML, API_CHECK, APIDOC = "pages", "html", "api-check", "apidoc"
#: the source values, which the build and ``scmd apidoc`` share
SOURCES = frozenset({PAGES, APIDOC})
#: what a build checks: the values of any builder
BUILD = frozenset({PAGES, HTML, API_CHECK})

#: MATLAB's own classes and namespaces, never documented in a project
DEFAULT_EXTERNAL_NAMES = [
    r"handle|dynamicprops",
    r"(matlab|Simulink|event|meta)\..+",
    r"double|single|u?int(8|16|32|64)|logical|char|string|cell|struct",
    r"function_handle|table|timetable|datetime|duration|calendarDuration",
    r"categorical|containers\.Map|dictionary|MException|missing|timeseries",
]


class Value(NamedTuple):
    """A row of ``CONFIG``."""

    default: Any
    #: what changing it rebuilds (``app.add_config_value``)
    rebuild: str
    #: the types Sphinx checks; ``()`` checks against the default's type
    types: tuple[type, ...]
    #: the runs that use it
    runs: frozenset[str]
    #: ``check(value, name)``: ConfigError for a bad value; it looks at the
    #: value only (type, allowed values, syntax)
    check: Callable[[Any, str], object] | None = None


def check_type(value, name):
    """ConfigError unless the type of ``value`` is one of the row's types."""
    types = CONFIG[name].types
    if type(value) not in types:
        names = " or ".join("None" if t is _NONE else t.__name__ for t in types)
        raise ConfigError(f"{name} must be {names}, not {value!r}.")


def _project_root(value, name):
    if value is not None and not isinstance(value, str):
        raise ConfigError(f"{name} must be a str or None, not {value!r}.")


def _matlab_version(value, _name):
    try:
        mat_naming.validate_matlab_version(value)
    except ValueError as err:
        raise ConfigError(str(err)) from err


def _auto_link(value, name):
    if value not in (None, "basic", "all"):
        raise ConfigError(f"{name} must be None, 'basic' or 'all', not {value!r}.")


def _external_names(names, option):
    """ConfigError unless ``names`` is a list of valid regular expressions."""
    if isinstance(names, str) or not isinstance(names, _LIST):
        raise ConfigError(f"{option} must be a list, not {names!r}.")
    for pattern in names:
        if not isinstance(pattern, str):
            raise ConfigError(f"{option}: {pattern!r} must be a str.")
        try:
            re.compile(pattern)
        except re.error as err:
            raise ConfigError(
                f"{option}: {pattern!r} is not a regular expression ({err})."
            ) from err


def _autobuild_server(server, option):
    if server is not None and not (
        isinstance(server, str) and server.startswith(("http://", "https://"))
    ):
        raise ConfigError(
            f"{option} must be None or start with http:// or https://, not {server!r}."
        )


def _file_name(value, name):
    check_type(value, name)
    if not value or any(sep in value for sep in "/\\"):
        raise ConfigError(f"{name} {value!r} must be a file name.")


def _apidoc_group(value, name):
    # matlab_apidoc imports this module
    from .matlab_apidoc._generate import GROUPS

    check_type(value, name)
    if value not in GROUPS:
        raise ConfigError(
            f"{name} must be {' or '.join(map(repr, GROUPS))}, not {value!r}."
        )


def _page_size(value, name):
    check_type(value, name)
    if value < 1:
        raise ConfigError(f"{name} must be 1 or more, not {value}.")


#: name -> Value
CONFIG = {
    # Sources. A relative project root is relative to the Sphinx source folder.
    "matlab_src_code_project_root": Value(None, "env", (), SOURCES, _project_root),
    # Globs relative to the project root; [] selects no files.
    "matlab_src_include_patterns": Value(
        list(mat_types.DEFAULT_INCLUDE_PATTERNS),
        "env",
        _LIST,
        SOURCES,
        mat_types.pattern_list,
    ),
    "matlab_src_exclude_patterns": Value(
        list(mat_types.DEFAULT_EXCLUSION_PATTERNS),
        "env",
        _LIST,
        SOURCES,
        mat_types.pattern_list,
    ),
    # Sidecar docs: [] is off; e.g. [".md", ".rst"].
    "matlab_src_sidecar_suffixes": Value(
        [], "env", _LIST, SOURCES, mat_types.sidecar_suffix_list
    ),
    "matlab_src_encoding": Value(
        None, "env", (), SOURCES, mat_types.check_text_encoding
    ),
    "matlab_version": Value(
        mat_naming.DEFAULT_MATLAB_VERSION, "env", (), SOURCES, _matlab_version
    ),
    # Rendering and links.
    "matlab_show_property_default_value": Value(True, "env", (), BUILD),
    "matlab_show_property_specs": Value(True, "env", (), BUILD),
    "matlab_auto_link": Value(None, "env", (), BUILD, _auto_link),
    "matlab_class_signature": Value(False, "env", (), BUILD),
    "matlab_add_namespace_names": Value(True, "env", (bool,), BUILD),
    # :inherited-members: works only when this is on (it repeats base help).
    "matlab_inherited_members": Value(False, "env", (bool,), BUILD, check_type),
    # Regexes of names references to which are text, without a warning.
    "matlab_external_names": Value(
        list(DEFAULT_EXTERNAL_NAMES), "html", _LIST, BUILD, _external_names
    ),
    # Stable addresses (mat/ref/, mat/name/) and "¶" links to them.
    "matlab_stable_urls": Value(True, "html", (bool,), BUILD),
    # Several objects of one MATLAB name are intended: link to their chooser
    # page, without mat.ambiguous.
    "matlab_link_shadowed_files_to_chooser_pages": Value(False, "env", (bool,), BUILD),
    # Simulink. The sphinx-autobuild address for Help links (make livehtml).
    "matlab_simulink_autobuild_server": Value(None, "", (), BUILD, _autobuild_server),
    # Metadata shown by default (directive option :metadata:).
    "matlab_simulink_metadata": Value(
        ["release", "model_version"], "env", _LIST, BUILD
    ),
    # Suffixes of documentation files next to Simulink files, by priority.
    "matlab_simulink_doc_suffixes": Value(
        [".md", ".rst"], "env", _LIST, SOURCES, mat_types.simulink_doc_suffix_list
    ),
    # matlab-api-check: read by the builder only, so no page is read again.
    # Rule -> severity, merged over mat_api_check.DEFAULT_RULES.
    "matlab_api_check_rules": Value({}, "", (dict,), BUILD, mat_api_check.check_rules),
    "matlab_api_check_ignore_patterns": Value(
        [], "", _LIST, BUILD, mat_types.pattern_list
    ),
    # None checks every file; a list (or, from -D, a comma-separated str) selects.
    "matlab_api_check_files": Value(None, "", (), BUILD, mat_api_check.check_files),
    # A text file of selection entries, one per line.
    "matlab_api_check_files_from": Value(
        None, "", (), BUILD, mat_api_check.check_files_from
    ),
    "matlab_api_check_ignore_unmatched": Value(False, "", (bool,), BUILD),
    # Section -> the labels it accepts, replacing the built-in ones.
    "matlab_api_check_section_labels": Value(
        {}, "", (dict,), BUILD, mat_api_check.section_labels
    ),
    # scmd apidoc: read by the CLI only.
    "matlab_apidoc_output_dir": Value(
        None, "", (str, _NONE), frozenset({APIDOC}), check_type
    ),
    "matlab_apidoc_separate": Value(
        False, "", (bool,), frozenset({APIDOC}), check_type
    ),
    "matlab_apidoc_maxdepth": Value(4, "", (int,), frozenset({APIDOC}), check_type),
    "matlab_apidoc_tocfile": Value(
        "index", "", (str,), frozenset({APIDOC}), _file_name
    ),
    "matlab_apidoc_templatedir": Value(
        None, "", (str, _NONE), frozenset({APIDOC}), check_type
    ),
    "matlab_apidoc_remove_old": Value(
        True, "", (bool,), frozenset({APIDOC}), check_type
    ),
    "matlab_apidoc_group": Value(
        "namespace", "", (str,), frozenset({APIDOC}), _apidoc_group
    ),
    "matlab_apidoc_page_size": Value(100, "", (int,), frozenset({APIDOC}), _page_size),
    "matlab_apidoc_private": Value(False, "", (bool,), frozenset({APIDOC}), check_type),
    # Removed: setting one raises ConfigError with the replacement.
    "matlab_src_dir": Value(None, "env", (), SOURCES),
    "matlab_keep_package_prefix": Value(None, "env", (), SOURCES),
    "matlab_short_links": Value(None, "env", (), SOURCES),
}

#: removed value -> what to do instead
REMOVED = {
    "matlab_src_dir": (
        "use matlab_src_code_project_root (relative to the Sphinx source "
        "directory) and, to select files, matlab_src_include_patterns and "
        "matlab_src_exclude_patterns"
    ),
    "matlab_keep_package_prefix": (
        "objects are referenced by path (which keeps '+') and signatures show "
        "MATLAB names (without '+')"
    ),
    "matlab_short_links": "signatures show MATLAB names by default",
}


def add_config_values(add):
    """Register every value with ``add`` (``app.add_config_value`` or
    ``Config.add``), each with a fresh copy of its default.
    """
    for name, row in CONFIG.items():
        add(name, copy.deepcopy(row.default), row.rebuild, row.types)


def check_values(config, run):
    """ConfigError for a removed value that is set, or for the first bad
    value that ``run`` (a set of runs) uses.
    """
    removed = [
        f"{name} was removed: {reason}."
        for name, reason in REMOVED.items()
        if getattr(config, name) is not None
    ]
    if removed:
        them = "it" if len(removed) == 1 else "them"
        raise ConfigError(" ".join(removed) + f" Remove {them} from conf.py.")
    for name, row in CONFIG.items():
        if row.check is not None and row.runs & run:
            row.check(getattr(config, name), name)


def check_sources(config, srcdir):
    """ConfigError for source settings that do not fit the files or each
    other: the checks that the build and ``scmd apidoc`` share, after
    ``check_values``.
    """
    sources = mat_types.source_filter(config)
    root = mat_types.project_root(config, srcdir)
    if root is not None:
        if not os.path.isdir(root):
            raise ConfigError(
                f"matlab_src_code_project_root {root!r} is not a folder. Set it to "
                "the folder of the MATLAB code; a relative path is relative to the "
                "Sphinx source folder."
            )
        mat_types.check_pattern_folders(sources, root)
        if config.matlab_src_sidecar_suffixes:
            mat_types.sidecar_layout_error(root, srcdir)
