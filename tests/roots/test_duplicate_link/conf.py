import os

author = "Denis Rosset, Jean-Daniel Bancal and collaborators"
autodoc_default_options = {"members": True, "show-inheritance": True}
autosummary_generate = True
default_role = "obj"
project = "RepLAB"
copyright = "Denis Rosset, Jean-Daniel Bancal and collaborators"
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
matlab_keep_package_prefix = True
matlab_src_dir = f"{os.path.dirname(os.path.abspath(f'{__file__}/'))}/_src"
nitpicky = True
primary_domain = "mat"
