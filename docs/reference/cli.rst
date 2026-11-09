Command-line tools
==================

The package provides one command, ``scmd`` (also installed as
``sphinxcontrib-matlabdomain``). Use ``scmd quickstart`` once to set up a project and
``scmd apidoc`` whenever its :term:`API` pages need updating; ``scmd skills``
copies the agent skills that ship with the package into a project. Run
``scmd --help`` or ``scmd SUBCOMMAND --help`` for the available commands
and options.

Every option has a short and a long spelling. Prefer long spellings in
scripts and CI. Project settings belong in Sphinx's ``conf.py``; CLI
options select the operation or control a single run.

``scmd quickstart``
-------------------

.. program:: scmd quickstart

Synopsis
~~~~~~~~

.. code-block:: text

   scmd quickstart [ROOT] [--output-dir DOCS] [--quiet] [--dry-run] [--answers FILE] [--force]

Sets up Sphinx documentation for the MATLAB project in ``ROOT``: the Sphinx
:term:`source folder <source directory>` ``DOCS`` with its files and API pages,
the docs dependencies,
and two lines for git. It asks one question per choice, with the answer it
detected as the default, and prints a report of the project.
:doc:`../user-guide/setting-up` is the tutorial.

Arguments
~~~~~~~~~

.. option:: ROOT

   The MATLAB project root, the folder all documented code is below.
   Default: the current folder.

.. option:: -o DOCS, --output-dir DOCS

   The Sphinx source folder, inside ``ROOT``. Default: ``ROOT/docs``. A
   folder that exists with files but without a ``conf.py`` is in use (an
   MkDocs ``docs/``, for example): the command says so and asks for
   another one, relative to ``ROOT``; with :option:`-q`, it stops.

Options
~~~~~~~

.. option:: -q, --quiet

   Ask nothing: take the answers of :option:`--answers`, then the detected
   defaults. It does not offer to save the answers.

.. option:: -n, --dry-run

   Write nothing. Print the files it would write in ``DOCS``, the lines
   it would add outside it and the report, then ask to save the answers
   (default yes). The answers file is the only file a dry run may write.

.. option:: -a FILE, --answers FILE

   Read answers from a TOML file and ask only for the others. The command
   offers to save one at the end (default ``ROOT/scmd-quickstart.toml``);
   the keys are those of :ref:`quickstart-answers`.

.. option:: -f, --force

   When ``DOCS/conf.py`` exists, rewrite the files the command writes
   (``conf.py``, ``index.rst``, ``_static/.gitkeep``, ``Makefile``,
   ``make.bat``, ``BUILDING_DOCS.md`` and the API pages) and nothing else.
   Without it, an existing ``DOCS/conf.py`` stops the command.

.. option:: -V, --version

   Print the version and exit.

.. option:: -h, --help

   Print the help and exit.

What it writes
~~~~~~~~~~~~~~

In ``DOCS``: ``conf.py``, ``index.rst``, ``_static/.gitkeep``,
``Makefile``, ``make.bat`` (CRLF line ends), ``BUILDING_DOCS.md`` (unless
the answer ``guide`` is ``false``), and the API pages in ``DOCS/API``,
written as :program:`scmd apidoc` would write them from that
``conf.py``. The templates are in the package
(``sphinxcontrib/matlab_quickstart/templates``).

Outside ``DOCS``, each only if the line is not there yet:

* ``pyproject.toml``: the docs dependencies in the dependency group
  ``docs``, through ``uv add --frozen --group docs``, when the project uses
  uv (a ``uv.lock`` or a ``[tool.uv]`` table). The ``uv.lock`` file is
  never touched; the next steps say to run ``uv lock`` and ``uv sync
  --group docs``. Without uv it edits nothing and prints the ``pip
  install`` line (and the ``[dependency-groups]`` table, when there is a
  ``pyproject.toml``).
* ``.gitignore``: ``DOCS/_build/`` (and ``DOCS/API/`` when the API pages
  are not committed).
* ``.gitattributes``: ``*.bat text eol=crlf``.
* In a project with Simulink models, libraries or subsystem files:
  ``ROOT/+sphinxcontrib/+matlabdomain/simulinkDocumentationLinker.m`` (the
  MATLAB function that Help links of Simulink files call; rewritten on
  each run) and its settings ``simulinkDocumentationLinker.json`` (written
  once, then kept up to date by HTML builds,
  :confval:`matlab_simulink_autobuild_server`); ``conf.py`` excludes
  ``+sphinxcontrib/``.

