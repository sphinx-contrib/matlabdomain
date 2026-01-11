import os

extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
matlab_src_dir = os.path.abspath(".")
# This option is set in the test script: test_package_prefix.py
matlab_keep_package_prefix = True
nitpicky = True
primary_domain = "mat"
