# Makefile for Sphinx documentation
# Written by sphinx-matlab-quickstart (sphinxcontrib-matlabdomain).

SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
APIDOC        ?= sphinx-matlab-apidoc
SPHINXAUTOBUILD ?= sphinx-autobuild
SOURCEDIR     = .
BUILDDIR      = _build

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help apidoc apidoc-check livehtml Makefile

# Write the API pages from conf.py (matlab_apidoc_*).
apidoc:
	$(APIDOC) -c "$(SOURCEDIR)"

# Exit 1 when the API pages are out of date.
apidoc-check:
	$(APIDOC) -c "$(SOURCEDIR)" --check

# Live rebuild on changes to the docs and the MATLAB code.
livehtml:
	$(SPHINXAUTOBUILD) "$(SOURCEDIR)" "$(BUILDDIR)/html" -d "$(BUILDDIR)/doctrees" --watch ".." --ignore "*/.venv/*" --ignore "*/.git/*" --pre-build "$(APIDOC) -c . -q" $(SPHINXOPTS) $(O)

# Route all other targets to Sphinx's "make mode" (html, clean, ...), after
# writing the API pages (they are not committed).
%: Makefile
	@$(APIDOC) -c "$(SOURCEDIR)" -q
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
