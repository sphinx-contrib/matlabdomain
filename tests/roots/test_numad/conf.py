import os

matlab_src_dir = os.path.abspath(".")
matlab_keep_package_prefix = False
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
primary_domain = "mat"
project = "test_class_options"
nitpicky = True
