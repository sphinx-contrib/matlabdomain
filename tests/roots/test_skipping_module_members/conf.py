import os

author = "Jørgen Cederberg"
copyright = "Jørgen Cederberg"
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
matlab_src_dir = os.path.abspath(".")
primary_domain = "mat"
project = "Skipping Members"
nitpicky = True


def skip_second(app, what, name, obj, skip, options):
    print(f"{app}, {what}, {name}, {obj}, {skip}, {options}")
    return name == "second"


def setup(app):
    app.connect("autodoc-skip-member", skip_second)
