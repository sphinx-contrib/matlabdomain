Generating pages: ``scmd apidoc``
=================================

``scmd apidoc`` writes :term:`reST` pages that document every MATLAB file
below a project root with the auto :term:`directives <directive>`: by default one page per
namespace, as MATLAB sees namespaces, or one page per folder. A large
project then needs no hand-written directives, and new files appear in the
docs when you run it again. It is the MATLAB counterpart of Sphinx's
``sphinx-apidoc``, with a deliberately small surface: its settings come
from ``conf.py``, and its flags only control a run. For different output,
edit its templates or write your own script on its Python :term:`API`
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
               README.md         a Markdown sidecar doc
               getting-started.md  another one
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
``scmd apidoc`` where to write the pages and which templates to
use:

.. literalinclude:: ../../examples/apidoc/docs/conf.py
   :language: python

Generate the pages from the repository root, naming the folder of
``conf.py`` with ``--conf-dir``:

.. code-block:: console

   $ uv run scmd apidoc --conf-dir examples/apidoc/docs

This writes one page per namespace into ``api/``, one for the files
outside any namespace (``global``), and the root page that lists them:

.. code-block:: text

   api/
       index.rst                 the root page
       global.rst                utils/, run_demo.m, DemoApp.mlapp
       demo.rst                  namespace demo
       demo.geometry.rst         namespace demo.geometry

Add the root page to a :term:`toctree`, here in ``docs/index.rst``:

.. literalinclude:: ../../examples/apidoc/docs/index.rst
   :language: rst

and build as usual:

.. code-block:: console

   $ uv run sphinx-build -M html examples/apidoc/docs examples/apidoc/docs/_build

The root page and the page of the ``demo`` namespace:

.. literalinclude:: ../../examples/apidoc/docs/api/index.rst
   :language: rst

.. literalinclude:: ../../examples/apidoc/docs/api/demo.rst
   :language: rst

What the pages contain
----------------------

With :confval:`matlab_apidoc_group` ``"namespace"`` (the default):

* One page per namespace that has a file or sidecar doc to document,
  whatever folders it is spread over: ``a/+ns/`` and ``b/+ns/`` make one
  namespace ``ns``, as in MATLAB. Its title is ``namespace ns``.
* One page for the global namespace, titled ``Global``: the files outside
  any namespace, in plain folders at any depth.
* Each page has a local table of contents and sections in this order:
  Functions, Classes, Scripts, Apps, Simulink Models, Simulink Libraries,
  Simulink Subsystem References, Simulink Library Blocks, Sidecar docs.
  Within a section, entries are sorted by title, ignoring case.
* A page holds at most :confval:`matlab_apidoc_page_size` entries (100 by
  default; sidecar docs count). A longer namespace gets several pages,
  titled with the range they hold: ``namespace ns (1-100)``,
  ``namespace ns (101-200)``, ``namespace ns (201-253)``. Adding or
  removing a file can move the entries after it to another page, and so
  change their address (:ref:`library-changes`).
* The root page (the toc file, ``index`` by default, always written) has
  one flat toctree: Global first, then the namespaces sorted by name,
  ignoring case. Nested namespaces are listed like the others
  (``demo``, ``demo.geometry``), so the navigation stays one level deep.
* Files in ``private/`` folders are left out (only the files of their
  folder can call them); with :confval:`matlab_apidoc_private` ``= True``
  they are listed on the page of the folder above (its namespace, or
  Global). Sidecar docs are rendered on the page of their
  namespace in the "Sidecar docs" section, each with its own title; one in
  ``private/`` goes with the folder above it.
* When two files of one page have the same MATLAB name (two folders with a
  ``utils.m`` on one path), both are listed, titled by path, with a
  ``mat.apidoc`` warning.

With ``"folder"``:

* One page per folder that has a file or sidecar doc to document; a
  folder with nothing of its own gets no page. The root folder's page is
  ``root``.
* The root page (the toc file) has one flat toctree, as in namespace
  grouping: the root folder's page first, then the folders sorted by path,
  ignoring case, so the navigation stays one level deep.
* The title is the folder's path: ``folder +demo/``, ``folder utils/``,
  ``folder ./`` for the root. A namespace spread over several folders
  (``a/+ns/``, ``b/+ns/``) gets a page per folder, each with its own title;
  the ``mat:autofolder`` signature still shows ``namespace ns``.
  The page has ``mat:autofolder`` (without ``:members:``), a local table of
  contents, and sections in this order: Classes, Functions, Scripts, Apps,
  then the Simulink sections as in namespace grouping.
  A long folder gets several pages, split at
  :confval:`matlab_apidoc_page_size` entries like a namespace
  (``folder utils/ (101-200)``). ``private/``
  files are left out by default; :confval:`matlab_apidoc_private`
  ``= True`` includes them on folder pages.
