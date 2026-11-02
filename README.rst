sphinxcontrib-matlabdomain
==========================

A `Sphinx <https://www.sphinx-doc.org/>`_ extension for MATLAB code: a ``mat``
domain with directives and roles for MATLAB functions, classes, scripts,
apps and folders, and *auto* directives that read the help text from
``.m`` and ``.mlapp`` files, like ``sphinx.ext.autodoc`` does for Python.
Objects are named the way MATLAB names them (``+namespace`` and ``@class``
folders), and help text is found where MATLAB's ``help`` finds it.

It also ships:

* ``sphinx-matlab-apidoc``, which writes pages for every file of a project;
* the ``matlab-api-check`` builder, which checks that help text describes
  every function, class, method, input and output, for example in CI;
* pages next to code: tutorials and notes as ``.md`` and ``.rst`` files
  among the MATLAB files, rendered into the documentation (off by default;
  Markdown with the ``markdown`` extra).

.. note::

   This branch is a major rework of the extension, to be released as 1.0.0;
   see `issue 349 <https://github.com/sphinx-contrib/matlabdomain/issues/349>`_.

Install
-------

.. code-block:: console

   $ uv add sphinxcontrib-matlabdomain
   $ pip install sphinxcontrib-matlabdomain

Python 3.11 or newer and Sphinx 8.0 or newer; Linux, Windows and macOS.

Use
---

``conf.py``:

.. code-block:: python

   extensions = ["sphinxcontrib.matlab"]
   matlab_src_code_project_root = "../src"  # relative to conf.py's folder

A page:

.. code-block:: rst

   .. mat:autoclass:: mypackage.MyClass
      :members:

   .. mat:autofunction:: mypackage.myFunction

Pages for a whole project, and a check of its help text:

.. code-block:: console

   $ sphinx-matlab-apidoc -c docs -o docs/api
   $ sphinx-build -b matlab-api-check docs docs/_build/api-check

Documentation
-------------

The documentation is in ``docs/``: getting started, a user guide
(configuration, directives, references, help text, the two tools,
warnings, migrating from 0.x), a reference and a developer guide. Build it
with ``sphinx-build -M html docs docs/_build`` after ``uv sync
--all-extras``.

* Changes: ``docs/CHANGES.rst``
* Contributing: ``docs/developer-guide/contributing.rst``
* License: BSD-2-Clause (``LICENSE``)
