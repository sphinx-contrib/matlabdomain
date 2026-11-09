Migrating from 0.22 and earlier
===============================

Version 1.0.0 is the first stable release, and it breaks with the 0.x
series on purpose: :term:`objects <object>` are named by path and by their MATLAB names
instead of Python-style dotted module names, the project root replaces
``matlab_src_dir``, and Python-only features are gone. Builds of old
projects fail early with errors that name the replacement, so the changes
below can be made one error at a time. :doc:`../CHANGES` lists every change.

The agent skill ``migrating-from-0x`` (``scmd skills install
migrating-from-0x``, :program:`scmd skills install`) walks
through a migration step by step, with scripts that rewrite dotted names in
pages, list files with comments above their declaration, and compare the
objects of the 0.x and 1.0 builds.

From 1.0.0 on, the project follows `semantic versioning
<https://semver.org/>`_: breaking changes, including changes to link anchors
and to the ``scmd apidoc`` template variables, come only in a new
major version.

Requirements
------------

Python 3.11 or newer and Sphinx 8.0 or newer (:doc:`../getting-started/installation`).

A pin such as ``sphinxcontrib-matlabdomain==0.*`` in a requirements file
or ``pyproject.toml`` keeps 0.x; change it to ``>=1,<2``. A :term:`virtual
environment` that is reused between builds (on a CI agent, or one that a
script creates only when it is missing) keeps the old version and the old
Sphinx until it is recreated or upgraded. ``scmd --version`` works only
with 1.0.

Remove a ``sys.path`` entry in ``conf.py`` that points at a checkout of the
:term:`extension` (projects that started from the extension's own test docs have
one): the old checkout's ``sphinxcontrib/__init__.py`` breaks the
``sphinxcontrib`` namespace, and the build stops with "Could not import
extension sphinxcontrib.applehelp (exception: No module named
'pkg_resources')".

``conf.py``
-----------

.. list-table::
   :header-rows: 1

   * - 0.x
     - 1.0
   * - ``matlab_src_dir = os.path.abspath("..")``
     - ``matlab_src_code_project_root = ".."``, relative to the folder of
       ``conf.py`` (an absolute path works too)
   * - ``matlab_keep_package_prefix``
     - remove it: references are paths (which keep the ``+``), and
       :term:`signatures <signature>` show MATLAB names (without the ``+``)
   * - ``matlab_short_links``
     - remove it: signatures show MATLAB names
   * - ``add_module_names = False``
     - ``matlab_add_namespace_names = False`` (the MATLAB :term:`domain`
       no longer
       reads ``add_module_names``)
   * - ``extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]``
     - ``sphinx.ext.autodoc`` is optional: the extension loads it

Setting a removed value is a ``ConfigError``; one error names all the
removed values that ``conf.py`` sets. So is any other ``conf.py`` name that
starts with ``matlab_`` and is not a configuration value: rename helper
variables such as ``matlab_root = ...`` (``_matlab_root``).

If ``matlab_src_dir`` pointed at a folder with several projects,
:confval:`matlab_src_include_patterns` can select some of them;
:confval:`matlab_src_exclude_patterns` leaves out tests or data
(:doc:`configuration`). A list of your own replaces the default exclusion
patterns, so copy them into it to keep them. Patterns use ``/`` on every
system; a ``\`` is a ``ConfigError``.


New settings worth a look: :confval:`matlab_version` (if the code targets a
release before R2026a), :confval:`matlab_src_encoding` (it used to be
ignored).

Directives and roles
--------------------

.. list-table::
   :header-rows: 1

   * - 0.x
     - 1.0
   * - ``.. module:: target``, ``.. mat:module:: target``
     - ``.. mat:folder:: target/``
   * - ``.. automodule:: target``, ``.. mat:automodule:: target``
     - ``.. mat:autofolder:: target/``
   * - ``.. currentmodule:: target``, ``.. mat:currentmodule:: target``
     - ``.. mat:currentfolder:: target/``
   * - ``.. module:: .`` (the root, so that names start there)
     - remove it: path references start at the root
   * - ``:mat:mod:`target```
     - ``:mat:folder:`target/```
   * - ``.. mat:exception::``, ``.. mat:autoexception::``, ``:mat:exc:``
     - document error classes with ``mat:class`` / ``mat:autoclass`` and
       ``:mat:class:``
   * - ``.. mat:decorator::``, ``.. mat:decoratormethod::``
     - removed (no MATLAB equivalent)
   * - ``.. mat:classmethod::``
     - ``.. mat:staticmethod::`` (MATLAB has no other class methods)
   * - ``:special-members:``, ``:inherited-members:``
     - removed (``:inherited-members:`` stopped every build that used it
       with an exception)
   * - ``:friend-members:``
     - ``:access-list-members:`` (the old name still works)

An old directive or role is an "Unknown directive type" or "Unknown
interpreted text role" error, and a removed option makes its directive fail
("An option to mat:autoclass is either unknown or has an invalid value").
Either way that object is missing from the page, but the build still
succeeds unless it runs with ``-W``. Search the pages, including Markdown
ones, before the first build:

.. code-block:: console

   $ grep -rnE "(auto|current)?module::|:mat:mod:|:(special|inherited)-members:|mat:(auto)?(exception|decorator)|mat:classmethod" docs

Names
-----

0.x named everything with dots, starting from ``matlab_src_dir``:
``target.+package.ClassBar``, ``target.@ClassFolder.ClassFolder``,
``target.submodule.f``. Dotted names are no longer references. Write the
MATLAB name or the path reference (:doc:`referencing`):

