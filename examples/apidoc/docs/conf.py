"""Sphinx configuration of the sphinx-matlab-apidoc example."""

project = "sphinx-matlab-apidoc example"
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
matlab_src_code_project_root = "../src"
# Read by sphinx-matlab-apidoc -c . (paths relative to this folder).
matlab_apidoc_output_dir = "api"
matlab_apidoc_templatedir = "../templates"
nitpicky = True
exclude_patterns = ["_build"]
