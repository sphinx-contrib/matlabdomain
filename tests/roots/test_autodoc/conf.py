import os

matlab_src_dir = os.path.abspath(".")
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
primary_domain = "mat"
nitpicky = True
# ignore warning about inheriting from unknown 'handle' class
nitpick_ignore = [("mat:class", "handle")]