.. list-table::
   :header-rows: 1

   * - 0.x
     - MATLAB name
     - Path reference
   * - ``target.ClassExample``
     - ``ClassExample``
     - ``target/ClassExample.m``
   * - ``target.+package.ClassBar``
     - ``package.ClassBar``
     - ``target/+package/ClassBar.m``
   * - ``target.+package.ClassBar.doBar``
     - ``package.ClassBar.doBar``
     - ``target/+package/ClassBar.m.doBar``
   * - ``target.@ClassFolder.ClassFolder``
     - ``ClassFolder``
     - ``target/@ClassFolder/ClassFolder.m``
   * - ``target.submodule.f``
     - ``f``
     - ``target/submodule/f.m``

The MATLAB name works when exactly one documented file has it; otherwise the
build warns (``mat.ambiguous``) and lists the path references to choose
from. Plain folders such as ``target`` and ``submodule`` are not part of
MATLAB names, as in MATLAB.

Links and anchors
-----------------

* Anchors are ``mat-`` followed by the path reference
  (``#mat-target/+package/ClassBar.m``); the old dotted and ``module-``
  anchors are gone, so deep links into old pages break once.
* The intersphinx inventory names objects by path reference. Projects that
  link to yours with intersphinx need the new names.
* The module index is now the folder index (``mat-folderindex.html``,
  ``:ref:`mat-folderindex```). Replace ``:ref:`modindex``` too (as
  ``sphinx-quickstart`` writes it): it names Python's module index.
* "Bases:" and auto-links now always use ``:mat:`` roles, so they link
  without ``primary_domain = "mat"``.
* Tools that read the build's output (its XML or doctrees, or the HTML ids)
  see the new names. A script that checks help text that way can be
  replaced by the ``matlab-api-check`` builder (:doc:`api-check`).

What the docs show
------------------

* Help text follows MATLAB's ``help``: a comment block *before* a file's
  ``function`` or ``classdef`` line wins over the block after it, so a
  licence header at the top of a file becomes its help, as in MATLAB. Put
  the help block first, above the licence header and a blank line. Other
  comments above the declaration count too: a ``%#ok`` pragma, a ``%%``
  section title, a commented-out signature. MATLAB's ``help`` shows the
  same text; move such comments below the help. To find them, list the
  files whose first non-blank line is a comment rather than the
  declaration.
* A script with local functions is documented as a script, not a function.
* Signatures show MATLAB names: ``package.ClassBar``, not ``+package.ClassBar``.
* ``+`` folders show as ``namespace``; other folders as ``folder``.
* Files MATLAB cannot call (a keyword namespace, an invalid file name) are
  documented by path, with a ``mat.not_callable`` warning.
* New warnings point at files that are probably broken
  (``mat.invalid_matlab``, ``mat.empty_code_file``, ``mat.encoding``); a
  file that cannot be read or parsed no longer stops the build
  (:doc:`warnings`).
* More objects are documented: enumeration members, and members that the
  0.x parser dropped after it failed on a line (a property default it
  could not read, a method signature with a comment). 0.x also documented
  members of a ``classdef`` inside a ``%{ ... %}`` block comment; 1.0 does
  not.

The first build
---------------

Build with ``-n`` (nitpicky) first, then fix or silence each warning type
and add ``-W`` to keep it clean. Typical ones after a migration:

* "reference target not found" for a class of a toolbox in "Bases:"
  (``sltest.TestCase``): add its names to
  :confval:`matlab_external_names`. MATLAB's own classes (``handle``,
  ``matlab.mixin.*``) are in its default, so a ``nitpick_ignore_regex``
  for them can go.
* docutils errors in help text ("Unexpected indentation"): help is
  reStructuredText; fix the help (:doc:`help-text`).
* ``mat.ambiguous``, ``mat.not_callable``, ``mat.empty_code_file`` and the
  other ``mat`` subtypes: :doc:`warnings`. Help files (comments only, such
  as the help of a MEX function) do not warn.
* ``image.not_readable`` for an image in help text: relative paths in help
  are relative to the code file (:doc:`help-text`); 0.x resolved them from
  the documentation page.

Comparing with the 0.x docs
---------------------------

Keep the 0.x build's ``objects.inv`` and compare the objects by kind
(the old dotted names map to path references as in `Names`_). Besides
the new objects above, expect:

* ``scmd apidoc`` pages show public members; 0.x pages often had
  ``:private-members:``. To keep private members on every generated page,
  set ``autodoc_default_options = {"private-members": True}``.
* The function files of a class folder are methods of the class, not also
  functions. With the default namespace grouping, ``private/`` files are
  left out; with ``matlab_apidoc_group = "folder"`` they get pages.
* One page per namespace (and Global), like many 0.x page generators; a
  0.x page per class folder is now the class on its namespace's page.
* Fewer warnings: 0.x parser messages ("Expected property", "Unexpected
  class name") are gone.

New tools
---------

* ``scmd apidoc`` writes the pages for a whole project
  (:doc:`apidoc`); it may replace hand-written ``automodule`` pages and
  page generators.
* The ``matlab-api-check`` builder checks help text (:doc:`api-check`).
  On an existing project, set every rule to ``"warning"`` first, so the
  check reports without failing, and make rules errors as the help
  improves. ``api-check.json`` can feed a pull-request comment.
