import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join("..", "..")))

author = "Mark Mikofski, Jørgen Cederberg"
copyright = "Mark Mikofski"
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
matlab_show_property_default_value = True
matlab_show_property_specs = True
matlab_src_dir = os.path.abspath("..")
primary_domain = "mat"
project = "MATLAB Sphinx Documentation Test"
