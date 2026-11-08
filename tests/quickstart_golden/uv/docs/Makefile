# Makefile for Sphinx documentation
# Written by sphinx-matlab-quickstart (sphinxcontrib-matlabdomain).

SPHINXOPTS    ?=
# The commands run in the project's uv environment, as locked in uv.lock.
UV            ?= uv run --frozen --group docs
SPHINXBUILD   ?= $(UV) sphinx-build
APIDOC        ?= $(UV) scmd apidoc
SPHINXAUTOBUILD ?= $(UV) sphinx-autobuild
SOURCEDIR     = .
BUILDDIR      = _build
# The port of make livehtml; the build gives it to Simulink Help links.
LIVEPORT      ?= 8000

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help apidoc apidoc-check livehtml Makefile

# Write the API pages from conf.py (matlab_apidoc_*).
apidoc:
	$(APIDOC) --conf-dir "$(SOURCEDIR)"

# Exit 1 when the API pages are out of date.
apidoc-check:
	$(APIDOC) --conf-dir "$(SOURCEDIR)" --check

# Live rebuild on changes to the docs and the MATLAB code.
livehtml:
	$(SPHINXAUTOBUILD) "$(SOURCEDIR)" "$(BUILDDIR)/html" -d "$(BUILDDIR)/doctrees" --watch ".." --ignore "*/.venv/*" --ignore "*/.git/*" --pre-build "$(APIDOC) --conf-dir . --quiet" --port $(LIVEPORT) -D matlab_simulink_server=http://127.0.0.1:$(LIVEPORT)/ $(SPHINXOPTS) $(O)

# Route all other targets to Sphinx's "make mode" (html, clean, ...).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