* With :confval:`matlab_src_sidecar_suffixes`, each sidecar doc gets a
  page of its own, listed in a "Sidecar docs" section, and a folder's
  README introduces the folder's page (:doc:`sidecars`).

In both:

* Simulink libraries are read for their masked blocks (the only files
  apidoc reads): each gets an entry in Simulink Library Blocks, titled
  ``library/Group/Block``. A library that cannot be read gets a
  ``mat.apidoc`` warning and no block entries.
* Each file gets a heading, its MATLAB name (or its path when MATLAB cannot
  call it), and an auto directive with its full path reference:
  ``mat:autoclass`` with ``:members:``, ``:undoc-members:`` and
  ``:show-inheritance:``, ``mat:autofunction``, ``mat:autoscript`` or
  ``mat:autoapplication``. A base class that is one of MATLAB's own
  (``< handle``) is shown as text (:confval:`matlab_external_names`).
  Sphinx also adds documented classes to the local table of
  contents, so a class appears there twice (its heading and its signature);
  ``toc_object_entries = False`` in ``conf.py`` hides the second.
* Class folders get no page of their own: their class is listed with the
  files of the folder above (its namespace). The function files of a class
  folder ``@X/`` whose ``X.m`` is a ``classdef`` are its methods and are
  not listed separately. In any other ``@`` folder (an old-style class, a
  ``classdef`` with another name, no class file), every file is listed
  (old-style classes are not supported, see :doc:`documenting`).
* ``Contents.m`` and the other special files (:doc:`help-text`) are left
  out. Files MATLAB cannot call are included, by path; files that cannot be
  read are left out with a ``mat.apidoc`` warning.

Settings
--------

The generator indexes the files exactly as the build does (the same
patterns, MATLAB names, types and warnings), but it does not parse them.
It runs ``conf.py`` as ``sphinx-build`` does and reads:

* the source settings: :confval:`matlab_src_code_project_root`,
  :confval:`matlab_src_include_patterns`,
  :confval:`matlab_src_exclude_patterns`, :confval:`matlab_version`,
  :confval:`matlab_src_encoding` and
  :confval:`matlab_src_sidecar_suffixes`;
* ``suppress_warnings``: the warnings it names are not printed
  (:doc:`warnings`);
* its own settings, which the build ignores:

  .. list-table::
     :header-rows: 1

     * - Value
       - Default
       - Sets
     * - :confval:`matlab_apidoc_output_dir`
       - required
       - the folder for the pages
     * - :confval:`matlab_apidoc_group`
       - ``"namespace"``
       - one page per namespace, or ``"folder"``
     * - :confval:`matlab_apidoc_page_size`
       - ``100``
       - the most entries on one namespace or folder page
     * - :confval:`matlab_apidoc_private`
       - ``False``
       - list ``private/`` files
     * - :confval:`matlab_apidoc_separate`
       - ``False``
       - one page per file
     * - :confval:`matlab_apidoc_maxdepth`
       - ``4``
       - the ``:maxdepth:`` of the toctrees
     * - :confval:`matlab_apidoc_tocfile`
       - ``"index"``
       - the name of the root page
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

Namespace pages are named by the namespace (``demo.geometry.rst``); its
further pages get ``-2``, ``-3`` (``demo.geometry-2.rst``). The global
namespace's page is ``global.rst`` (``global`` is a MATLAB keyword, so no
namespace has that name). Namespaces whose names differ only by case, and a
namespace named like the toc file or like a page of
:confval:`matlab_apidoc_separate`, are escaped as below.

Folder pages and the pages of :confval:`matlab_apidoc_separate` follow the
folder tree: the folder ``a/+p/`` gets ``a/+p/index.rst`` (further pages
``a/+p/index-2.rst``), and the root folder ``root.rst`` (``~72oot.rst`` if
the toc file is ``root``). Characters other than ``A-Z a-z 0-9 _ . + @ -`` in a
folder or file name become ``~XX`` per UTF-8 byte (``my folder`` becomes
``my~20folder``), so names are safe in URLs on every system. Windows device
names (``CON``, ``NUL``, ...) and sibling folders whose names differ only by
case are escaped too, the latter with a ``mat.apidoc`` warning.
If a folder would have the same output path as a generated page file, its
last dot is escaped too: ``guide-md.rst/`` next to ``guide.md`` becomes
``guide-md~2Erst/``, leaving ``guide-md.rst`` for the sidecar page.

