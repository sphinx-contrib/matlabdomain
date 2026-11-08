"""sphinx-multiproject root configuration: ``PROJECT=alpha`` or ``beta``.

``alpha/conf.py`` and ``beta/conf.py`` also build on their own (the
supported recipe) and are what ``scmd apidoc -c docs/<project>``
reads. sphinx-multiproject 1.0.0 cannot read them on Sphinx 9
(``PROBE_MULTIPROJECT_MODE=file`` shows the failure; on Sphinx 8 it warns
that they set ``extensions``), so by default this file passes their values
through the ``config`` option instead.
"""

import os
import runpy
import sys

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)

from shared_conf import *  # noqa: E402, F403
from shared_conf import extensions  # noqa: E402

extensions = [*extensions, "multiproject"]
_PROJECTS = ("alpha", "beta")


def _values(name):
    conf = runpy.run_path(os.path.join(_here, name, "conf.py"))
    return {
        key: value
        for key, value in conf.items()
        if key in ("project", "intersphinx_mapping") or key.startswith("matlab_")
    }


if os.environ.get("PROBE_MULTIPROJECT_MODE") == "file":
    # The extension's default: read <project>/conf.py itself.
    multiproject_projects = {name: {} for name in _PROJECTS}
else:
    multiproject_projects = {
        name: {"use_config_file": False, "config": _values(name)} for name in _PROJECTS
    }
