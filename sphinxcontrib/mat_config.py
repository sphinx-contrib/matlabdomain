"""sphinxcontrib.mat_config.
~~~~~~~~~~~~~~~~~~~~~~~~~

The ``matlab_*`` configuration values in one table. The build registers
them (``setup``) and ``scmd apidoc`` reads ``conf.py`` with the same
defaults and the same checks, so the two always agree.
"""

from __future__ import annotations

import copy

from sphinx.errors import ConfigError

from . import mat_naming, mat_types

_NONE = type(None)
_LIST = (list, tuple)

#: MATLAB's own classes and namespaces, never documented in a project
DEFAULT_EXTERNAL_NAMES = [
    r"handle|dynamicprops",
    r"(matlab|Simulink|event|meta)\..+",
    r"double|single|u?int(8|16|32|64)|logical|char|string|cell|struct",
    r"function_handle|table|timetable|datetime|duration|calendarDuration",
    r"categorical|containers\.Map|dictionary|MException|missing|timeseries",
]

#: name -> (default, rebuild, types); ``()`` checks against the default's type
CONFIG = {
    # Sources. A relative project root is relative to the Sphinx source folder.
    "matlab_src_code_project_root": (None, "env", ()),
    # Globs relative to the project root; [] selects no files.
    "matlab_src_include_patterns": (
        list(mat_types.DEFAULT_INCLUDE_PATTERNS),
        "env",
        _LIST,
    ),
    "matlab_src_exclude_patterns": (
        list(mat_types.DEFAULT_EXCLUSION_PATTERNS),
        "env",
        _LIST,
    ),
    # Sidecar docs: [] is off; e.g. [".md", ".rst"] (plan.md 2.11).
    "matlab_src_sidecar_suffixes": ([], "env", _LIST),
    "matlab_src_encoding": (None, "env", ()),
    "matlab_version": (mat_naming.DEFAULT_MATLAB_VERSION, "env", ()),
    # Rendering and links.
    "matlab_show_property_default_value": (True, "env", ()),
    "matlab_show_property_specs": (True, "env", ()),
    "matlab_auto_link": (None, "env", ()),
    "matlab_class_signature": (False, "env", ()),
    "matlab_add_namespace_names": (True, "env", bool),
    # Regexes of names references to which are text, without a warning.
    "matlab_external_names": (list(DEFAULT_EXTERNAL_NAMES), "html", _LIST),
    # Stable addresses (mat/ref/, mat/name/) and "¶" links to them.
    "matlab_stable_urls": (True, "html", bool),
    # Several objects of one MATLAB name are intended: link to their chooser
    # page, without mat.ambiguous.
    "matlab_link_shadowed_files_to_chooser_pages": (False, "env", bool),
    # Simulink. The sphinx-autobuild address for Help links (make livehtml).
    "matlab_simulink_autobuild_server": (None, "", ()),
    # Metadata shown by default (directive option :metadata:).
    "matlab_simulink_metadata": (["release", "model_version"], "env", _LIST),
    # Suffixes of documentation files next to Simulink files, by priority.
    "matlab_simulink_doc_suffixes": ([".md", ".rst"], "env", _LIST),
    # matlab-api-check: read by the builder only, so no page is read again.
    # Rule -> severity, merged over mat_api_check.DEFAULT_RULES.
    "matlab_api_check_rules": ({}, "", dict),
    "matlab_api_check_ignore_patterns": ([], "", _LIST),
    # None checks every file; a list (or, from -D, a comma-separated str) selects.
    "matlab_api_check_files": (None, "", ()),
    # A text file of selection entries, one per line.
    "matlab_api_check_files_from": (None, "", ()),
    "matlab_api_check_ignore_unmatched": (False, "", bool),
    # Section -> the labels it accepts, replacing the built-in ones.
    "matlab_api_check_section_labels": ({}, "", dict),
    # scmd apidoc (plan.md Section 2.8): read by the CLI only.
    "matlab_apidoc_output_dir": (None, "", (str, _NONE)),
    "matlab_apidoc_separate": (False, "", (bool,)),
    "matlab_apidoc_maxdepth": (4, "", (int,)),
    "matlab_apidoc_tocfile": ("index", "", (str,)),
    "matlab_apidoc_templatedir": (None, "", (str, _NONE)),
    "matlab_apidoc_remove_old": (True, "", (bool,)),
    "matlab_apidoc_group": ("namespace", "", (str,)),
    "matlab_apidoc_page_size": (100, "", (int,)),
    "matlab_apidoc_private": (False, "", (bool,)),
    # Removed: setting one raises ConfigError with the replacement.
    "matlab_src_dir": (None, "env", ()),
    "matlab_keep_package_prefix": (None, "env", ()),
    "matlab_short_links": (None, "env", ()),
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
    for name, (default, rebuild, types) in CONFIG.items():
        add(name, copy.deepcopy(default), rebuild, types)


def typed_value(config, name):
    """``config.<name>``, or ConfigError if its type is not one of the table's."""
    value = getattr(config, name)
    types = CONFIG[name][2]
    if type(value) not in types:
        names = " or ".join("None" if t is _NONE else t.__name__ for t in types)
        raise ConfigError(f"{name} must be {names}, not {value!r}.")
    return value


def check_sources(config, srcdir):
    """ConfigError for a removed value or a bad source setting: the checks
    that the build and ``scmd apidoc`` share.
    """
    removed = [
        f"{name} was removed: {reason}."
        for name, reason in REMOVED.items()
        if getattr(config, name) is not None
    ]
    if removed:
        them = "it" if len(removed) == 1 else "them"
        raise ConfigError(" ".join(removed) + f" Remove {them} from conf.py.")

    sources = mat_types.source_filter(config)
    if config.matlab_src_code_project_root is not None:
        root = mat_types.project_root(config, srcdir)
        mat_types.check_pattern_folders(sources, root)
        if mat_types.sidecar_suffix_list(config.matlab_src_sidecar_suffixes):
            mat_types.sidecar_layout_error(root, srcdir)

    mat_types.check_text_encoding(config.matlab_src_encoding, "matlab_src_encoding")
    try:
        mat_naming.validate_matlab_version(config.matlab_version)
    except ValueError as err:
        raise ConfigError(str(err)) from err
