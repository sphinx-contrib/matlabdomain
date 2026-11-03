Documenting MATLAB code
=======================

The *auto* directives read a MATLAB file and write its documentation: the
signature, the help text and, for classes, the members. This page shows
them on a small sample project, rendered by this documentation's own build.
:doc:`../reference/directives` lists every directive and option.

Auto and description directives
-------------------------------

Every kind of object has two directives: an auto directive
(``mat:autofunction``) and a description directive (``mat:function``).

.. list-table::
   :header-rows: 1
   :stub-columns: 1

   * -
     - ``mat:autofunction``, ``mat:autoclass``, ...
     - ``mat:function``, ``mat:class``, ...
   * - Reads the source file
     - yes
     - never
   * - Signature
     - from the file (or the one you give)
     - as you write it
   * - Text
     - the help text, then your content
     - only your content
   * - Members
     - with ``:members:``
     - nested directives you write
   * - No file has the name
     - a ``mat.not_found`` warning ("don't know which object to
       document"); nothing is shown
     - no warning; shown as written

The auto directives write description directives, filled from the file.
Use the auto directives for code that has files; write description
directives for objects without a ``.m`` file, such as MEX functions
(:ref:`below <hand-written>`).

The sample project
------------------

``conf.py`` of these docs sets ``matlab_src_code_project_root = "src"``, the
folder with:

.. code-block:: text

   src/
       times_two.m              a function
       times_two_napoleon.m     a function with Google-style help
       +shapes/                 namespace shapes
           Shape.m              class shapes.Shape
           Circle.m             class shapes.Circle (a subclass of Shape)
           Color.m              enumeration shapes.Color
           totalArea.m          function shapes.totalArea
           @Polygon/            class folder: class shapes.Polygon
               Polygon.m
               perimeter.m      a method in its own file
           private/
               checkPositive.m  a private function
       scripts/
           shapes_demo.m        a script
       apps/
           ShapesApp.mlapp      an App Designer app

Naming what to document
-----------------------

The argument of an auto directive names one file or member, in one of these
ways:

* its MATLAB name, as you would type it in MATLAB: ``shapes.Circle``,
  ``shapes.Circle.area``, ``times_two``;
* its path reference, the path below the project root:
  ``+shapes/Circle.m``, ``+shapes/Circle.m.area``,
  ``+shapes/@Polygon/Polygon.m``;
* a path or name relative to the current folder (below).

A MATLAB name must belong to exactly one file. When several files share it
(two folders with a ``utils.m``, say), the directive warns
(``mat.ambiguous``) and lists their path references; use one of those.
:doc:`referencing` explains names and references in detail.

Functions
---------

.. literalinclude:: ../snippets/autofunction.rst
   :language: rst

.. include:: ../snippets/autofunction.rst

The signature lists the input names. Name-value arguments (``opts.Scale``
in an ``arguments`` block) appear as their structure, ``opts``.

Classes
-------

``mat:autoclass`` documents the class help; ``:members:`` adds its
constructor, properties, enumeration values and methods, in sections:

.. literalinclude:: ../snippets/autoclass.rst
   :language: rst

.. include:: ../snippets/autoclass.rst

* ``:show-inheritance:`` adds the "Bases:" line, with links to base
  classes that are documented. MATLAB's own classes (``handle``,
  ``matlab.mixin.Copyable``) are not documented in your project; they are
  shown as text, without a "reference target not found" warning (see
  :confval:`matlab_external_names` for the names and how to add others).
* Members without help are left out (enumeration values are always
  shown); ``:undoc-members:`` adds them.
* Members with ``Access = private`` or ``protected``, ``Hidden`` members and
  members whose access is a list of classes (``Access = ?OtherClass``) are
  left out. ``:private-members:``, ``:protected-members:``,
  ``:hidden-members:`` and ``:access-list-members:`` add them: all of
  them, or the ones you name (for ``:access-list-members:``, the classes
  that have access). ``Circle`` above has a hidden property ``Tag`` and a
  private method ``check``.
* ``:members: area, Radius`` documents only the named members;
  ``:exclude-members: unit`` leaves out the named ones.
