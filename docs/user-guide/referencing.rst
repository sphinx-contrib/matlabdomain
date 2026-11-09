Names, references and links
===========================

MATLAB names things differently from Python, and this :term:`extension` follows
MATLAB. This page explains how :term:`objects <object>` are named, how to link to them, and
what their link anchors look like.

How MATLAB names files
----------------------

* A ``+name`` folder is a namespace (formerly *package*):
  ``+shapes/+io/read.m`` is the function ``shapes.io.read``.
* An ``@Name`` folder is a class folder: ``@Polygon/Polygon.m`` defines the
  class ``Polygon``, and the other files in the folder are its methods.
* Any other folder is not a namespace. Its files are global names: both
  ``toolbox/f.m`` and ``examples/f.m`` are the function ``f``, and MATLAB
  calls whichever comes first on its path.
* Files in a ``private/`` folder can be called only from the folder above
  it.

The extension computes the MATLAB name of every file this way, for the
release in :confval:`matlab_version`. :term:`Signatures <signature>`, the
index and the :term:`inventory` show it.

Path references
---------------

Two files can have the same MATLAB name, so the extension identifies every
object by its *path reference* instead: its path relative to
:confval:`matlab_src_code_project_root`, with ``/`` on every system and the
file extension.

.. list-table::
   :header-rows: 1

   * - Object
     - Path reference
     - MATLAB name (shown)
   * - ``+shapes/Circle.m``
     - ``+shapes/Circle.m``
     - ``shapes.Circle``
   * - its method ``area``
     - ``+shapes/Circle.m.area``
     - ``shapes.Circle.area``
   * - ``+shapes/@Polygon/Polygon.m``
     - ``+shapes/@Polygon/Polygon.m``
     - ``shapes.Polygon``
   * - ``+shapes/@Polygon/perimeter.m``, a method in its own file
     - ``+shapes/@Polygon/Polygon.m.perimeter``
     - ``shapes.Polygon.perimeter``
   * - ``+shapes/private/checkPositive.m``
     - ``+shapes/private/checkPositive.m``
     - ``checkPositive``
   * - the folder ``+shapes``
     - ``+shapes/``
     - ``shapes``
   * - the project root
     - ``./``
     - (none)

Members follow their file with a ``.``; folders end with ``/``. Paths are
unique, so a path reference always names exactly one object. You normally
write MATLAB names, and use a path reference when a MATLAB name is
ambiguous.

Linking with roles
------------------

.. literalinclude:: ../snippets/roles.rst
   :language: rst

renders as:

.. include:: ../snippets/roles.rst

.. list-table::
   :header-rows: 1

   * - Role
     - Links to
   * - ``:mat:func:``
     - functions
   * - ``:mat:class:``
     - classes
   * - ``:mat:meth:``
     - methods and static methods
   * - ``:mat:attr:``
     - properties and enumeration values
   * - ``:mat:folder:``
     - folders and namespaces
   * - ``:mat:scpt:``
     - scripts
   * - ``:mat:app:``
     - App Designer apps
   * - ``:mat:data:``
     - objects documented with ``mat:data``
   * - ``:mat:obj:``, ``:mat:const:``, ``:mat:enum:``
     - an object of any type

A role prefers objects of its own type; when none matches, it accepts an
object of any type. With ``primary_domain = "mat"`` in ``conf.py``, the
``mat:`` prefix can be left out (``:func:`times_two```).

The text of a link:

* is the target as written, with ``()`` added for ``:mat:func:`` and
  ``:mat:meth:`` (``add_function_parentheses``);
* ``~`` before the target shows only its last part: ``~shapes.Circle.area``
  shows ``area()``;
* ``title <target>`` sets it explicitly.

A target that starts with ``.`` (``.area``) also finds an object whose
MATLAB name ends with it, when nothing else matches.

How a target is found
---------------------

Roles, auto directives, "See also" links and auto-links look a target up in
this order:

