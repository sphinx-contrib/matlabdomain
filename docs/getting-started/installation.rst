Installation
============

Install the package from PyPI. With `uv <https://docs.astral.sh/uv/>`_, add
it to your project:

.. code-block:: console

   $ uv add sphinxcontrib-matlabdomain

or with ``pip``:

.. code-block:: console

   $ pip install sphinxcontrib-matlabdomain

Examples use ``uv run``. With another environment manager, run the same
commands without that prefix when the installed tools are on :term:`PATH`.

This installs Sphinx, `tree-sitter <https://tree-sitter.github.io/>`_ and the
MATLAB grammar for tree-sitter, which the extension uses to read MATLAB code.
MATLAB itself is not needed.

For :doc:`Markdown sidecar docs <../user-guide/sidecars>`, add the
``markdown`` extra, which installs `myst-parser
<https://myst-parser.readthedocs.io/>`_ 4 or 5:

.. code-block:: console

   $ uv add "sphinxcontrib-matlabdomain[markdown]"

With pip, use ``pip install "sphinxcontrib-matlabdomain[markdown]"``.

Requirements
------------

* Python 3.11 or newer, the standard builds. Free-threaded Python is not
  supported, because ``tree-sitter`` does not support it yet
  (`py-tree-sitter#458
  <https://github.com/tree-sitter/py-tree-sitter/issues/458>`_).
* Sphinx 8.0 or newer.
* ``tree-sitter`` 0.26.1 and ``tree-sitter-matlab`` 1.3.3. These
  are pinned exactly, because both projects change their output in minor
  releases; each new release is checked before the pins move.
* On Python 3.11 only, ``typing-extensions`` 4.4 or newer, for the
  ``override`` decorator that Python 3.12 added to ``typing``.

Tested: Python |python-tested| and Sphinx |sphinx-tested|. Support is best
effort: every Python version that is still maintained, and every Sphinx
release from 8.0 on, is meant to work. A new release is added to the tests
within about three months, so a newer version may already work before it is
listed. A Python version past its end of life may still work but is not
supported.

On Python 3.15 and newer, ``tree-sitter`` 0.26.1 has no prebuilt wheel, so
installing it compiles it from source and needs a C compiler (on Windows,
the Microsoft C++ Build Tools). Python 3.15 support is merged in
py-tree-sitter (`py-tree-sitter#519
<https://github.com/tree-sitter/py-tree-sitter/issues/519>`_) but not yet
released.

The extension is tested on Linux and Windows (x86-64) and macOS (arm64).
Path references and patterns are case-sensitive on every system. On a
case-insensitive file system (the Windows and macOS default), names that
differ only by letter case are handled on a best-effort basis.

What gets installed
-------------------

* The Sphinx :term:`extension` ``sphinxcontrib.matlab``: add it to ``extensions`` in
  ``conf.py`` (see :doc:`quickstart`). It also loads ``sphinx.ext.autodoc``,
  whose configuration values the auto directives read.
* The ``matlab-api-check`` :term:`builder`, which comes with the extension:
  ``sphinx-build -b matlab-api-check`` (see :doc:`../user-guide/api-check`).
* The command ``scmd`` (also ``sphinxcontrib-matlabdomain``), with
  ``apidoc`` to write :term:`API` pages and ``quickstart`` to set up documentation
  (see :doc:`../reference/cli`).

To work on the extension itself, see :doc:`../developer-guide/contributing`.
