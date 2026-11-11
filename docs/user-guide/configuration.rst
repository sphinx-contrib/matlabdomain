Configuration
=============

All settings go in ``conf.py``. They start with ``matlab_``;
:doc:`../reference/configuration` lists every one with its type and default.
This page explains how to use them.

The project root
----------------

:confval:`matlab_src_code_project_root` is the folder all MATLAB code lives
below:

.. code-block:: python

   matlab_src_code_project_root = "../src"

* A relative path is relative to the Sphinx :term:`source folder <source directory>` (the folder with
  ``index.rst`` that you pass to ``sphinx-build``; usually ``conf.py`` is
  there too), so the docs build the same from any working
  folder and with `sphinx-multiversion
  <https://github.com/sphinx-contrib/multiversion>`_. An absolute path works
  too, except with sphinx-multiversion: every version would document the
  code of the checkout (:doc:`projects-and-versions`).
* Every :term:`object` is identified by its path below this folder, its *path
  reference* (``+shapes/Circle.m``, see :doc:`referencing`). Choose the root
  once: moving it changes every reference, link anchor and :term:`inventory` entry.
* Without it, no file is indexed and the auto :term:`directives <directive>` (``mat:autoclass``
  and the others) find nothing; each one warns. Description directives
  (``.. mat:function:: f(x)``, :doc:`documenting`) never read a file, so
  they work the same with or without it.

Use the folder you would add to the MATLAB path, or the folder above several
such folders (``src/`` with ``toolbox/`` and ``examples/`` below it). Plain
folders put files into the global namespaces, as in MATLAB: ``toolbox/f.m`` is
the global function ``f``.

Selecting files
---------------

By default every file below the root is indexed. Two lists of glob patterns
change that; both are relative to the root and use ``/``:

.. code-block:: python

   matlab_src_include_patterns = ["toolbox/**", "examples/*.m"]
   matlab_src_exclude_patterns = ["**/tests/**", "**/private/**"]

* :confval:`matlab_src_include_patterns` (default ``["**/*"]``): a file is
  indexed if its path reference matches one of them. ``[]`` selects nothing.
* :confval:`matlab_src_exclude_patterns`: files and folders that match
  one of them are left out; an excluded folder is not searched. The default
  leaves out ``README.*``, ``CHANGES.*``, ``CHANGELOG.*``, ``LICENSE.*``,
  ``CONTRIBUTING.*``, ``CODE_OF_CONDUCT.*`` and ``SECURITY.*`` at the root
  (they matter for :doc:`sidecar docs <sidecars>`); your own list
  replaces it, so add them to it if you want to keep leaving them out.

Exclude wins over include: a file that matches both lists is left out.

Patterns match like Sphinx's ``exclude_patterns``: ``**`` matches across
folders, ``*`` and ``?`` within one folder, and ``**/x`` also matches ``x``
itself, so ``**/tests`` leaves out every ``tests`` folder with everything
below it. Matching is case-sensitive on every system. Patterns and names
are compared in Unicode NFC form, so ``é`` typed as one character matches a
name stored as ``e`` and an accent (as macOS may store it), and the other
way round.

Examples, for a project root with these files:

.. code-block:: text

   main.m
   +mypkg/a.m
   +mypkg/+sub/b.m
   apps/Viewer.mlapp
   data/case1.m
   examples/demo1.m
   examples/advanced/demo2.m
   toolbox/f.m
   toolbox/fTest.m
   toolbox/legacy_util.m
   toolbox/+pkg/C.m
   toolbox/+pkg/private/h.m
   toolbox/data/big.m
   toolbox/internal/g.m
   toolbox/tests/test_f.m

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Patterns
     - Indexed
   * - include ``["toolbox/**"]``
     - every file below ``toolbox/``, at any depth
   * - include ``["toolbox/**", "examples/**"]``
     - every file below ``toolbox/`` and ``examples/``
   * - include ``["examples/*.m"]``
     - ``examples/demo1.m`` only: ``*`` stays in one folder
   * - include ``["+mypkg/**"]``
     - the namespace ``mypkg`` with its inner namespaces
   * - include ``["**/*.m"]``
     - every ``.m`` file, also ``main.m`` at the root; no ``.mlapp``
   * - exclude ``["**/tests"]``
     - all but ``toolbox/tests/test_f.m``: the folder is not searched
   * - exclude ``["**/test_*.m", "**/*Test.m"]``
     - all but the test files ``test_f.m`` and ``fTest.m``, wherever they
       are
   * - exclude ``["**/data"]``
     - all but ``data/case1.m`` and ``toolbox/data/big.m``
   * - exclude ``["**/private"]``
     - all but ``toolbox/+pkg/private/h.m``; links to private functions
       then find nothing
   * - exclude ``["**/*.mlapp"]``
     - all but ``apps/Viewer.mlapp``
   * - exclude ``["toolbox/legacy_util.m"]``
     - all but that one file
   * - include ``["toolbox/**"]``, exclude ``["toolbox/internal"]``
     - ``toolbox/`` without ``toolbox/internal/``