1. an exact path reference (``+shapes/Circle.m``);
2. relative to the current folder: a path below it (``Circle.m``) or a
   MATLAB name visible from it, including the folder's ``private/`` files,
   as in MATLAB. The current folder is set by ``mat:autofolder``,
   ``mat:folder`` and ``mat:currentfolder``; in help text, it is the folder
   of the documented file. Inside a class, its members can be named
   without the class (``:mat:meth:`area```);
3. a MATLAB name (``shapes.Circle``) that exactly one documented object has.
   ``private/`` files are not considered, so a private helper never makes a
   public name ambiguous. If several objects have the name, a
   ``mat.ambiguous`` warning lists their path references, which you can use
   instead. With :confval:`matlab_link_shadowed_files_to_chooser_pages` the name links
   to the page that lists them (:ref:`stable-addresses`), without the
   warning;
4. a folder path without its trailing ``/`` (``scripts``), tried last so
   that it never hides a MATLAB name.

There is no search path and no precedence: when two global functions share
a name, link to the one you mean by path. A role links only to documented
objects; with ``nitpicky = True``, Sphinx warns about the others.

Folders and namespaces
----------------------

All folders are one object type, ``folder`` (directives ``mat:folder``,
``mat:autofolder``; role ``:mat:folder:``). A valid ``+`` folder shows
``namespace shapes`` and can be linked by its MATLAB name (``shapes``) or
its path (``+shapes/``). Any other folder shows ``folder scripts/`` and is
linked by path. ``@Name`` class folders are not folder objects: link to
their class. The :ref:`mat-folderindex` lists the documented folders.

Files MATLAB cannot call
------------------------

Some files have no MATLAB name, because MATLAB cannot call them for
:confval:`matlab_version`:

* files below a namespace folder named after a keyword (``+for/``);
* file names that are not valid MATLAB names (``bad-name.m``);
* a class file that does not match its class folder (``@Shape/Other.m``)
  and class folders inside class folders (``@Outer/@Inner/``);
* from R2026a on, scripts and functions in a subfolder of a class folder
  (``@Shape/helpers/f.m``).

They are documented and linked by path, each with one ``mat.not_callable``
warning. Files below ``private/`` and the special files such as
``Contents.m`` never get this warning.

Link anchors
------------

The HTML anchor of an object is ``mat-`` followed by its path reference,
for example ``documenting.html#mat-+shapes/Circle.m`` and
``#mat-+shapes/Circle.m.area`` on :doc:`documenting`. In the path reference, each character other
than ASCII letters, digits, non-ASCII characters and
``- . _ ! $ & ' ( ) * + , ; = : @ /`` is written as ``~XX`` per UTF-8 byte
(a space becomes ``~20``, ``~`` becomes ``~7E``). Only folder names can
contain such characters. Distinct references never share an anchor.

This scheme is a stable contract: an anchor and an inventory name change
only when the file moves or is renamed. The *page* an object is on is not
part of it: when ``scmd apidoc`` splits long pages
(:confval:`matlab_apidoc_page_size`), adding or removing a file can move an
object to another page, and an address copied from the browser then no
longer shows it. Each object therefore also has a stable address,
``mat/name/<MATLAB name>.html`` or ``mat/ref/<path reference>.html``,
which its "¶" link and its inventory entry point to (:ref:`library-changes`).

Linking from other projects
---------------------------

The ``objects.inv`` inventory names each object by its path reference and
shows its MATLAB name. Another Sphinx project that loads this extension
and the inventory (``sphinx.ext.intersphinx``) links with either, as
for its own objects; its own objects come first:

.. code-block:: rst

   :mat:class:`shapes.Circle`
   :mat:class:`+shapes/Circle.m`

:doc:`linking-projects` shows the setup, the differences from local
references and how links follow changes of the other project;
:doc:`projects-and-versions` covers several projects and versions.

Coming from Python
------------------

* There is no module path. ``mat:folder`` replaces ``py:module``; a dotted
  name such as ``target.subfolder.f`` is not a reference.
* Plain folders do not qualify names; files in them are global.
* Two files may have the same MATLAB name in one project; MATLAB decides by
  path order at run time. The extension does not model the path: it warns
  about the ambiguity and expects a path reference.
* Classes are found from ``@`` folders and ``classdef`` files, not by
  importing code. Nothing is executed.
