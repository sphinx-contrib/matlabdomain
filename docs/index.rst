sphinxcontrib-matlabdomain
==========================

If Sphinx is new to you, its `glossary
<https://www.sphinx-doc.org/en/master/glossary.html>`_ explains terms such as
directives, roles, domains and builders used in this documentation.

**sphinxcontrib-matlabdomain** is a `Sphinx`_ extension for `MATLAB`_ code. It
adds a ``mat`` domain to Sphinx, with directives and roles for MATLAB
functions, classes, scripts, apps and folders, and *auto* directives that
read the help text from the ``.m`` and ``.mlapp`` files themselves, much like
``sphinx.ext.autodoc`` does for Python.

It names objects the way MATLAB does: ``+pkg`` folders are namespaces,
``@Cls`` folders hold a class and its methods, and help text is found where
MATLAB's ``help`` finds it. Three tools come with it:

* ``sphinx-matlab-quickstart`` sets up the documentation of a MATLAB
  project: ``conf.py``, the make files and the API pages, with defaults
  read from the project;
* ``sphinx-matlab-apidoc`` writes pages for every file of a project, so a
  large project needs no hand-written directives;
* the ``matlab-api-check`` builder checks that functions, classes and
  methods have help text, and that it describes their inputs, outputs and
  name-value arguments, for example in CI.

A ``conf.py`` and a page that document one function:

.. code-block:: python

   extensions = ["sphinxcontrib.matlab"]
   matlab_src_code_project_root = "../src"  # relative to conf.py folder

.. literalinclude:: snippets/quickstart.rst
   :language: rst

:doc:`getting-started/quickstart` shows the result.

It needs Python 3.11 or newer and Sphinx 8.0 or newer, and is tested on
Linux, Windows and macOS. Start with :doc:`getting-started/installation`.

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   getting-started/installation
   getting-started/quickstart

.. toctree::
   :maxdepth: 2
   :caption: User guide

   user-guide/configuration
   user-guide/setting-up
   user-guide/documenting
   user-guide/referencing
   user-guide/linking-projects
   user-guide/help-text
   user-guide/apidoc
   user-guide/sidecars
   user-guide/api-check
   user-guide/warnings
   user-guide/builds
   user-guide/projects-and-versions
   user-guide/migration

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference/configuration
   reference/directives
   reference/cli
   reference/templates
   reference/api-check-report
   reference/warnings

.. toctree::
   :maxdepth: 2
   :caption: Developer guide

   developer-guide/contributing
   developer-guide/testing
   developer-guide/architecture
   developer-guide/debugging
   developer-guide/roadmap

.. toctree::
   :maxdepth: 1
   :caption: Project

   CHANGES

Indices and tables
------------------

* :ref:`genindex`
* :ref:`mat-folderindex`
* :ref:`search`

.. _Sphinx: https://www.sphinx-doc.org/
.. _MATLAB: https://www.mathworks.com/products/matlab.html
