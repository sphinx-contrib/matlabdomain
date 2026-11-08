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

``uv sync`` installs the ``dev`` dependency group: the ``test`` group
(pytest, coverage), the ``docs`` group (the theme the
documentation uses, `Furo <https://pradyunsg.me/furo/>`_, and Mermaid), and
pre-commit, tox, Ruff, Pyright and sphinx-autobuild. ``--all-extras`` adds
Markdown support (the ``markdown`` extra). Run
tools through the environment: ``uv run pytest``, or ``.venv/bin/python``
(Linux, macOS) and ``.venv\Scripts\python`` (Windows).

With plain ``pip`` (25.1 or later, for ``--group``):

.. code-block:: console

   $ python -m venv .venv
   $ .venv/bin/python -m pip install -e ".[markdown]" --group dev

Writing documentation
---------------------

The documentation is in ``docs/``. To preview it while you edit, run the
``livehtml`` target, which rebuilds on every change (also to the worked
example in ``examples/apidoc``) and serves the pages at
http://127.0.0.1:8000:

.. code-block:: console

   $ cd docs
   $ make livehtml        # Linux, macOS
   $ make.bat livehtml    # Windows

It runs ``sphinx-autobuild``. Changes to the extension's own code need a
restart. Check the final text with a full strict build:

.. code-block:: console

   $ uv run sphinx-build -M html docs docs/_build -E -n -W

Code style
----------

`pre-commit <https://pre-commit.com/>`_ runs on every commit: ruff (lint
and format), codespell, TOML and YAML checks, trailing whitespace and line
ends (LF), and ``uv lock``. Run it on demand with ``uv run pre-commit run
--files <files>``. Pull requests run every hook on all files.

* Python code follows ruff's configuration in ``pyproject.toml``.
* Run ``uv run tox -e lint`` for non-mutating lint, format and basic type
  checks, including tests and maintained helper scripts.
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
* GitHub requests a review from the maintainers listed in
  ``.github/CODEOWNERS``.

.. _project-roles:

Project roles
-------------

GitHub's repository settings decide who can do what; this list says who
plays which part. ``AUTHORS`` credits everyone.

Lead maintainer
  Jason H. Nicholson (`@jasonnicholson
  <https://github.com/jasonnicholson>`_): design decisions, releases,
  repository settings.
Maintainers
  Remi Gau (`@Remi-Gau <https://github.com/Remi-Gau>`_) and Anton
  Edvinovich Pozharskiy (`@apozharski <https://github.com/apozharski>`_):
  review, merge and triage.
Former maintainer
  Jørgen Cederberg (`@joeced <https://github.com/joeced>`_).
Original author
  Mark Mikofski (`@mikofski <https://github.com/mikofski>`_).

Releases are published from tags by
``.github/workflows/push-master.yml``. The `PyPI project
<https://pypi.org/project/sphinxcontrib-matlabdomain/>`_ is owned by
Jørgen Cederberg. Read the Docs project owner: to be confirmed.

Versions and compatibility
--------------------------

* The project follows `semantic versioning <https://semver.org/>`_ from
  1.0.0. The public interface includes the configuration values,
  directives, roles and options, path references and link anchors
  (:doc:`../user-guide/referencing`), the ``scmd apidoc``
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

.. _repository-configuration:

Repository configuration
------------------------

``pyproject.toml`` owns Python metadata and shared tool policy. Keep a file
separate only when its consumer requires that format or it records generated
state. The inventory below is checked by
``tests/test_documentation.py::test_repository_configuration``; update it
when adding, removing or moving a maintained configuration file.

``pyproject.toml``
  Hand-maintained package metadata, build backend and minimum backend version,
  runtime dependencies, optional extras, dependency groups (``dev``,
  ``test``, ``docs``), console entry point, namespace-package
  discovery and Jinja package data. Also owns pytest, coverage, codespell,
  Ruff, Pyright, native tox environments and uv's public package index.
  Check with ``uv build``, ``uv run pytest`` and ``uv run tox -e lint``.
  The former ``tox.ini`` is merged here. The old ``MANIFEST.in`` is removed:
  setuptools includes the declared readme and license, setuptools-scm includes
  tracked source files, and package-data includes the CLI templates. Do not
  reintroduce a second copy of these settings.
``uv.lock``
  Generated by ``uv lock``; never edit by hand. Records the reproducible local
  development environment, not the supported dependency range. Commit it with
  dependency edits; check with ``uv sync --locked --all-extras``. tox deliberately
  resolves its minimum/latest/development matrix independently of this lock.
``.python-version``
  Hand-selected uv development interpreter; also read by the static-check CI
  job. It is not the supported Python range, which is declared in
  ``pyproject.toml`` and tested by the CI matrix.
``.pre-commit-config.yaml``
  Hook repositories, revisions and hook-only arguments. Tool policy stays in
  ``pyproject.toml``; Ruff's hook revision must match the development pin.
  Ruff applies safe fixes only. Run ``uv run pre-commit run --all-files``;
  inspect and rerun after automatic fixes. Pyright runs in tox/CI rather than
  once per staged file, since it needs the complete project environment.
  ``mixed-line-ending`` runs last so one run also fixes the CRLF that the
  TOML formatter writes on Windows.
