"""Configuration of the versioned fixture (the same in every revision; the
release is in ``VERSION``).
"""

import importlib.metadata
import json
import os
from pathlib import Path

project = "Geo"
version = release = (
    Path(__file__).with_name("VERSION").read_text(encoding="utf-8").strip()
)

extensions = ["sphinxcontrib.matlab", "sphinx_multiversion", "myst_parser"]
templates_path = ["_templates"]
html_theme = "alabaster"
html_sidebars = {
    "**": ["about.html", "navigation.html", "versions.html", "searchbox.html"]
}
html_context = {
    "matlabdomain_version": importlib.metadata.version("sphinxcontrib-matlabdomain")
}
exclude_patterns = ["_build"]
nitpicky = True

# Relative to the Sphinx source folder, which sphinx-multiversion moves to
# each revision's copy. ``PROBE_ABSOLUTE_ROOT`` shows what an absolute path
# does instead: it points every version at this conf.py's checkout.
matlab_src_code_project_root = "../src"
if os.environ.get("PROBE_ABSOLUTE_ROOT"):
    matlab_src_code_project_root = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "src"
    )
matlab_src_sidecar_suffixes = [".md"]
matlab_apidoc_output_dir = "api"

smv_tag_whitelist = r"^v\d+\.\d+$"
smv_branch_whitelist = r"^main$"
smv_remote_whitelist = None
# Matched against the full name (refs/tags/...), unlike the default.
smv_released_pattern = r"^refs/tags/.*$"
smv_latest_version = "v2.0"


def _record(app, exception):
    """Probe instrument: write what this build used to ``$PROBE_RECORD_DIR``."""
    folder = os.environ.get("PROBE_RECORD_DIR")
    if not folder or exception is not None:
        return
    import sys

    import sphinx

    import sphinxcontrib.matlab

    name = os.environ.get("SPHINX_MULTIVERSION_NAME", "plain")
    record = {
        "version_name": name,
        "release": app.config.release,
        "documented_commit": os.path.basename(os.path.dirname(os.fspath(app.srcdir))),
        "srcdir": os.fspath(app.srcdir),
        "confdir": os.fspath(app.confdir),
        "doctreedir": os.fspath(app.doctreedir),
        "references": sorted(
            r["reference"] for r in app.env.domaindata["mat"]["index"].values()
        ),
        "python": sys.executable,
        "matlabdomain_file": sphinxcontrib.matlab.__file__,
        "matlabdomain_version": app.extensions["sphinxcontrib.matlab"].version,
        "sphinx": sphinx.__version__,
    }
    with open(os.path.join(folder, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump(record, f, indent=1)


def setup(app):
    app.connect("build-finished", _record)
