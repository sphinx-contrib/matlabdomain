"""Sphinx configuration of the sphinx-matlab-apidoc example."""

project = "sphinx-matlab-apidoc example"
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab", "myst_parser"]
matlab_src_code_project_root = "../src"
# Pages next to code: Markdown (needs myst_parser) and reST.
matlab_src_page_suffixes = [".md", ".rst"]
# Read by sphinx-matlab-apidoc -c . (paths relative to this folder).
matlab_apidoc_output_dir = "api"
matlab_apidoc_templatedir = "../templates"
nitpicky = True
exclude_patterns = ["_build"]
