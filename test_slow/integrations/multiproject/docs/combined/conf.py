"""One build, one root above both projects (for comparison only)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_conf import *  # noqa: F403

project = "Combined"
matlab_src_code_project_root = "../.."
matlab_src_include_patterns = ["alpha/src/**", "beta/src/**"]
matlab_src_sidecar_suffixes = [".md"]
matlab_apidoc_output_dir = "api"
