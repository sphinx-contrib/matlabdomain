Contributing to sphinxcontrib-matlabdomain
==========================================

The developer guide is part of the documentation:
`docs/developer-guide/ <docs/developer-guide/contributing.rst>`_
(contributing, testing, architecture, debugging and profiling, roadmap).
Build it with:

.. code-block:: bash

    uv sync --all-extras
    uv run sphinx-build -M html docs docs/_build

Quick start:

.. code-block:: bash

    uv sync --all-extras
    uv run pre-commit install
    uv run pytest -q -o addopts=
