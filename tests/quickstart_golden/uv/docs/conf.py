# Sphinx configuration of the Quickstart test documentation.
# Written by sphinx-matlab-quickstart (sphinxcontrib-matlabdomain); edit freely.
# Configuration values: https://www.sphinx-doc.org/en/master/usage/configuration.html

import configparser
import os

# -- Project information -----------------------------------------------------

project = "Quickstart test"
copyright = "<YEAR>, Test Author"
author = "Test Author"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinxcontrib.matlab",
    "sphinx.ext.napoleon",
    "myst_parser",  # Markdown pages and sidecar docs
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

primary_domain = "mat"
highlight_language = "matlab"
# Keep the straight quotes of the help text ('name', "text") as typed:
# smartquotes = False

# -- MATLAB domain -----------------------------------------------------------


def _submodule_paths(gitmodules):
    """Paths of the git submodules listed in a .gitmodules file."""
    parser = configparser.ConfigParser()
    parser.read(gitmodules, encoding="utf-8")
    return [parser[s]["path"] for s in parser.sections() if "path" in parser[s]]


_GITMODULES = os.path.join(os.path.dirname(__file__), "../.gitmodules")


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
    # Not on the MATLAB project path (matlab.toml); start-up files may
    # add more. Uncomment what is not the project's API:
    # "data",
    # "src/startup_hook.m",
    # Submodules are separate projects with their own docs.
    *_submodule_paths(_GITMODULES),
]
matlab_version = "R2024b"
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
# Classes of other projects (submodules, toolboxes) as text, not as
# "reference target not found" warnings:
# from sphinxcontrib.matlab import DEFAULT_EXTERNAL_NAMES
# matlab_external_names = [*DEFAULT_EXTERNAL_NAMES, r"othernamespace\..+"]

# Help-text audit: sphinx-build -b matlab-api-check. All rules warn at first.
matlab_api_check_rules = {
    "description": "warning",
    "method-description": "warning",
    "property-description": "warning",
    "event-description": "warning",
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
# The project's own help headings, used in 10 or more files.
# Headings match ignoring case, and only if made of letters, digits, "_"
# and spaces. Under a "params_style" heading, "name - text" and
# "name: text" items become parameters. ("Input", "Inputs") makes "Input"
# an alias of "Inputs".
napoleon_custom_sections = [
    "Description",
    ("Outputs", "params_style"),
    ("Inputs", "params_style"),
    ("Input", "Inputs"),
]

# -- MyST --------------------------------------------------------------------

myst_enable_extensions = ["colon_fence", "deflist", "dollarmath"]
myst_heading_anchors = 6

# -- HTML output -------------------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
# Put published URL here. Blank, it means local mode is used.
# This assists Simulink documentation linking.
html_baseurl = ""
