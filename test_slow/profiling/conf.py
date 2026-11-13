"""Sphinx config for the SCM profiling harness.

Points `matlab_src_code_project_root` at a large real MATLAB tree (~1700 .m
files). Before the index became lazy, `analyze()` walked and parsed every
file on `builder-inited`; now a build only indexes them (read and
classify), and nothing is documented here, so nothing is parsed.
"""

import os

_here = os.path.dirname(os.path.abspath(__file__))

project = "SCM profiling harness"
author = "SCM"
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]

# Largest bundled fixture: vhlab-toolbox-matlab (~1726 .m files).
matlab_src_code_project_root = os.path.normpath(
    os.path.join(_here, "..", "repos", "vhlab-toolbox-matlab")
)

master_doc = "index"
exclude_patterns = ["_build"]
