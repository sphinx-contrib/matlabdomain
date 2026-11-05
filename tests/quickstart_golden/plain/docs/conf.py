# Sphinx configuration of the Quickstart test documentation.
# Written by sphinx-matlab-quickstart (sphinxcontrib-matlabdomain); edit freely.
# Configuration values: https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------

project = "Quickstart test"
copyright = "<YEAR>, Test Author"
author = "Test Author"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinxcontrib.matlab",
    "sphinx.ext.napoleon",
]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

primary_domain = "mat"
highlight_language = "matlab"
# Keep the straight quotes of the help text ('name', "text") as typed:
# smartquotes = False

# -- MATLAB domain -----------------------------------------------------------

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
]
matlab_version = "R2026a"

# API pages: sphinx-matlab-apidoc -c docs (make apidoc)
matlab_apidoc_output_dir = "API"
matlab_apidoc_group = "folder"
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

# -- HTML output -------------------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
