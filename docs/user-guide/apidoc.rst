Generating pages: ``sphinx-matlab-apidoc``
==========================================

``sphinx-matlab-apidoc`` writes reST pages that document every MATLAB file
below a project root with the auto directives, one page per folder. A large
project then needs no hand-written directives, and new files appear in the
docs when you run it again. It is the MATLAB counterpart of Sphinx's
``sphinx-apidoc``, with a deliberately small surface: its settings come
from ``conf.py``, and its flags only control a run. For different output,
edit its templates or write your own script on its Python API
(:ref:`apidoc-write-your-own`); that makes sense when you want
fine-grained control over the generated output.

A worked example
----------------

The repository's ``examples/apidoc`` folder is a complete example: a small
MATLAB project, its Sphinx project with the generated pages, and an edited
copy of the templates. The test suite regenerates the pages, compares them
with the committed ones and builds the project with ``-W``, so everything
shown here is current.

.. code-block:: text

   examples/apidoc/
       src/                      the MATLAB project (ROOT)
           +demo/
               Contents.m        folder help (left out of the pages)
               README.md         the introduction of the namespace's page
               getting-started.md  a Markdown sidecar doc
               img/shapes.svg    its image
               +geometry/
                   Point.m       class demo.geometry.Point
                   distance.m    function demo.geometry.distance
               @Shape/           class folder: class demo.Shape
                   Shape.m
                   area.m        a method in its own file
                   scale.m
           utils/                a plain folder: global functions
               clamp.m
               lerp.m
               notes.rst         a reST sidecar doc
               private/
                   check_range.m
           run_demo.m            a script
           DemoApp.mlapp         an App Designer app
       docs/                     the Sphinx project
           conf.py
           index.rst
           api/                  generated
       templates/                edited copies of the default templates
       make_api.py               the same pages from a script

``docs/conf.py`` points :confval:`matlab_src_code_project_root` at the
project, turns on :doc:`sidecar docs <sidecars>` and tells
``sphinx-matlab-apidoc`` where to write the pages and which templates to
use:

.. literalinclude:: ../../examples/apidoc/docs/conf.py
   :language: python

Generate the pages in the folder of ``conf.py`` (from elsewhere, name that
folder with ``-c``, ``--conf-dir``):

.. code-block:: console

   $ cd examples/apidoc/docs
   $ sphinx-matlab-apidoc

This writes one page per folder into ``api/``, mirroring the folder tree,
and one per sidecar doc:

.. code-block:: text

   api/
       index.rst                 the root folder
       +demo/index.rst
       +demo/getting-started-md.rst
       +demo/+geometry/index.rst
       utils/index.rst
       utils/notes-rst.rst
       utils/private/index.rst

Add the root page to a toctree, here in ``docs/index.rst``:

.. literalinclude:: ../../examples/apidoc/docs/index.rst
   :language: rst

and build as usual:

.. code-block:: console

   $ sphinx-build -M html . _build

The generated page of the ``+demo`` namespace:

.. literalinclude:: ../../examples/apidoc/docs/api/+demo/index.rst
   :language: rst

and of the plain folder ``utils/``:

.. literalinclude:: ../../examples/apidoc/docs/api/utils/index.rst
   :language: rst

What the pages contain
----------------------

* One page per folder that has a file to document at or below it. The page
  of the root folder is the toc file (``index`` by default) and is always
  written.
* The title is the folder's signature: ``namespace demo`` for a ``+``
  folder, ``folder utils/`` for a plain folder, ``folder ./`` for the root.
* Each page has ``mat:autofolder`` (without ``:members:``), a local table of
  contents, and sections in this order: Classes, Functions, Scripts, Apps.
  Within a section, entries are sorted by title, ignoring case.
* Each file gets a heading, its MATLAB name (or its path when MATLAB cannot
  call it), and an auto directive with its full path reference:
  ``mat:autoclass`` with ``:members:``, ``:undoc-members:`` and
  ``:show-inheritance:``, ``mat:autofunction``, ``mat:autoscript`` or
  ``mat:autoapplication``. With ``-n``, a class whose base is one of
  MATLAB's own classes (``< handle``) gives a "reference target not found"
  warning; :doc:`documenting` shows the ``nitpick_ignore_regex`` that
  silences it. Sphinx also adds documented classes to the local table of
  contents, so a class appears there twice (its heading and its signature);
  ``toc_object_entries = False`` in ``conf.py`` hides the second.
