import os

matlab_src_dir = os.path.abspath(".")
# This option is set in the test script: test_package_prefix.py
matlab_keep_package_prefix = True

primary_domain = "mat"


extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]

# The master toctree document.
master_doc = "index"
source_suffix = {".rst": "restructuredtext"}
nitpicky = True
