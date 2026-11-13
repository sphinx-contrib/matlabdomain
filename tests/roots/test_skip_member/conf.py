author = "Mark Mikofski, Jørgen Cederberg, Jason H. Nicholson and contributors"
copyright = "the sphinxcontrib-matlabdomain team (see AUTHORS)"
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]
matlab_src_code_project_root = "."
primary_domain = "mat"
project = "Skipping Members"
nitpicky = True


def skip_second(app, what, name, obj, skip, options):
    print(f"{app}, {what}, {name}, {obj}, {skip}, {options}")
    return name == "second"


def setup(app):
    app.connect("autodoc-skip-member", skip_second)