* A "Folders" toctree lists the pages of the subfolders: namespaces, then
  plain folders, then ``private/``.
* Class folders get no page of their own: their class is listed on the page
  of the folder above. The function files of a class folder ``@X/`` whose
  ``X.m`` is a ``classdef`` are its methods and are not listed separately.
  In any other ``@`` folder (an old-style class, a ``classdef`` with another
  name, no class file), every file is listed.
* ``Contents.m`` and the other special files (:doc:`help-text`) are left
  out. Files MATLAB cannot call are included, by path; files that cannot be
  read are left out with a ``mat.apidoc`` warning.
* With :confval:`matlab_src_sidecar_suffixes`, each sidecar doc gets a
  page of its own, listed in a "Sidecar docs" section before "Folders", and
  a folder's README introduces the folder's page (:doc:`sidecars`).

Settings
--------

The generator indexes the files exactly as the build does (the same
patterns, MATLAB names, types and warnings), but it does not parse them.
It runs ``conf.py`` as ``sphinx-build`` does and reads:

* the source settings: :confval:`matlab_src_code_project_root`,
  :confval:`matlab_src_include_patterns`,
  :confval:`matlab_src_exclusion_patterns`, :confval:`matlab_version`,
  :confval:`matlab_namelengthmax`, :confval:`matlab_src_encoding` and
  :confval:`matlab_src_sidecar_suffixes`;
* its own settings, which the build ignores:

  .. list-table::
     :header-rows: 1

     * - Value
       - Default
       - Sets
     * - :confval:`matlab_apidoc_output_dir`
       - required
       - the folder for the pages
     * - :confval:`matlab_apidoc_separate`
       - ``False``
       - one page per file
     * - :confval:`matlab_apidoc_maxdepth`
       - ``4``
       - the ``:maxdepth:`` of the toctrees
     * - :confval:`matlab_apidoc_tocfile`
       - ``"index"``
       - the name of the root folder's page
     * - :confval:`matlab_apidoc_suffix`
       - ``"rst"``
       - the suffix of the files
     * - :confval:`matlab_apidoc_templatedir`
       - ``None``
       - a folder of templates that replace the defaults
     * - :confval:`matlab_apidoc_remove_old`
       - ``True``
       - remove marked pages that are no longer pages

Paths in ``conf.py`` are relative to its folder. No flag overrides a
setting, so the command and the build agree; :doc:`../reference/cli`
lists the few cases where they can still differ. The flags only control a
run: ``-f``, ``-n``, ``--check`` and ``-q``.

Output file names
-----------------

The output tree mirrors the folder tree: the folder ``a/+p/`` gets
``a/+p/index.rst``. Characters other than ``A-Z a-z 0-9 _ . + @ -`` in a
folder or file name become ``~XX`` per UTF-8 byte (``my folder`` becomes
``my~20folder``), so names are safe in URLs on every system. Windows device
names (``CON``, ``NUL``, ...) and sibling folders whose names differ only by
case are escaped too, the latter with a ``mat.apidoc`` warning.

Running it again
----------------

Run it whenever the MATLAB files change; the pages stay accurate:

* Every generated file starts with the marker line ``.. Generated by
  sphinx-matlab-apidoc.``. A marked page whose text changed is rewritten.
  Files are written only when their text changes, so Sphinx does not read
  unchanged pages again.
* Marked files below the output folder that are no longer pages (of
  deleted or moved folders) are deleted, with the folders this leaves
  empty; :confval:`matlab_apidoc_remove_old` = ``False`` keeps them. Files
  without the marker are never deleted.
* To edit a generated page by hand, delete its marker line: the page is
  then kept, with a ``mat.apidoc`` warning. ``-f`` (``--force``)
  overwrites such files too.
* ``-n`` (``--dry-run``) changes nothing and lists what would change.
  ``--check`` does the same and exits with 1 if a page would be created,
  rewritten, renamed or deleted.

The exit status is 0 on success, also with warnings, 1 when ``--check``
finds a change, and 2 for a usage or settings error. All flags:
:doc:`../reference/cli`.

Run it before each build
------------------------

The build does not run the generator; run it first. ``sphinx-build``
finds the new pages as usual.

