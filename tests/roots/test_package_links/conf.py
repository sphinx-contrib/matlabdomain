import os

extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
master_doc = "contents"
matlab_src_dir = os.path.abspath(".")
matlab_keep_package_prefix = True
primary_domain = "mat"
nitpicky = True
