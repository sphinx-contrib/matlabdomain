Setting up a project: ``sphinx-matlab-quickstart``
==================================================

``sphinx-matlab-quickstart`` sets up Sphinx documentation for a MATLAB
project that has none yet: a Sphinx source folder with ``conf.py``, a home
page, make files, a build guide and the API pages, the docs dependencies,
and a report of what it found in the project. It is the MATLAB counterpart
of Sphinx's ``sphinx-quickstart``, and it uses the extension's own index,
so its defaults are what the build will see. Run it once; afterwards
``conf.py`` is yours, and ``sphinx-matlab-apidoc`` (:doc:`apidoc`) keeps the
API pages up to date. The options are in :doc:`../reference/cli`.

A first look
------------

Start with a dry run from the project's folder. It writes nothing and
prints what it would write, then the report:

.. code-block:: console

   $ sphinx-matlab-quickstart -n

The report lists:

* the project facts: the MATLAB releases named in the CI files,
  ``matlab.toml`` and the README, whether the project uses uv, how
  matlabdomain itself is installed, the git submodules, and the folders
  that are not on the MATLAB project path;
* the inventory: files by kind, namespaces, duplicate MATLAB names (two
  files, one name: exclude a copy, or keep both, listed by path), files
  MATLAB cannot call, files that are not UTF-8;
* the help headings: which go into ``napoleon_custom_sections``, which are
  napoleon's own, which napoleon cannot match, and which are too rare;
* the copyright and licence blocks that run into the help text: the help
  ends at the first line that is not a comment, so a block right after the
  help, without a blank line between, becomes part of it;
* the next steps.

At the end it asks to save your answers (default yes); the real run reads
them back:

.. code-block:: console

   $ sphinx-matlab-quickstart --answers sphinx-matlab-quickstart.toml

The questions
-------------

Each question shows the detected answer as the default; press Enter to
keep it. With ``-q`` nothing is asked: the answers file, then the
defaults.

.. list-table::
   :header-rows: 1
   :widths: 22 40 38

   * - Key
     - Question
     - Default
   * - ``project``
     - Project name
     - the name of the ``ROOT`` folder
   * - ``author``
     - Author names
     - ``git config user.name``, else "The *project* authors"
   * - ``matlab_version``
     - MATLAB release the code targets
     - the release named most often in the CI files (GitHub, GitLab,
       CircleCI, Travis, Azure, Jenkins), ``matlab.toml`` and the README;
       ``R2024a`` for an older one; ``R2026a`` when none is named
   * - ``group``
     - API pages per namespace or per folder
     - ``"namespace"`` (:confval:`matlab_apidoc_group`)
   * - ``theme``
     - HTML theme
     - ``"furo"``
   * - ``exclude``
     - Folders and files not to document
     - none; the defaults of :confval:`matlab_src_exclusion_patterns` and
       the git submodules are always left out
   * - ``markdown``
     - Markdown pages with MyST
     - yes when ``myst_parser`` can be imported
   * - ``sidecars``
     - Markdown notes next to the code as API pages
     - yes when ``.md`` files sit in folders with MATLAB code
       (:doc:`sidecars`); needs ``markdown``
   * - ``make``
     - Make files through uv or plain
     - ``"uv"`` in a uv project (a ``uv.lock`` or ``[tool.uv]``), else
       ``"plain"``
   * - ``guide``
     - A build guide for contributors (``BUILDING_DOCS.md``)
     - yes
   * - ``api_pages``
     - API pages committed, or generated before each build
     - ``"commit"``
   * - ``napoleon_custom_sections``
     - Use these napoleon_custom_sections
     - the survey of the help headings (below)

.. _quickstart-answers:

The answers file
----------------

A TOML file with any of the keys above. A rerun, or a second project,
asks only for what the file leaves out:

.. code-block:: toml

   project = "My toolbox"
   author = "The My toolbox authors"
   matlab_version = "R2024b"
   group = "namespace"
   theme = "furo"
   exclude = ["tests", "examples/data"]
   markdown = true
   sidecars = true
   make = "uv"
   guide = true
   api_pages = "commit"
   napoleon_custom_sections = [
       ["Inputs", "params_style"],
       "Description",
       ["Input", "Inputs"],
   ]

An unknown key or a wrong value stops the command with exit status 2.

What it detects
---------------

The release
   ``R2024b`` and ``r2024b`` count alike; a tie goes to the newer release.
   It sets :confval:`matlab_version`, which decides MATLAB's naming rules.