Before it writes anything it checks ``git status`` of these three files and
stops if one has uncommitted changes, so ``git restore`` undoes exactly its
edits. Outside a git repository it prints the lines instead. It never
touches the project's MATLAB code or CI, and never commits.

The matlabdomain requirement copies how the running matlabdomain is
installed (``direct_url.json``, PEP 610): a git URL and commit, an editable
folder (``uv add --editable``, ``pip install -e``), another URL, or a
version from an index.

Exit status
~~~~~~~~~~~

0 on success, also with warnings (the index warnings and ``mat.apidoc``,
printed like Sphinx prints them); 1 when ``uv add`` fails or the run is
interrupted; 2 for a usage error and when it stops before writing: ``ROOT``
is not a folder, ``DOCS`` is not inside ``ROOT`` or is in use with
:option:`-q`, ``DOCS/conf.py`` exists without :option:`--force`, one of the
three files has uncommitted changes, or the answers file is missing or
invalid.

``scmd apidoc``
---------------

.. program:: scmd apidoc

Synopsis
~~~~~~~~

.. code-block:: text

   scmd apidoc [--conf-dir CONF_DIR] [--force] [--dry-run] [--check] [--quiet]

Writes reST pages with ``mat:auto*`` directives for the MATLAB files below
the project root: one page per namespace and one for the global namespace
(:confval:`matlab_apidoc_group` ``"namespace"``, the default), or one page
per folder with files (``"folder"``), listed flat on the root page.
:doc:`../user-guide/apidoc` is the tutorial.

Settings
~~~~~~~~

Every setting comes from ``CONF_DIR/conf.py`` (:doc:`configuration`); no
flag overrides one:

The source settings are :confval:`matlab_src_code_project_root` (required),
:confval:`matlab_src_include_patterns`, :confval:`matlab_src_exclude_patterns`,
:confval:`matlab_src_sidecar_suffixes`, :confval:`matlab_version`,
:confval:`matlab_src_encoding` and
:confval:`matlab_simulink_doc_suffixes`.

The command's own settings are :confval:`matlab_apidoc_output_dir` (required),
:confval:`matlab_apidoc_group`, :confval:`matlab_apidoc_page_size`,
:confval:`matlab_apidoc_private`, :confval:`matlab_apidoc_separate`,
:confval:`matlab_apidoc_maxdepth`, :confval:`matlab_apidoc_tocfile`,
:confval:`matlab_apidoc_templatedir` and
:confval:`matlab_apidoc_remove_old`.

Paths in ``conf.py`` are relative to ``CONF_DIR``, which is taken to be
the Sphinx source folder. Errors name the config value that caused them.
For full control, write a script on the Python API
(:ref:`apidoc-write-your-own`).

The command runs ``conf.py`` as ``sphinx-build`` does, but it sets up no
extensions and has no tags. So in a few cases it gets other values than
the build:

* ``conf.py`` tests ``tags`` (``sphinx-build -t NAME``), for example to
  exclude files from a public build;
* the build sets values with ``sphinx-build -D name=value``;
* another extension changes a ``matlab_*`` value while the build runs;
* ``conf.py`` is not in the source folder (``sphinx-build -c``): relative
  paths in it are then relative to the source folder in the build, but to
  ``CONF_DIR`` here.

Then make ``conf.py`` give both the same values (test an environment
variable instead of a tag, for example), or write a script.

Arguments
~~~~~~~~~

.. option:: -c CONF_DIR, --conf-dir CONF_DIR

   The folder of ``conf.py``, usually the Sphinx source folder. Default:
   the current folder. Without a ``conf.py`` there, the command exits
   with 2.

Run-time options
~~~~~~~~~~~~~~~~

.. option:: -f, --force

   Also overwrite files without the marker line. Without it, such files
   are kept, with a ``mat.apidoc`` warning. Files with the marker are
   rewritten whenever their text changes; files are written only then.

.. option:: -n, --dry-run

   Write and remove nothing; list what would change.

.. option:: -k, --check

   A dry run that exits with 1 if a page would be created, rewritten,
   renamed or removed (kept files without the marker do not count).

.. option:: -q, --quiet

   No output on stdout; warnings still go to stderr.

.. option:: -V, --version

   Print the version and exit.

