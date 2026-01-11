import os
import sys

sys.path.insert(0, os.path.abspath("pysrc"))

extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
matlab_src_dir = os.path.abspath(".")
nitpicky = True
