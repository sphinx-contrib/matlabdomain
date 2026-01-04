import os

project = "test_docs_automodule"
copyright = "Jørgen Cederberg"
author = "Jørgen Cederberg"
matlab_src_dir = os.path.abspath(".")
matlab_short_links = True
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
nitpicky = True
primary_domain = "mat"
