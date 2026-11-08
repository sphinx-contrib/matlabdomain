import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join("..", "..")))

author = "Mark Mikofski, Jørgen Cederberg, Jason H. Nicholson and contributors"
copyright = "the sphinxcontrib-matlabdomain team (see AUTHORS)"
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
matlab_show_property_default_value = True
matlab_show_property_specs = True
matlab_src_code_project_root = ".."
primary_domain = "mat"
project = "MATLAB Sphinx Documentation Test"