Exclusions
   The default patterns, plus the paths in ``.gitmodules``, which
   ``conf.py`` reads when it runs (submodules are separate projects). A
   MATLAB project (``matlab.toml`` ``[folders] path``, or a ``.prj``
   project's ``resources/project`` files) names the folders on the MATLAB
   path; the highest folders with code that are not on it, and the start-up
   and shut-down files, are written into ``conf.py`` as commented-out
   patterns. Uncomment what is not the project's API. Any of the three
   ``.prj`` layouts works (single file, multi-file, fixed-path multi-file);
   a project file that cannot be read, or names no path folder, gives no
   suggestions, and the report says so. A ``startup.m`` is not read.

Help headings
   A heading is a comment line that holds only a label and a colon
   (``% Inputs:``) in a help block. Spellings that differ in case count as
   one, as napoleon matches them. A heading in 10 or more files becomes a
   section; ``Inputs``, ``Outputs``, ``Name Value Pairs`` and ``Options``
   as ``params_style``, so that their ``name: text`` items become
   parameters. Its plural or singular is an alias (``("Input",
   "Inputs")``). Napoleon's own sections (``Args``, ``Returns``,
   ``Examples``, ``See Also``, ...) need no entry; headings with other
   characters than letters, digits, ``_`` and spaces (``Name-Value
   Pairs``) never match, so rename them in the code.

Sidecar docs
   ``.md`` files in a folder with ``.m`` or ``.mlapp`` files, outside the
   Sphinx source folder. Markdown pages elsewhere (an MkDocs site) do not
   count.

The matlabdomain requirement
   Copied from how the running matlabdomain is installed: a git URL and
   commit (``sphinxcontrib-matlabdomain @ git+URL@SHA``), an editable
   folder, another URL, or the installed version from an index
   (``sphinxcontrib-matlabdomain>=X``).

What it writes
--------------

In the Sphinx source folder (``docs`` by default; ``-o`` names another,
inside the project):

``conf.py``
   The extensions (``sphinxcontrib.matlab``, ``sphinx.ext.napoleon``, and
   ``myst_parser`` for Markdown), the project root, the exclusions, the
   release, sidecar docs, the API page settings, every
   :confval:`matlab_api_check_rules` entry set to ``"warning"``, napoleon,
   MyST and the theme. Commented lines show :confval:`matlab_external_names`
   and ``smartquotes``.
``index.rst``
   The project name and a toctree with the API pages (and the build
   guide). The introduction is yours to write.
``Makefile``, ``make.bat``
   ``make html``, ``clean`` and every other Sphinx target, plus
   ``apidoc``, ``apidoc-check`` and ``livehtml`` (``sphinx-autobuild``,
   rebuilding when a page or a MATLAB file changes). In a uv project they
   run everything with ``uv run --frozen --group docs``. ``make.bat`` has
   CRLF line ends.
``BUILDING_DOCS.md``
   A short guide for contributors: set-up, commands, what to do when the
   code changes, the layout.
``_static/.gitkeep``
   Git keeps no empty folder, and Sphinx warns about a missing
   ``_static``.
``API/``
   The API pages, as ``sphinx-matlab-apidoc`` writes them from that
   ``conf.py``.

Outside it, it adds the docs dependencies to ``pyproject.toml`` in a uv
project (``uv add --frozen --group docs``, the dependency group ``docs``),
``DOCS/_build/`` to ``.gitignore`` and ``*.bat text eol=crlf`` to
``.gitattributes``, each only if missing. It checks ``git status`` of these
three files first and stops if one has uncommitted changes, so ``git
restore`` undoes exactly its edits; outside git, it prints the lines
instead. Without uv it prints the ``pip install`` line. It never touches
``uv.lock``, MATLAB code or CI, and never commits. (``uv add`` writes
``pyproject.toml`` with LF line ends, so a CRLF file shows as changed on
every line.)

A ``DOCS`` folder that exists with files but no ``conf.py`` is in use (an
MkDocs ``docs/``): the command asks for another folder. One with a
``conf.py`` stops it; ``--force`` rewrites the files above and leaves
everything else.

Next steps
----------

The report ends with them:

#. ``uv lock`` and ``uv sync --group docs`` (or the printed ``pip
   install``).
#. Write the introduction in ``index.rst``.
#. A clean build with ``-n`` (``make clean html SPHINXOPTS="-n"``), then
   fix or explain each warning (:doc:`warnings`). The strict build
   (``-n -W``) is the CI build.
#. ``make apidoc-check`` in CI, when the API pages are committed.
#. ``make matlab-api-check``, the help-text audit (:doc:`api-check`).

Not automated: edits to the MATLAB code (help-text fixes, copyright
blocks: only reported), the lock file, external names and intersphinx
(they need a build's warnings), CI and publishing, commits.
