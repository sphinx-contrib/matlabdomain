"""Alpha's configuration: builds on its own (``sphinx-build docs/alpha``)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_conf import *

project = "Alpha"
# Relative to this folder, the Sphinx source folder of the project.
matlab_src_code_project_root = "../../alpha/src"
matlab_src_sidecar_suffixes = [".md"]
matlab_apidoc_output_dir = "api"
