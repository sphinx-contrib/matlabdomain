import os
import sys

sys.path.insert(0, os.path.abspath("pysrc"))

extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
matlab_src_code_project_root = "."
nitpicky = True
