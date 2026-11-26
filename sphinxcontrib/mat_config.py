"""The ``matlab_*`` configuration values in one table.

The build registers them (``setup``) and ``scmd apidoc`` reads ``conf.py``
with the same defaults and the same checks, so the two always agree. Each
row says which runs use the value and how to check it; ``check_values``
checks the values of a run: a run stops for a bad value it uses and warns
once for a bad value that only another run uses.
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
_PAGES = frozenset({PAGES})
_HTML = frozenset({HTML})
_API_CHECK = frozenset({API_CHECK})
_APIDOC = frozenset({APIDOC})
#: who uses a value, for the warning of a run that does not
_USERS = {
    PAGES: "sphinx-build",
    HTML: "HTML builds",
    API_CHECK: "the matlab-api-check builder",
    APIDOC: "scmd apidoc",
}

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


def _maxdepth(value, name):
    # A toctree's :maxdepth: of 0 or less has no limit; -1 is Sphinx's own.
    check_type(value, name)
    if value < 1 and value != -1:
        raise ConfigError(f"{name} must be 1 or more, or -1 for no limit, not {value}.")


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
    "matlab_show_property_default_value": Value(
        True, "env", (bool,), _PAGES, check_type
    ),
    "matlab_show_property_specs": Value(True, "env", (bool,), _PAGES, check_type),
    "matlab_auto_link": Value(None, "env", (), _PAGES, _auto_link),
    "matlab_class_signature": Value(False, "env", (bool,), _PAGES, check_type),
    "matlab_add_namespace_names": Value(True, "env", (bool,), _PAGES, check_type),
    # :inherited-members: works only when this is on (it repeats base help).
    "matlab_inherited_members": Value(False, "env", (bool,), _PAGES, check_type),
    # Regexes of names references to which are text, without a warning.
    "matlab_external_names": Value(
        list(DEFAULT_EXTERNAL_NAMES), "html", _LIST, _PAGES, _external_names
    ),
    # Stable addresses (mat/ref/, mat/name/) and "¶" links to them.
    "matlab_stable_urls": Value(True, "html", (bool,), _HTML, check_type),
    # Several objects of one MATLAB name are intended: link to their chooser
    # page, without mat.ambiguous.
    "matlab_link_shadowed_files_to_chooser_pages": Value(
        False, "env", (bool,), _PAGES, check_type
    ),
    # matlab-api-check: read by the builder only, so no page is read again.
    # Rule -> severity, merged over mat_api_check.DEFAULT_RULES.
    "matlab_api_check_rules": Value(
        {}, "", (dict,), _API_CHECK, mat_api_check.check_rules
    ),
    "matlab_api_check_ignore_patterns": Value(
        [], "", _LIST, _API_CHECK, mat_types.pattern_list
    ),
    # None checks every file; a list (or, from -D, a comma-separated str) selects.
    "matlab_api_check_files": Value(
        None, "", (), _API_CHECK, mat_api_check.check_files
    ),
    # A text file of selection entries, one per line.
    "matlab_api_check_files_from": Value(
        None, "", (), _API_CHECK, mat_api_check.check_files_from
    ),
    "matlab_api_check_ignore_unmatched": Value(
        False, "", (bool,), _API_CHECK, check_type
    ),
    # Section -> the labels it accepts, replacing the built-in ones.
    "matlab_api_check_section_labels": Value(
        {}, "", (dict,), _API_CHECK, mat_api_check.section_labels
    ),
    # scmd apidoc; HTML builds remove the stale pages of the output folder.
    "matlab_apidoc_output_dir": Value(
        None, "", (str, _NONE), _APIDOC | _HTML, check_type
    ),
    "matlab_apidoc_separate": Value(False, "", (bool,), _APIDOC, check_type),
    "matlab_apidoc_maxdepth": Value(4, "", (int,), _APIDOC, _maxdepth),
    "matlab_apidoc_tocfile": Value("index", "", (str,), _APIDOC, _file_name),
    "matlab_apidoc_templatedir": Value(None, "", (str, _NONE), _APIDOC, check_type),
    "matlab_apidoc_remove_old": Value(True, "", (bool,), _APIDOC, check_type),
    "matlab_apidoc_group": Value("namespace", "", (str,), _APIDOC, _apidoc_group),
    "matlab_apidoc_page_size": Value(100, "", (int,), _APIDOC, _page_size),
    "matlab_apidoc_private": Value(False, "", (bool,), _APIDOC, check_type),
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


#: the values a build checks when its builder is known (``builder-inited``)
BUILDER_VALUES = tuple(
    name
    for name, row in CONFIG.items()
    if PAGES not in row.runs and row.runs & {HTML, API_CHECK}
)
#: the values a build checks at ``config-inited``
START_VALUES = tuple(name for name in CONFIG if name not in BUILDER_VALUES)


def _sphinx_warns(value, row):
    """Whether Sphinx's own type check (``check_confval_types``) warns about
    ``value``: not the default's type, a declared type or a common base.
    """
    if row.default is None and not row.types:
        return False
    kind, default = type(value), type(row.default)
    if kind is default or kind in row.types:
        return False
    return not ({*kind.__bases__, kind} & set(default.__bases__)) - {object}


def check_values(config, run, names=START_VALUES + BUILDER_VALUES):
    """Check the values ``names`` for ``run``, the runs a process is (a build:
    ``PAGES``, and ``HTML`` or ``API_CHECK`` for its builder; ``scmd
    apidoc``: ``APIDOC``).

    ConfigError for a removed value that is set and for the first bad value
    that ``run`` uses. Return a message for each bad value that only other
    runs use, to be warned once (``mat.config``).
    In a build, a wrong type of a value it does not use is left to Sphinx's
    own warning.
    """
    removed = [
        f"{name} was removed: {reason}."
        for name, reason in REMOVED.items()
        if name in names and getattr(config, name) is not None
    ]
    if removed:
        them = "it" if len(removed) == 1 else "them"
        raise ConfigError(" ".join(removed) + f" Remove {them} from conf.py.")
    this = "scmd apidoc" if APIDOC in run else "this build"
    problems = []
    for name in names:
        row = CONFIG[name]
        value = getattr(config, name)
        used = row.runs & run
        if row.check is None or (
            not used and PAGES in run and _sphinx_warns(value, row)
        ):
            continue
        try:
            row.check(value, name)
        except ConfigError as err:
            if used:
                raise
            users = " and ".join(_USERS[r] for r in _USERS if r in row.runs)
            problems.append(f"{err} It is used only by {users}; {this} ignores it.")
    return problems


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
