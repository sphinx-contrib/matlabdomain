import os

matlab_src_dir = os.path.abspath(".")
matlab_short_links = True
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
primary_domain = "mat"
project = "test_classfolder"
master_doc = "index"
source_suffix = ".rst"
nitpicky = True
