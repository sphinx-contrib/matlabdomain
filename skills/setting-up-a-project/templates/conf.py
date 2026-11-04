# Sphinx configuration for the documentation of a MATLAB project.
# Template from the setting-up-a-project skill of sphinxcontrib-matlabdomain;
# replace every <...> and delete what the project does not use.

import configparser
import os

from sphinxcontrib.matlab import DEFAULT_EXTERNAL_NAMES

# -- Project information -----------------------------------------------------

project = "<Project name>"
copyright = "<year>, <owner>"
author = "<owner>"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinxcontrib.matlab",
    "sphinx.ext.napoleon",
    "myst_parser",  # Markdown pages and sidecar docs; drop if unused
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

primary_domain = "mat"
highlight_language = "matlab"

# -- MATLAB domain -----------------------------------------------------------


def _submodule_paths(gitmodules):
    """Paths of the git submodules listed in a .gitmodules file."""
    parser = configparser.ConfigParser()
    parser.read(gitmodules, encoding="utf-8")
    return [parser[s]["path"] for s in parser.sections() if "path" in parser[s]]


matlab_src_code_project_root = ".."
matlab_src_exclusion_patterns = [
    # The default list, which a project list replaces.
    "README.*",
    "CHANGES.*",
    "CHANGELOG.*",
    "LICENSE.*",
    "CONTRIBUTING.*",
    "CODE_OF_CONDUCT.*",
    "SECURITY.*",
    # Not code of the project, or not on its MATLAB path.
    "<folder>",
    # Submodules are separate projects with their own docs.
    *_submodule_paths(os.path.join(os.path.dirname(__file__), "..", ".gitmodules")),
]
matlab_version = "<R20xxx>"
# Markdown notes next to the code become part of the API pages.
matlab_src_sidecar_suffixes = [".md"]

# API pages: sphinx-matlab-apidoc -c docs (make apidoc)
matlab_apidoc_output_dir = "API"
matlab_apidoc_group = "namespace"
matlab_apidoc_page_size = 100

matlab_class_signature = True
matlab_add_namespace_names = False
matlab_auto_link = "basic"
autoclass_content = "class"
# Classes from other projects (submodules, toolboxes): text, not warnings.
matlab_external_names = [
    *DEFAULT_EXTERNAL_NAMES,
    r"<namespace>\..+",
]

# Help-text audit: sphinx-build -b matlab-api-check. All rules warn at first.
matlab_api_check_rules = {
    "description": "warning",
    "method-description": "warning",
    "property-description": "warning",
    "inputs": "warning",
    "outputs": "warning",
    "name-value": "warning",
    "example": "warning",
    "method-example": "warning",
    "sidecar-documented": "warning",
    "sidecar-links": "warning",
}

# -- Napoleon ----------------------------------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_rtype = True
# The project's own help headings (help_headings.py), besides napoleon's.
napoleon_custom_sections = [
    ("Inputs", "params_style"),
    ("Outputs", "params_style"),
    "Description",
]

# -- MyST --------------------------------------------------------------------

myst_enable_extensions = ["colon_fence", "deflist", "dollarmath", "linkify"]
myst_heading_anchors = 6

# -- HTML output -------------------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