A ``Makefile`` target (Sphinx's ``Makefile`` passes other targets to
``sphinx-build``; recipe lines start with a tab):

.. code-block:: make

   .PHONY: apidoc
   html: apidoc
   	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

   apidoc:
   	sphinx-matlab-apidoc -q -c "$(SOURCEDIR)"

Read the Docs: add a ``pre_build`` job to the ``build`` section of
``.readthedocs.yaml``:

.. code-block:: yaml

   build:
     jobs:
       pre_build:
         - sphinx-matlab-apidoc -c docs

To commit the generated pages, as the example does, check in CI that they
are current:

.. code-block:: console

   $ sphinx-matlab-apidoc --check -c docs

or in a `pre-commit <https://pre-commit.com/>`_ hook, an entry under
``repos:`` in ``.pre-commit-config.yaml``:

.. code-block:: yaml

   - repo: local
     hooks:
       - id: sphinx-matlab-apidoc
         name: API pages are current
         entry: sphinx-matlab-apidoc --check -q -c docs
         language: system
         pass_filenames: false
         always_run: true

With ``make livehtml`` (sphinx-autobuild), run the generator first and add
``--watch`` for the MATLAB folder; a source change then needs another run
of the generator.

Customizing the output
----------------------

The pages come from three `Jinja <https://jinja.palletsprojects.com/>`_
templates: ``folder.rst.jinja`` (one folder page), ``object.rst.jinja``
(one file's page, with :confval:`matlab_apidoc_separate`) and
``sidecar.rst.jinja`` (one sidecar doc's page). To change them:

1. copy the defaults from ``sphinxcontrib/matlab_apidoc/templates/`` in the
   installed package (or the example's copies) into your project;
2. edit them;
3. set :confval:`matlab_apidoc_templatedir` to their folder. A template
   missing there falls back to the default.

The example's ``folder.rst.jinja`` titles the root page "Demo API
reference" and leaves out ``:undoc-members:``:

.. literalinclude:: ../../examples/apidoc/templates/folder.rst.jinja
   :language: jinja

The variables a template can use are listed in
:doc:`../reference/templates`. They are a public interface: new variables
may be added, but renaming or removing one is a breaking change.

.. _apidoc-write-your-own:

Write your own
--------------

For full control (several project roots, settings computed per folder,
pages written next to other generated files), write a short script on the
Python API that the command itself uses. The example's ``make_api.py``
writes the same pages as ``sphinx-matlab-apidoc -c docs``; the test suite
checks that it does:

.. literalinclude:: ../../examples/apidoc/make_api.py
   :language: python

It takes three steps:

1. ``sphinxcontrib.mat_types.IndexSettings`` says what to index: ``root``
   (an absolute path), ``include`` and ``exclude`` (tuples of patterns as
   in :confval:`matlab_src_include_patterns`, with ``/``, relative to the
   root), ``encoding``, ``matlab_version``, ``namelengthmax``,
   ``sidecar_suffixes``, ``source_dir`` (the Sphinx source folder) and
   ``cache_text`` (keep the text read for a later parse). The defaults
   are those of the build.
2. ``sphinxcontrib.mat_types.build_index(settings)`` indexes the files, as
   the build does, and returns a ``SourceIndex``.
3. ``sphinxcontrib.matlab_apidoc.generate(source_index, options)`` writes
   the pages. ``ApidocOptions`` has a field for each ``matlab_apidoc_*``
   value (``output_dir``, ``separate``, ``maxdepth``, ``tocfile``,
   ``suffix``, ``templatedir``, ``remove_old``; paths as given, not
   relative to ``conf.py``) and for the flags ``-f`` and ``-n``
   (``force``, ``dry_run``).
   It returns a ``Result``: ``pages`` (the docnames, without suffix), the
   lists of files ``created``, ``updated``, ``unchanged``, ``kept`` and
   ``removed`` and of files and folders ``renamed`` (paths relative to the
   output folder), and ``changed``, true when a file was (or with
   ``dry_run`` would be) written, renamed or removed.

Warnings go through Python's ``logging`` (the ``sphinx`` loggers); without
a handler, Python prints them on stderr. For more than this, the generator
is a small package (``sphinxcontrib/matlab_apidoc/``) to copy. Options for
every layout preference are deliberately not offered.
