import sys
import os

# General information about the project.
project = "MATLAB Sphinx Documentation Test"
copyright = "2014, Mark Mikofski"
author = "Mark Mikofski, Jørgen Cederberg"


sys.path.insert(0, os.path.abspath(os.path.join("..", "..")))
matlab_src_dir = os.path.abspath("..")

extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
primary_domain = "mat"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "default"