``.github/codespell_ignore_words.txt``
  Hand-maintained project vocabulary for codespell, referenced by
  ``tool.codespell``. Add legitimate words, not misspellings; check with the
  codespell pre-commit hook.
``.github/CODEOWNERS``
  GitHub review routing: the maintainers of :ref:`project-roles` own every
  path. Keep it in step with that list; GitHub flags unknown owners on the
  file's page.
``.github/dependabot.yml``
  GitHub-required YAML. One quarterly pull request updates the Actions pins,
  the pre-commit hook revisions and ``uv.lock`` together; security updates are
  grouped per ecosystem.
``.github/workflows/pr-master.yml``
  Pull requests to ``master`` (and on demand): all pre-commit hooks, static
  checks and ``tests.yml``. Its ``PR checks`` job passes only when every
  other job passed; the ``master`` ruleset requires that one check, so
  renaming jobs never breaks the ruleset. Actions are pinned by commit SHA
  with the version in a comment.
``.github/workflows/tests.yml``
  The supported Python/OS/Sphinx matrix and the combined 100% coverage gate,
  called by ``pr-master.yml`` and run monthly (new Python, Sphinx and
  dependency releases) and on demand. The Sphinx-development job is
  non-blocking. Uses the shared tox environments; local checks cannot
  substitute for the cross-platform coverage gate.
``.github/workflows/push-master.yml``
  Pushes to ``master`` and release tags (bare versions such as ``0.22.1``):
  no tests. It builds the sdist and wheel and runs ``scmd`` from the
  installed wheel. A tag of the upstream repository must be on ``master``;
  the ``pypi`` environment then publishes those files to PyPI and a GitHub
  release.
``readthedocs.yml``
  Read the Docs-required service file: build image, Python version, docs entry
  point, ``docs`` dependency group (installed with ``uv sync``) and warning
  policy. Validate documentation
  locally with the strict Sphinx build, then inspect the hosted build.
``.vscode/settings.json``
  Portable clone-level interpreter, workspace diagnostics and Ruff integration.
  ``files.eol`` makes new files LF, as ``.gitattributes`` stores them, so
  the line-ending hook has nothing to fix on Windows.
  Open the repository folder in VS Code, select its ``.venv`` interpreter and
  install Python/Pylance and Ruff. Pylance reads basic mode, Python 3.11 target
  and analysis scope from ``tool.pyright``; Ruff reads ``tool.ruff``. Parent
  workspace or user settings may override editor behavior: the CLI gate is
  authoritative, with no machine-specific interpreter path committed here.
``.vscode/launch.json``
  Hand-maintained debugger launch profiles for docs, pytest, profiling and the
  CLIs. Uses the selected interpreter; try the relevant profile after changing
  command arguments. Do not copy lint or type policy into launch profiles.
``.gitattributes``
  Git text/binary and line-ending rules: LF, except CRLF for ``.bat`` and
  ``.cmd`` (``cmd.exe`` misreads labels in LF files; pre-commit's LF hook skips
  them). Keep binary MATLAB artifacts binary; inspect ``git diff --check`` and
  cross-platform checkouts after edits.
``.gitignore``
  Git exclusions for environments, build/coverage/cache output and fetched
  gauntlet repositories/runs. It does not define Python analysis scope;
  ``tool.ruff`` and ``tool.pyright`` explicitly exclude fixtures and generated
  projects. Check ``git status --ignored`` after adding an output directory.
``docs/conf.py``
  Hand-maintained Sphinx documentation project: extensions, MATLAB example
  source, theme, links and strictness. Validate with
  ``uv run sphinx-build -M html docs docs/_build -E -n -W``.
``docs/Makefile``
  POSIX Sphinx convenience targets, including live preview. Calls Sphinx tools
  from the selected environment; try ``make html`` after edits in the docs folder.
``docs/make.bat``
  Windows counterpart of the Makefile. Keep equivalent targets in sync; try
  ``make html`` from the docs folder.
``examples/apidoc/docs/conf.py``
  Maintained worked-example Sphinx project, not shared repository tool policy.
  The example-build tests check it, its generated API pages and reports.
``test_slow/gauntlet/projects.toml``
  Hand-maintained real-project declarations: URLs, versions, exclusions and
  project-specific build options. Consumed by ``fetch.py`` and ``gauntlet.py``;
  validate with the gauntlet workflow described in :doc:`testing`.
``test_slow/gauntlet/projects.lock.toml``
  Generated fetched commit IDs. ``fetch.py`` updates it; review URL/commit
  changes with the project declarations. Separate from ``uv.lock`` because it
  locks MATLAB input repositories, not Python dependencies.
``CONTRIBUTING.rst``
  Root discoverability pointer and quick-start commands; GitHub links it from
  new issues and pull requests. It points to the maintained guide at
  ``docs/developer-guide/``.

Ruff and basic Pyright analyze ``sphinxcontrib``, tests, documentation config,
examples, skill scripts and slow-test tools. They exclude ``tests/roots``,
``tests/test_data`` and ``tests/test_docs`` (test inputs, sometimes deliberately
invalid), skill templates copied into user projects, generated builds/caches
and gauntlet checkouts/runs. User-facing configuration templates and fixture
``conf.py`` files are tested as data. If
a parent workspace disables Pylance checks, open this repository as its own
folder to use these settings.
