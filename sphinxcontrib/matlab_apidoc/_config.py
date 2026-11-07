"""sphinxcontrib.matlab_apidoc._config.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``matlab_apidoc_*`` config values (plan.md Section 2.8): read from
``conf.py`` by ``sphinx-matlab-apidoc``; the build only registers them.
"""

from __future__ import annotations

from sphinx.errors import ConfigError

from .. import mat_naming
from ..mat_types import DEFAULT_EXCLUSION_PATTERNS, DEFAULT_INCLUDE_PATTERNS

_NONE = type(None)

#: name -> (default, types)
APIDOC_CONFIG = {
    "matlab_apidoc_output_dir": (None, (str, _NONE)),
    "matlab_apidoc_separate": (False, (bool,)),
    "matlab_apidoc_maxdepth": (4, (int,)),
    "matlab_apidoc_tocfile": ("index", (str,)),
    "matlab_apidoc_suffix": ("rst", (str,)),
    "matlab_apidoc_templatedir": (None, (str, _NONE)),
    "matlab_apidoc_remove_old": (True, (bool,)),
    "matlab_apidoc_group": ("namespace", (str,)),
    "matlab_apidoc_page_size": (100, (int,)),
    "matlab_apidoc_private": (None, (bool, _NONE)),
}

#: the build's values the CLI reads, with the defaults of ``setup()``
SOURCE_CONFIG = {
    "matlab_src_code_project_root": None,
    "matlab_src_include_patterns": list(DEFAULT_INCLUDE_PATTERNS),
    "matlab_src_exclusion_patterns": list(DEFAULT_EXCLUSION_PATTERNS),
    "matlab_src_sidecar_suffixes": [],
    "matlab_src_encoding": None,
    "matlab_version": mat_naming.DEFAULT_MATLAB_VERSION,
    "matlab_namelengthmax": None,
}


#: the build's other values, which the CLI accepts and ignores
BUILD_ONLY_CONFIG = frozenset(
    {
        "matlab_src_cache_text",
        "matlab_src_dir",
        "matlab_keep_package_prefix",
        "matlab_short_links",
        "matlab_show_property_default_value",
        "matlab_show_property_specs",
        "matlab_auto_link",
        "matlab_class_signature",
        "matlab_add_namespace_names",
        "matlab_external_names",
        "matlab_stable_urls",
        "matlab_document_shadowed_files",
        "matlab_simulink_server",
        "matlab_api_check_enabled",
        "matlab_api_check_rules",
        "matlab_api_check_ignore_patterns",
        "matlab_api_check_files",
        "matlab_api_check_files_from",
        "matlab_api_check_ignore_unmatched",
        "matlab_api_check_section_labels",
    }
)


def add_config_values(app):
    """Register the ``matlab_apidoc_*`` values (rebuild ``''``)."""
    for name, (default, types) in APIDOC_CONFIG.items():
        app.add_config_value(name, default, "", types)


def apidoc_value(config, name):
    """``config.<name>``, or ConfigError if it has the wrong type."""
    value = getattr(config, name)
    types = APIDOC_CONFIG[name][1]
    if type(value) not in types:
        names = " or ".join("None" if t is _NONE else t.__name__ for t in types)
        raise ConfigError(f"{name} must be {names}, not {value!r}.")
    return value