.. option:: -h, --help

   Print the help and exit.

Exit status
~~~~~~~~~~~

0 on success, also with warnings (``mat.apidoc`` and the index warnings,
printed like Sphinx prints them, except those named in
``suppress_warnings``); 1 when :option:`--check` finds a page to
change; 2 for a usage or settings error, such as an invalid pattern,
version or encoding, a missing ``conf.py`` or required value, an error in
``conf.py``, or a ``matlab_*`` name that is not a configuration value (a
typo; :doc:`configuration`). Unknown and abbreviated options (``--dry``
for ``--dry-run``) are usage errors.

Output files
~~~~~~~~~~~~

In the folder :confval:`matlab_apidoc_output_dir` (``OUTPUT_DIR``),
created if needed, with the suffix ``rst`` (``SUFFIX``):

* In namespace grouping, the namespace ``a.b`` gets
  ``OUTPUT_DIR/a.b.SUFFIX`` (further pages ``a.b-2.SUFFIX``, ...) and the
  global namespace ``OUTPUT_DIR/global.SUFFIX``. In folder grouping, the
  folder ``a/+p/`` gets ``OUTPUT_DIR/a/+p/index.SUFFIX``. With
  :confval:`matlab_apidoc_separate`, the file ``a/+p/Cls.m`` also gets
  ``OUTPUT_DIR/a/+p/Cls.m.SUFFIX``. The root page is
  ``OUTPUT_DIR/TOCFILE.SUFFIX`` (:confval:`matlab_apidoc_tocfile`,
  default ``index``).
* Each path segment keeps ``A-Z a-z 0-9 _ . + @ -``; every other character
  becomes ``~XX`` per UTF-8 byte. Windows device names (``CON``, ``NUL``,
  ``COM1``, ...) and a trailing ``.`` get their first or last character
  escaped, and a folder's leading ``_`` is escaped (``_util/`` ->
  ``~5Futil/``), so no output folder starts with ``_``. Siblings whose
  names differ only by case get their uppercase letters escaped, with a
  ``mat.apidoc`` warning.
* Files are UTF-8 with ``\n`` line ends on every system.
* With :confval:`matlab_apidoc_remove_old` (default ``True``), files with
  ``SUFFIX`` below ``OUTPUT_DIR`` that start with the marker line ``..
  Generated by scmd apidoc.`` and are not pages of this run are
  removed, with the folders this leaves empty. Files without the marker,
  files with other suffixes and folders whose names start with ``.`` or
  ``_`` are never touched.

``scmd skills``
---------------

.. program:: scmd skills

Synopsis
~~~~~~~~

.. code-block:: text

   scmd skills list
   scmd skills install [NAME ...] [--dest DIR] [--force]

The package ships agent skills: folders with a ``SKILL.md`` (the `Agent
Skills <https://agentskills.io/>`_ format) and the scripts it uses.
``setting-up-a-project`` sets up documentation with ``scmd quickstart``;
``migrating-from-0x`` migrates a 0.x project (:doc:`../user-guide/migration`).

.. option:: COMMAND

   ``list`` or ``install``.

.. option:: -V, --version

   Print the version and exit.

.. option:: -h, --help

   Print the help and exit.

``scmd skills list``
~~~~~~~~~~~~~~~~~~~~

.. program:: scmd skills list

Prints the name and description of each skill.

.. option:: -h, --help

   Print the help and exit.

``scmd skills install``
~~~~~~~~~~~~~~~~~~~~~~~

.. program:: scmd skills install

Copies skill folders into the project's skill folder, each to
``DIR/NAME``. Agent tools read a project's skills from their own folder:

* GitHub Copilot (VS Code, Copilot CLI): ``.github/skills``, the default;
* Claude: ``.claude/skills``;
* OpenAI Codex: ``.agents/skills``.

Run it from the project root and commit the folders to share them. Run it
again with :option:`--force` after an upgrade of the package.

.. option:: NAME

   The skills to copy. Default: all.

.. option:: -d DIR, --dest DIR

   The project's skill folder. Default: ``.github/skills``.

.. option:: -f, --force

   Replace skill folders that exist. Without it, the command copies
   nothing when one of the folders exists.

.. option:: -h, --help

   Print the help and exit.

Exit status: 0 on success; 1 when a skill folder exists and
:option:`--force` is not given; 2 for a usage error, such as an unknown
skill name.