Running it again
----------------

Run it whenever the MATLAB files change; the pages stay accurate:

* Every generated file starts with the marker line ``.. Generated by
  scmd apidoc.``. A marked page whose text changed is rewritten.
  Files are written only when their text changes, so Sphinx does not read
  unchanged pages again. Line endings do not count: pages checked out with
  CRLF (git ``core.autocrlf`` on Windows) are unchanged.
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
``sphinx-build``):

.. code-block:: text

   .PHONY: apidoc
   html: apidoc ; @$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
   apidoc: ; uv run scmd apidoc --quiet --conf-dir "$(SOURCEDIR)"

Read the Docs: add a ``pre_build`` job to the ``build`` section of
``.readthedocs.yaml``. It runs in the environment Read the Docs installed
the documentation's requirements into, so it needs no ``uv run``:

.. code-block:: yaml

   build:
     jobs:
       pre_build:
         - scmd apidoc --conf-dir docs

To commit the generated pages, as the example does, check in CI that they
are current:

.. code-block:: console

   $ uv run scmd apidoc --check --conf-dir docs

or in a `pre-commit <https://pre-commit.com/>`_ hook, an entry under
``repos:`` in ``.pre-commit-config.yaml``:

.. code-block:: yaml

   - repo: local
     hooks:
       - id: scmd-apidoc
         name: API pages are current
         entry: uv run scmd apidoc --check --quiet --conf-dir docs
         language: system
         pass_filenames: false
         always_run: true

With ``make livehtml`` (sphinx-autobuild), add ``--watch`` for the MATLAB
folder and run the generator with ``--pre-build`` (:doc:`builds`).

Customizing the output
----------------------

The pages come from `Jinja <https://jinja.palletsprojects.com/>`_
templates: ``namespace.rst.jinja`` (one page of a namespace) and
``root.rst.jinja`` (the root page) in namespace grouping,
``folder.rst.jinja`` (one folder page) and ``sidecar.rst.jinja`` (one
sidecar doc's page) in folder grouping, and ``object.rst.jinja`` (one
file's page, with :confval:`matlab_apidoc_separate`). To change them:

1. copy the defaults from ``sphinxcontrib/matlab_apidoc/templates/`` in the
   installed package (or the example's copies) into your project;
2. edit them;
3. set :confval:`matlab_apidoc_templatedir` to their folder. A template
   missing there falls back to the default.

The example's ``root.rst.jinja`` titles the root page "Demo API
reference":

.. literalinclude:: ../../examples/apidoc/templates/root.rst.jinja
   :language: jinja

and its ``namespace.rst.jinja`` leaves out ``:undoc-members:``:

.. literalinclude:: ../../examples/apidoc/templates/namespace.rst.jinja
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
writes the same pages as ``scmd apidoc --conf-dir docs``; the test suite
checks that it does:

.. literalinclude:: ../../examples/apidoc/make_api.py
   :language: python

It takes three steps:

1. ``sphinxcontrib.mat_types.IndexSettings`` says what to index: ``root``
   (an absolute path), ``include`` and ``exclude`` (tuples of patterns as
   in :confval:`matlab_src_include_patterns`, with ``/``, relative to the
   root), ``encoding``, ``matlab_version``, ``sidecar_suffixes`` and
   ``source_dir`` (the Sphinx source folder). The defaults are those of
   the build.
2. ``sphinxcontrib.mat_types.build_index(settings)`` indexes the files, as
   the build does, and returns a ``SourceIndex``.
3. ``sphinxcontrib.matlab_apidoc.generate(source_index, options)`` writes
   the pages. ``ApidocOptions`` has a field for each ``matlab_apidoc_*``
   value (``output_dir``, ``group``, ``page_size``, ``private``, ``separate``,
   ``maxdepth``, ``tocfile``, ``templatedir``, ``remove_old``;
   paths as given, not relative to ``conf.py``), for the file suffix
   (``suffix``, default ``"rst"``) and for the flags ``-f``
   and ``-n`` (``force``, ``dry_run``).
   It returns a ``Result``: ``pages`` (the docnames, without suffix), the
   lists of files ``created``, ``updated``, ``unchanged``, ``kept`` and
   ``removed`` and of files and folders ``renamed`` (paths relative to the
   output folder), and ``changed``, true when a file was (or with
   ``dry_run`` would be) written, renamed or removed.

Warnings go through Python's ``logging`` (the ``sphinx`` loggers); without
a handler, Python prints them on stderr. For more than this, the generator
is a small package (``sphinxcontrib/matlab_apidoc/``) to copy. Options for
every layout preference are deliberately not offered.
