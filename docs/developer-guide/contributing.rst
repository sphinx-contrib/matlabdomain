Contributing
============

Contributions are welcome: bug reports with a small MATLAB example, fixes,
tests and documentation. The code lives at
https://github.com/sphinx-contrib/matlabdomain.

Setting up
----------

The project uses `uv <https://docs.astral.sh/uv/>`_ and a lock file
(``uv.lock``). From a clone of the repository:

.. code-block:: console

   $ uv sync --all-extras
   $ uv run pre-commit install

``--all-extras`` installs the ``dev`` tools (pytest, coverage, pre-commit,
tox) and the ``rtd`` theme the documentation uses. Run tools through the
environment: ``uv run pytest``, or ``.venv/bin/python`` (Linux, macOS) and
``.venv\Scripts\python`` (Windows).

With plain ``pip``:

.. code-block:: console

   $ python -m venv .venv
   $ .venv/bin/python -m pip install -e ".[dev,rtd]"

Code style
----------

`pre-commit <https://pre-commit.com/>`_ runs on every commit: ruff (lint
and format), codespell, TOML and YAML checks, trailing whitespace and line
ends (LF), and ``uv lock``. Run it on demand with ``uv run pre-commit run
--files <files>``.

* Python code follows ruff's configuration in ``pyproject.toml``.
* Every new configuration value starts with ``matlab_``.
* Comments say what the code cannot show; tests and ``docs/CHANGES.rst``
  record behavior.
* MATLAB behavior the code follows (help text, names, file types,
  encodings) is checked against MATLAB itself; the tests cite the release.

Pull requests
-------------

* Keep each pull request to one subject, and reference the issue it targets
  ("Closes #123").
* Add tests for every change (:doc:`testing`); the coverage check requires
  every line and branch to be covered.
* Add an entry to ``docs/CHANGES.rst``. Mark changes that break existing
  projects with **Breaking**.
* Update the documentation when behavior changes; ``docs/`` builds with
  ``-n -W`` in the test suite.
* Tag the title when it helps: ``[FIX]``, ``[DOC]``, ``[ENH]``, ``[STY]``,
  ``[REF]``, ``[MAINT]``; ``[WIP]`` or a draft for work in progress.

Versions and compatibility
--------------------------

* The project follows `semantic versioning <https://semver.org/>`_ from
  1.0.0. The public interface includes the configuration values,
  directives, roles and options, path references and link anchors
  (:doc:`../user-guide/referencing`), the ``sphinx-matlab-apidoc``
  options and template variables, and the ``matlab-api-check`` rules and
  report format.
* Supported: Python 3.11 to 3.14, Sphinx 8.0 and newer, on Linux, Windows
  and macOS.
* ``tree-sitter`` and ``tree-sitter-matlab`` are pinned to exact ranges in
  ``pyproject.toml``. Neither project marks breaking changes with a major
  version, so every new release is evaluated by reading its changes and
  running the gauntlet (:doc:`testing`) before a pin moves.
* ``MATLABDomain.data_version`` is bumped whenever the domain data or the
  cached parsed objects change, so Sphinx drops stale environments.
