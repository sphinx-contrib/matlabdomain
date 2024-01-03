import sys
import os

# General information about the project.
project = "test_docs_automodule"
copyright = "2023, Jørgen Cederberg"
author = "Jørgen Cederberg"

# Setup extension
matlab_src_dir = os.path.abspath(".")
matlab_short_links = True
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
primary_domain = "mat"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_theme = "default"
