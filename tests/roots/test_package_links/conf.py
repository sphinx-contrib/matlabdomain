import os

matlab_src_dir = os.path.abspath(".")
matlab_keep_package_prefix = True

extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
primary_domain = "mat"
master_doc = "contents"


# The suffix of source filenames.
source_suffix = {".rst": "restructuredtext"}

nitpicky = True
