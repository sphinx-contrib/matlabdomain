Migrating from 0.22 and earlier
===============================

Version 1.0.0 is the first stable release, and it breaks with the 0.x
series on purpose: objects are named by path and by their MATLAB names
instead of Python-style dotted module names, the project root replaces
``matlab_src_dir``, and Python-only features are gone. Builds of old
projects fail early with errors that name the replacement, so the changes
below can be made one error at a time. :doc:`../CHANGES` lists every change.

From 1.0.0 on, the project follows `semantic versioning
<https://semver.org/>`_: breaking changes, including changes to link anchors
and to the ``sphinx-matlab-apidoc`` template variables, come only in a new
major version.

Requirements
------------

Python 3.11 or newer and Sphinx 8.0 or newer (:doc:`../getting-started/installation`).

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
       signatures show MATLAB names (without the ``+``)
   * - ``matlab_short_links``
     - remove it: signatures show MATLAB names
   * - ``add_module_names = False``
     - ``matlab_add_namespace_names = False`` (the MATLAB domain no longer
       reads ``add_module_names``)
   * - ``extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]``
     - ``sphinx.ext.autodoc`` is optional: the extension loads it

Setting a removed value is a ``ConfigError``. If ``matlab_src_dir`` pointed
at a folder with several projects, :confval:`matlab_src_include_patterns`
can select some of them; :confval:`matlab_src_exclusion_patterns` leaves out
tests or data (:doc:`configuration`).

New settings worth a look: :confval:`matlab_version` (if the code targets a
release before R2026a), :confval:`matlab_src_encoding` (it used to be
ignored).

Directives and roles
--------------------

.. list-table::
   :header-rows: 1

   * - 0.x
     - 1.0
   * - ``.. module:: target``
     - ``.. mat:folder:: target/``
   * - ``.. automodule:: target``
     - ``.. mat:autofolder:: target/``
   * - ``.. currentmodule:: target``
     - ``.. mat:currentfolder:: target/``
   * - ``:mat:mod:`target```
     - ``:mat:folder:`target/```
   * - ``.. mat:exception::``, ``.. mat:autoexception::``, ``:mat:exc:``
     - document error classes with ``mat:class`` / ``mat:autoclass`` and
       ``:mat:class:``
   * - ``.. mat:decorator::``, ``.. mat:decoratormethod::``
     - removed (no MATLAB equivalent)
   * - ``:special-members:``, ``:inherited-members:``
     - removed (``:inherited-members:`` crashed the build)
   * - ``:friend-members:``
     - ``:access-list-members:`` (the old name still works)

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
  ``:ref:`mat-folderindex```).
* "Bases:" and auto-links now always use ``:mat:`` roles, so they link
  without ``primary_domain = "mat"``.

What the docs show
------------------

* Help text follows MATLAB's ``help``: a comment block *before* a file's
  ``function`` or ``classdef`` line wins over the block after it, so a
  licence header at the top of a file becomes its help, as in MATLAB. Put
  the help block first, above the licence header and a blank line.
* A script with local functions is documented as a script, not a function.
* Signatures show MATLAB names: ``package.ClassBar``, not ``+package.ClassBar``.
* ``+`` folders show as ``namespace``; other folders as ``folder``.
* Files MATLAB cannot call (a keyword namespace, an invalid file name) are
  documented by path, with a ``mat.not_callable`` warning.
* New warnings point at files that are probably broken
  (``mat.invalid_matlab``, ``mat.no_code``, ``mat.encoding``); a file that
  cannot be read or parsed no longer stops the build (:doc:`warnings`).

New tools
---------

* ``sphinx-matlab-apidoc`` writes the pages for a whole project
  (:doc:`apidoc`); it may replace hand-written ``automodule`` pages.
* The ``matlab-api-check`` builder checks help text (:doc:`api-check`).
