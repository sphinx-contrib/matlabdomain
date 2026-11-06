"""Settings shared by both projects (imported by every conf.py here)."""

import json
import os

_here = os.path.dirname(os.path.abspath(__file__))

extensions = [
    "sphinxcontrib.matlab",
    "sphinx.ext.intersphinx",
    "myst_parser",
]
# Absolute, so it works whichever folder Sphinx takes as the conf folder.
templates_path = [os.path.join(_here, "_templates")]
html_theme = "alabaster"
exclude_patterns = ["_build"]
nitpicky = True


def _record(app, exception):
    """Probe instrument: write what this build used to ``$PROBE_RECORD``."""
    path = os.environ.get("PROBE_RECORD")
    if not path or exception is not None:
        return
    import sphinx

    import sphinxcontrib.matlab
    from sphinxcontrib import mat_types

    record = {
        "project": app.config.project,
        "srcdir": os.fspath(app.srcdir),
        "confdir": os.fspath(app.confdir),
        "doctreedir": os.fspath(app.doctreedir),
        "project_root": mat_types.project_root(app.config, app.srcdir),
        "indexed": sorted(app.env.domaindata["mat"]["index"]),
        "sidecars": sorted(app.env.domaindata["mat"]["sidecars"]),
        "matlabdomain_file": sphinxcontrib.matlab.__file__,
        "matlabdomain_version": app.extensions["sphinxcontrib.matlab"].version,
        "sphinx": sphinx.__version__,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=1)


def setup(app):
    app.connect("build-finished", _record)