These are configuration errors (``ConfigError``), reported when the build
starts (Sphinx prints "Configuration error!" and the message on the last
line of a short traceback):

* changing either list from its default without
  :confval:`matlab_src_code_project_root`;
* a pattern that is absolute, has a drive (``C:``, ``\\server``) or a
  ``\``, is empty, or uses ``..`` to leave the root or after a wildcard
  (``src/../+pkg/*.m`` is fine: it means ``+pkg/*.m``);
* a list that is not a list or tuple;
* a pattern whose leading folders lead out of the root through a link.

Some files and folders are never indexed or need care:

* Folders whose names start with ``.`` are never searched (``.git``), nor
  is Sphinx output: the ``_build`` folder of the Sphinx source folder, and
  any folder with a ``.buildinfo`` or ``environment.pickle`` file, with
  both ``objects.inv`` and ``searchindex.js`` (HTML output, also a copy
  made with ``cp -r html/* public/``, which leaves out ``.buildinfo``), or
  with a ``doctrees`` folder that has ``environment.pickle`` (the output of
  another layout, such as ``build/``). Folders whose names start with
  ``_`` are searched like any other; exclude those without MATLAB code
  (``**/_assets/**``) when they are large.
* A link or Windows junction below the root that points outside it is left
  out, with one ``mat.outside_root`` warning. Links that stay inside the
  root are followed, and the files they lead to are documented at both
  paths, except a link to the folder it is in or to a folder above it (up
  to the root): it would repeat that folder without end, so it is not
  followed, with one ``mat.link_cycle`` warning.
* Two names in one folder that differ only by Unicode form (``é`` as one
  character and as ``e`` and an accent) have the same path reference; the
  first in the order of the names on disk is indexed, the other gets a
  ``mat.parse_error`` warning that shows both names with escapes.
* Generated data files can be large and slow to parse; exclude them
  (``**/data/**``) when they need no documentation.
* Git submodules below the root are indexed like any folder when they are
  checked out, and are empty folders when not. A project that documents
  submodules separately can read their paths from ``.gitmodules`` in
  ``conf.py``, so the list stays in step with the repository:

  .. code-block:: python

     import configparser
     import os


     def _submodule_paths(gitmodules):
         parser = configparser.ConfigParser()
         parser.read(gitmodules, encoding="utf-8")
         return [parser[s]["path"] for s in parser.sections() if "path" in parser[s]]


     matlab_src_code_project_root = ".."
     matlab_src_exclude_patterns = [
         "README.*",  # ... the rest of the default list
         *_submodule_paths(os.path.join(os.path.dirname(__file__), "..", ".gitmodules")),
     ]

  A helper's name must not start with ``matlab_`` (that prefix is kept for
  configuration values).

``scmd apidoc`` reads the same root and patterns from
``conf.py``; no option overrides them (:doc:`apidoc`).

The MATLAB release
------------------

:confval:`matlab_version` (default ``"R2026a"``) is the release the code is
written for. It sets the defaults of release-dependent rules:

* The longest valid name: 2048 from R2025a on, 63 before.
* Whether scripts and functions in a subfolder of a class folder
  (``@C/sub/x.m``) can be called: before R2026a they can, from R2026a on they
  cannot (they are then documented by path, with a ``mat.not_callable``
  warning).

The oldest supported release is R2024a; an older one, or a value that is not
``R<year>a`` or ``R<year>b``, is a configuration error.

File encoding
-------------

Files are read like MATLAB R2026a reads them:

1. a byte-order mark selects UTF-8, UTF-16 or UTF-32;
2. otherwise :confval:`matlab_src_encoding`, a Python codec name such as
   ``"cp1252"`` or ``"shift_jis"``, if set;
3. otherwise UTF-8. A file that is not valid UTF-8 is read with the Windows
   ANSI code page on Windows and as ISO-8859-1 (Latin-1) elsewhere, with one
   ``mat.encoding`` warning that gives the line of the first invalid byte.

Set :confval:`matlab_src_encoding` when a project uses one legacy encoding
throughout, so that Windows and Linux builds read it the same way. An
unknown codec is a configuration error.

How things are shown
--------------------

* :confval:`matlab_show_property_default_value` (default ``True``): show a
  property's default value after its name (``Radius = 1``), and the
  constructor arguments of an enumeration value (``Red (1, 0, 0)``).
* :confval:`matlab_show_property_specs` (default ``True``): show a
  property's size, class and validators (``Radius (1,1) double
  {mustBePositive}``).
* :confval:`matlab_class_signature` (default ``False``): show the
  constructor's arguments in the class signature. In the sample project
  (:doc:`documenting`):

  .. list-table::
     :header-rows: 1

     * - Class
       - ``False``
       - ``True``
     * - ``Circle``, constructor ``Circle(radius)``
       - ``class shapes.Circle``
       - ``class shapes.Circle(radius)``
     * - ``Polygon`` (class folder), constructor ``Polygon(x, y)``
       - ``class shapes.Polygon``
       - ``class shapes.Polygon(x, y)``
     * - ``Shape``, no constructor
       - ``class shapes.Shape``
       - ``class shapes.Shape``

  A constructor with ``varargin`` shows ``(varargin)``. If the
  constructor's first help line looks like its signature and
  ``autodoc_docstring_signature`` is on (the default), that line is the
  class signature whatever this setting is.
* :confval:`matlab_add_namespace_names` (default ``True``): show the
  namespace in signatures (``shapes.Circle``); ``False`` shows ``Circle``.
* :confval:`matlab_external_names`: MATLAB's own classes and namespaces
  (``handle``, ``matlab.*``, ``Simulink.*``, ``double``, ``datetime``,
  ...). A reference to one of them that the project does not document is
  text, without a "reference target not found" warning. Add the names of
  other toolboxes you use (``r"sltest\..+"``) to the default list.
* :confval:`matlab_auto_link` (default ``None``): turn names in help text
  into links. ``"basic"`` links the entries of "See also" lines and the
  property and method lists of class help; ``"all"`` also links every known
  class and function name. See :doc:`help-text`.

  Use ``"basic"``. ``"all"`` searches every help text for every class and
  function name in the project, so it costs more as the project grows, and
  it also links ordinary words that are names in the project: with a
  function ``data``, every "data" in the help becomes a link.

These Sphinx and autodoc settings apply too:

* ``autoclass_content``: ``"class"`` (default) shows the class help;
  ``"init"`` the constructor's help instead; ``"both"`` both, and then the
  constructor is not listed again among the members.
* ``autodoc_docstring_signature`` (default ``True``): if the first help line
  of a function or method looks like its signature (``times_two(x)``), use it
  as the signature and drop it from the text.
* ``autodoc_member_order``, and ``:member-order:`` on a directive, set the
  order of the members on a page:

  * ``"alphabetical"`` (default): by name; uppercase letters sort before
    lowercase ones.
  * ``"groupwise"``: by kind, then by name. In a class: static methods,
    other methods, then properties and enumeration values. In a folder:
    scripts and apps, classes, then functions.
  * ``"bysource"``: a class's members in the order of its ``classdef``
    file. The files of a folder have no source order; they stay in name
    order, whatever order the file system lists them in.
* ``autodoc_default_options``: default options of the auto directives, for
  example ``{"members": True, "show-inheritance": True}``.
* ``add_function_parentheses``: ``()`` after function and method links.
  Sphinx's ``add_module_names`` is not read; use
  :confval:`matlab_add_namespace_names`.
* ``suppress_warnings``: see :doc:`warnings`. Use this to suppress some warnings
  during the build.
* The events ``autodoc-process-docstring`` and ``autodoc-skip-member`` are
  emitted for MATLAB objects too, so extensions such as
  ``sphinx.ext.napoleon`` work on MATLAB help.

Checking help text
------------------

:confval:`matlab_api_check_rules`,
:confval:`matlab_api_check_ignore_patterns`,
:confval:`matlab_api_check_section_labels`,
:confval:`matlab_api_check_files`, :confval:`matlab_api_check_files_from`
and :confval:`matlab_api_check_ignore_unmatched` configure the
``matlab-api-check`` builder; see :doc:`api-check`.

The ignore patterns match the path references of files and of methods in a
``classdef`` file (``+shapes/Circle.m.draw``), with the rules of the
patterns above; ``*`` matches dots too, so ``Circle.m.*`` matches every
method of ``Circle``. Ignoring a class file also skips its methods.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Pattern
     - Not checked
   * - ``"generated/**"``
     - everything below ``generated/``
   * - ``"+pkg/internal/**"``
     - the files below ``+pkg/internal/`` and their methods
   * - ``"utils/legacy.m"``
     - one file
   * - ``"+shapes/Circle.m"``
     - the class ``shapes.Circle`` and all its methods
   * - ``"+shapes/Circle.m.*"``
     - the methods of ``Circle``, but not the class itself
   * - ``"+shapes/Circle.m.draw"``
     - one method
   * - ``"**.m.set*"``
     - methods whose names start with ``set``, in every class
   * - ``"**/*.m.*"``
     - every method in a ``classdef`` file: only files are checked
   * - ``"**/tests/**"``, ``"**/*Test.m"``
     - test folders and test classes
   * - ``"examples/*.m"``
     - the scripts directly in ``examples/``, not in its subfolders
   * - ``"@Legacy/**"``
     - an old-style class folder

Memory
------

The index keeps decoded source text in memory until it is parsed or the
build ends. Its memory cost depends on the selected source files.

Removed settings
----------------

Setting ``matlab_src_dir``, ``matlab_keep_package_prefix`` or
``matlab_short_links`` is a configuration error that names the replacement.
:doc:`migration` shows how to update an older ``conf.py``.
