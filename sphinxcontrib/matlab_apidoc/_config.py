"""sphinxcontrib.matlab_apidoc._config.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``matlab_apidoc_*`` config values (plan.md Section 2.8): read from
``conf.py`` by ``sphinx-matlab-apidoc -c``; the build only registers them.
Each is ``matlab_apidoc_`` + the long flag with ``-`` -> ``_``.
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
}

#: the build's values the CLI reads, with the defaults of ``setup()``
SOURCE_CONFIG = {
    "matlab_src_code_project_root": None,
    "matlab_src_include_patterns": list(DEFAULT_INCLUDE_PATTERNS),
    "matlab_src_exclusion_patterns": list(DEFAULT_EXCLUSION_PATTERNS),
    "matlab_src_page_suffixes": [],
    "matlab_src_encoding": None,
    "matlab_version": mat_naming.DEFAULT_MATLAB_VERSION,
    "matlab_namelengthmax": None,
}


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