* Static methods are marked ``static``. ``get.``/``set.`` property methods,
  abstract methods (declared without a body) and converter methods with
  dotted names are not documented.

Enumeration values, here in the order of the file (``:member-order:
bysource``; the default is alphabetical):

.. literalinclude:: ../snippets/autoclass_enum.rst
   :language: rst

.. include:: ../snippets/autoclass_enum.rst

A class folder (``@Polygon/``) is documented through its class. Methods
defined in their own files in the folder (``perimeter.m``) are members like
the methods in the class file:

.. literalinclude:: ../snippets/autoclass_folder.rst
   :language: rst

.. include:: ../snippets/autoclass_folder.rst

A folder ``@X/`` is a class folder only if ``@X/X.m`` is a ``classdef``.
In an old-style class folder (``@X/X.m`` is a function), document each file
with ``mat:autofunction``.

Single members
--------------

``mat:automethod`` and ``mat:autoattribute`` (properties) document one
member. The basic class help with its members, and one method again (with
``:noindex:``, because ``area`` is already documented above):

.. literalinclude:: ../snippets/automembers.rst
   :language: rst

.. include:: ../snippets/automembers.rst

The help text of ``Shape`` lists its properties and methods in MATLAB's
``Shape Properties:`` / ``Shape Methods:`` form. With
``matlab_auto_link = "basic"``, as in these docs, those entries and the "See
also" line become links (:doc:`help-text`).

``mat:autoenum`` is ``mat:autoattribute`` for an enumeration value.

Scripts, apps and private files
-------------------------------

.. literalinclude:: ../snippets/autoother.rst
   :language: rst

.. include:: ../snippets/autoother.rst

Files in ``private/`` folders are documented like any other file. Their
MATLAB name (``checkPositive``) is only visible from the parent folder, as
in MATLAB, so from elsewhere name them by path. App Designer apps show the
summary and description stored in the app.

``mat:autodata`` documents a script as data (a script that defines
variables, such as a parameter file): it looks the same, but its object
type is ``data`` (role ``:mat:data:``) and it gets an index entry.

Folders and the current folder
------------------------------

``mat:autofolder`` documents a folder. A ``+`` folder is shown as a
namespace; any other folder as ``folder`` and its path:

.. literalinclude:: ../snippets/autofolder.rst
   :language: rst

.. include:: ../snippets/autofolder.rst

The folder also becomes the *current folder* of the page: for the rest of
the page, or until the next folder directive, names are looked up relative
to it, so ``Circle.m``,
``shapes.Circle`` and the private ``checkPositive`` all work. To set the
current folder without documenting the folder, use ``mat:currentfolder``:

.. code-block:: rst

   .. mat:currentfolder:: +shapes/

``.`` is the project root and ``None`` clears the current folder.

``:members:`` on ``mat:autofolder`` documents the files directly in the
folder: functions, classes, scripts and apps, in alphabetical order. It does
not include class folders (``@X/``), ``private/`` or subfolders, and leaves
out ``Contents.m`` and the other special files (:doc:`help-text`). The
options apply to the members too: ``:members:`` on a folder also documents
every member of its classes. For a whole project,
``sphinx-matlab-apidoc`` writes one directive per file instead
(:doc:`apidoc`).

Adding text
-----------

Content below an auto directive is added after the help text:

.. code-block:: rst

   .. mat:autofunction:: shapes.totalArea

      Added by hand: an example that is not in the help text.

.. _hand-written:

Writing directives by hand
--------------------------

The ``mat:function``, ``mat:class``, ``mat:method``, ``mat:staticmethod``,
``mat:attribute``, ``mat:script``, ``mat:application``, ``mat:data`` and
``mat:folder`` directives describe an object without reading a file, for
example a MEX function:

.. literalinclude:: ../snippets/handwritten.rst
   :language: rst

.. include:: ../snippets/handwritten.rst

If the name matches a file below the project root, the object gets that
file's path reference, so links to the file land here; the file itself is
not read. Otherwise its reference is the name as written, below the current
folder if one is set (here ``+shapes/fastSolve``). Either way there is no
warning.
Nest ``mat:method`` and ``mat:attribute`` in ``mat:class`` to document
members. The auto directives generate these directives; you rarely need
them for code that has files.
