# Makefile for Sphinx documentation

SPHINXOPTS    ?=
# The commands run in the project's uv environment, as locked in uv.lock.
UV            ?= uv run --frozen
SPHINXBUILD   ?= $(UV) sphinx-build
APIDOC        ?= $(UV) sphinx-matlab-apidoc
SPHINXAUTOBUILD ?= $(UV) sphinx-autobuild
SOURCEDIR     = .
BUILDDIR      = _build

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help apidoc apidoc-check livehtml Makefile

# Write the API pages from conf.py (matlab_apidoc_*).
apidoc:
	$(APIDOC) -c "$(SOURCEDIR)"

# Exit 1 when the committed API pages are out of date.
apidoc-check:
	$(APIDOC) -c "$(SOURCEDIR)" --check

# Live rebuild on changes to the docs and the MATLAB code.
livehtml:
	$(SPHINXAUTOBUILD) "$(SOURCEDIR)" "$(BUILDDIR)/html" -d "$(BUILDDIR)/doctrees" --watch .. --ignore "*/.venv/*" --ignore "*/.git/*" --pre-build "$(APIDOC) -c . -q" $(SPHINXOPTS) $(O)

# Route all other targets to Sphinx's "make mode" (html, clean, ...).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
