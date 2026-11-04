# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
# The commands run in the project's uv environment, as locked in uv.lock.
UV            = uv run --frozen --all-extras
SPHINXBUILD   = $(UV) sphinx-build
SPHINXAUTOBUILD = $(UV) sphinx-autobuild
SPHINXPROJ    = sphinxcontrib-matlabdomain
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Rebuild on every change and serve the HTML at http://127.0.0.1:8000.
# The pages include files from the worked example, so watch it too.
livehtml:
	@$(SPHINXAUTOBUILD) "$(SOURCEDIR)" "$(BUILDDIR)/html" -d "$(BUILDDIR)/doctrees" --watch ../examples/apidoc $(SPHINXOPTS) $(O)

.PHONY: help livehtml Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
