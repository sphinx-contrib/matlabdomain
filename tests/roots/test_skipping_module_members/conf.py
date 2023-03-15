import os

project = "Skipping Members"
copyright = "2023, Jørgen Cederberg"
author = "Jørgen Cederberg"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []
matlab_src_dir = os.path.abspath(".")

extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
primary_domain = "mat"
master_doc = "index"

# The suffix of source filenames.
source_suffix = ".rst"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]


def skip_second(app, what, name, obj, skip, options):
    print(f"{app}, {what}, {name}, {obj}, {skip}, {options}")
    return name == "second"


def setup(app):
    app.connect("autodoc-skip-member", skip_second)
