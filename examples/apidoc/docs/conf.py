"""Sphinx configuration of the scmd apidoc example."""

project = "scmd apidoc example"
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab", "myst_parser"]
matlab_src_code_project_root = "../src"
# Sidecar docs: Markdown (needs myst_parser) and reST.
matlab_src_sidecar_suffixes = [".md", ".rst"]
# Read by scmd apidoc (paths relative to this folder).
matlab_apidoc_output_dir = "api"
matlab_apidoc_templatedir = "../templates"
nitpicky = True
exclude_patterns = ["_build"]
