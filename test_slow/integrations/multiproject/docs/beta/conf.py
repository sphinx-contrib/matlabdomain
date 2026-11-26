"""Beta's configuration: builds on its own (``sphinx-build docs/beta``)."""

import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))
from shared_conf import *

project = "Beta"
matlab_src_code_project_root = "../../beta/src"
matlab_src_sidecar_suffixes = [".md"]
matlab_apidoc_output_dir = "api"

# Alpha is built first; its pages sit next to Beta's (``site/alpha/``).
# The inventory path is relative to the source folder (this one).
intersphinx_mapping = {"alpha": ("../alpha/", "../_build/alpha/html/objects.inv")}
