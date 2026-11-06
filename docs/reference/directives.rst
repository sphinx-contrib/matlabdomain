Directives, roles and indices
=============================

Every directive and role is in the ``mat`` domain. With
``primary_domain = "mat"`` the ``mat:`` prefix may be left out.
:doc:`../user-guide/documenting` and :doc:`../user-guide/referencing` show
them in use.

Auto directives
---------------

An auto directive takes one argument: a MATLAB name, a path reference, or a
name relative to the current folder (:doc:`../user-guide/referencing`),
optionally followed by a signature, ``(a, b)``, that replaces the one read
from the file. It reads the file and writes the matching description directive
(below) with the help text. Content below the directive is added after the
help text. ``autodoc_default_options`` supplies default options. If no
object matches the argument, the build warns (``mat.not_found``, "don't
know which object to document") and the directive writes nothing.

.. rst:directive:: .. mat:autofunction:: name

   A function file. The signature lists the inputs; with
   ``autodoc_docstring_signature``, a first help line that looks like the
   signature replaces it.

   .. rst:directive:option:: noindex
                             no-index

      Do not create a link target or an index entry.

.. rst:directive:: .. mat:autoclass:: name

   A class: a ``classdef`` file, or the class of a class folder
   (``@Cls/Cls.m``, with the methods in other files of the folder).
   With ``:members:``, its members follow in the sections "Constructor
   Summary", "Property Summary", "Enumeration Values" and "Method Summary".

   .. rst:directive:option:: members
      :type: no value, or a comma-separated list of member names

      Document all members, or the named ones.

   .. rst:directive:option:: undoc-members

      Also document members without help (enumeration values are always
      documented).

   .. rst:directive:option:: private-members
      :type: no value, or a comma-separated list of member names

      Also document members with ``Access = private`` (all, or the named
      ones).

   .. rst:directive:option:: protected-members
      :type: no value, or a comma-separated list of member names

      Also document members with ``Access = protected``.

   .. rst:directive:option:: hidden-members
      :type: no value, or a comma-separated list of member names

      Also document ``Hidden`` members.

   .. rst:directive:option:: access-list-members
      :type: no value, or a comma-separated list of class names

      Also document members whose access is a list of classes
      (``Access = ?OtherClass`` or ``{?A, ?B}``): all, or those accessible
      to the named classes (with or without ``?``).

   .. rst:directive:option:: friend-members

      The old name of ``:access-list-members:``.

   .. rst:directive:option:: exclude-members
      :type: a comma-separated list of member names

      Leave out the named members.

   .. rst:directive:option:: member-order
      :type: ``alphabetical``, ``groupwise`` or ``bysource``

      The order of the members in each section; default
      ``autodoc_member_order``.

   .. rst:directive:option:: show-inheritance

      Add a "Bases:" line with the superclasses.

   .. rst:directive:option:: noindex
                             no-index

      Do not create link targets or index entries, also for the members.

.. rst:directive:: .. mat:automethod:: name

   One method: ``Cls.method`` (a MATLAB name or a path reference such as
   ``+pkg/Cls.m.method``), or the method name alone inside a class.
   Static methods are written as ``mat:staticmethod``. In the signature,
   a first input named ``obj`` or ``self`` is left out, except for the
   constructor and static methods (they have no object).

   .. rst:directive:option:: noindex
                             no-index

      Do not create a link target or an index entry.

.. rst:directive:: .. mat:autoattribute:: name

   One property or enumeration value, named like a method.

   .. rst:directive:option:: annotation
      :type: no value, or text

      Without a value, show neither default value nor specification. With a
      value, show ``= <value>`` after the name instead.

   .. rst:directive:option:: noindex
                             no-index

      Do not create a link target or an index entry.

.. rst:directive:: .. mat:autoenum:: name

   The same as ``mat:autoattribute``, for an enumeration value; it takes the
   same options.

   .. rst:directive:option:: annotation
                             noindex
                             no-index

      As for ``mat:autoattribute``.

.. rst:directive:: .. mat:autoevent:: name

   One event of a class, named like a method.

   .. rst:directive:option:: noindex
                             no-index

      Do not create a link target or an index entry.

.. rst:directive:: .. mat:autoscript:: name

   A script file.

   .. rst:directive:option:: noindex
                             no-index

      Do not create a link target or an index entry.

.. rst:directive:: .. mat:autodata:: name

   A script documented as data (``mat:data``), for example a file of
   parameters.

   .. rst:directive:option:: noindex
                             no-index

      Do not create a link target or an index entry.

.. rst:directive:: .. mat:autoapplication:: name

   An App Designer app (``.mlapp``), with the summary and description
   stored in the app.

   .. rst:directive:option:: noindex
                             no-index

      Do not create a link target or an index entry.

.. rst:directive:: .. mat:autofolder:: name

   A folder (path reference ending with ``/``, or a namespace's MATLAB
   name), written as ``mat:folder``. It also sets the current folder. The
   options apply to the members too, so ``:members:`` also documents the
   members of the folder's classes.

   .. rst:directive:option:: members
      :type: no value, or a comma-separated list of file names

      Document the functions, classes, scripts and apps directly in the
      folder (not class folders, ``private/`` or subfolders; not
      ``Contents.m`` and the other special files), sorted by name; or the
      named ones.

   .. rst:directive:option:: undoc-members
                             private-members
                             protected-members
                             hidden-members
                             access-list-members
                             friend-members
                             exclude-members
                             member-order
                             show-inheritance

      As for ``mat:autoclass``; they apply to the folder's members and their
      members.

   .. rst:directive:option:: synopsis
                             platform
                             deprecated

      As for ``mat:folder``.

   .. rst:directive:option:: noindex
                             no-index

      Do not create link targets or index entries.

Sidecar docs
------------

.. rst:directive:: .. mat:autosidecar:: reference

   Render a sidecar doc (:doc:`../user-guide/sidecars`): the path
   reference of a ``.md`` or ``.rst`` file that
   :confval:`matlab_src_sidecar_suffixes` indexes. Its headings become
   sections; the first is the sidecar doc's title. One without a heading
   gets its file name as title, with a ``mat.sidecar`` warning. Relative
   paths in it are relative to its folder. A reference that is not an
   indexed sidecar doc writes nothing, with a ``mat.sidecar`` warning. Use
   it in reST documents (in a Markdown document, a reST sidecar doc would be
   read as Markdown).

   .. rst:directive:option:: no-title

      Leave out the sidecar doc's first heading: the rest of it continues
      the current section (a folder's README as the introduction of the
      folder's page).

Description directives
----------------------

The auto directives write these; write them by hand for objects without a
source file (:doc:`../user-guide/documenting`). They never read a file and
never warn about a missing one: they show the signature and content as
written. The argument is a
signature: a name, optionally followed by ``(arguments)`` (optional
arguments in ``[...]``) and ``-> annotation``. If the name matches a source
file, the object gets its path reference (for links), not its help. Their
content may use
Sphinx's info fields: ``:param x:``, ``:type x:``, ``:returns:``,
``:rtype:``, ``:raises Cls:`` (a link to an error class), ``:var v:``.
A type in ``:type x:`` or ``:vartype v:`` links to a documented object of
that name; any other type (``double``, ``(1,1) string``) is shown as text,
without a "reference target not found" warning.

.. rst:directive:: .. mat:function:: signature

   A function.

   .. rst:directive:option:: noindex
                             no-index

      Do not create a link target or an index entry.

   .. rst:directive:option:: annotation
      :type: text

      Text after the signature.

   .. rst:directive:option:: reference
      :type: a path reference

      The object's path reference (the auto directives set it).

.. rst:directive:: .. mat:class:: signature

   A class (shown as ``class <name>``). Methods and properties described in
   its content belong to it.

   .. rst:directive:option:: noindex
                             no-index
                             annotation
                             reference

      As for ``mat:function``.

   .. rst:directive:option:: abstract
                             sealed

      Show the MATLAB class attribute before ``class`` (``abstract class
      Shape``). ``mat:autoclass`` sets them from the ``classdef``.

.. rst:directive:: .. mat:method:: signature

   A method, inside ``mat:class`` or named ``Cls.method``.

   .. rst:directive:option:: noindex
                             no-index
                             annotation
                             reference

      As for ``mat:function``.

   .. rst:directive:option:: abstract
                             sealed

      Show the MATLAB method attribute before the name (``abstract
      area()``). The auto directives set them from the ``methods`` block.

.. rst:directive:: .. mat:staticmethod:: signature

   A static method, shown with ``static``.

   .. rst:directive:option:: noindex
                             no-index
                             annotation
                             reference
                             abstract
                             sealed

      As for ``mat:method``.

.. rst:directive:: .. mat:attribute:: name

   A property or enumeration value.

   .. rst:directive:option:: noindex
                             no-index
                             annotation
                             reference

      As for ``mat:function``.

   .. rst:directive:option:: abstract
                             constant
                             dependent
                             read-only

      Show the property attribute before the name (``constant Max = 10``).
      The auto directives set them from the ``properties`` block;
      ``read-only`` when ``SetAccess`` (or ``Access``) is stricter than the
      read access (``SetAccess = private``, ``immutable``, ...), except for
      constants.

.. rst:directive:: .. mat:event:: name

   An event, inside ``mat:class`` or named ``Cls.event``.

   .. rst:directive:option:: noindex
                             no-index
                             annotation
                             reference

      As for ``mat:function``.

.. rst:directive:: .. mat:script:: name

   A script.

   .. rst:directive:option:: noindex
                             no-index
                             annotation
                             reference

      As for ``mat:function``.

.. rst:directive:: .. mat:application:: name

   An App Designer app.

   .. rst:directive:option:: noindex
                             no-index
                             annotation
                             reference

      As for ``mat:function``.

.. rst:directive:: .. mat:data:: name

   Data, such as a script that defines variables.

   .. rst:directive:option:: noindex
                             no-index
                             annotation
                             reference

      As for ``mat:function``.

.. rst:directive:: .. mat:folder:: name

   A folder: a path reference (with or without the trailing ``/``) or a
   namespace's MATLAB name. A valid ``+`` folder is shown as ``namespace
   <MATLAB name>``, any other as ``folder <path>``; an ``@`` class folder
   is an error (document its class). Sets the current folder. A folder may
   be described on several pages; the last one is the link target.

   .. rst:directive:option:: synopsis
      :type: text

      A one-line description, shown in the folder index and link titles.

   .. rst:directive:option:: platform
      :type: text

      Platforms, shown in the folder index.

   .. rst:directive:option:: deprecated

      Mark the folder as deprecated in the folder index.

   .. rst:directive:option:: noindex
                             no-index

      Do not create a link target or an index entry.

.. rst:directive:: .. mat:currentfolder:: name

   Set the current folder for the rest of the page without documenting
   it: a folder path or namespace name, ``.`` for the project root, or
   ``None`` to clear it.

Roles
-----

The target is a MATLAB name, a path reference or a name relative to the
current folder. ``~target`` shows only the last part; ``title <target>``
sets the text; a leading ``.`` also matches the end of MATLAB names. A role
prefers objects of its type, then accepts any.

.. rst:role:: mat:func

   A function. ``()`` is added to the text (``add_function_parentheses``).

.. rst:role:: mat:class

   A class.

.. rst:role:: mat:meth

   A method or static method. ``()`` is added to the text.

.. rst:role:: mat:attr

   A property or enumeration value.

.. rst:role:: mat:event

   An event.

.. rst:role:: mat:folder

   A folder or namespace.

.. rst:role:: mat:scpt

   A script.

.. rst:role:: mat:app

   An App Designer app.

.. rst:role:: mat:data

   An object documented with ``mat:data``.

.. rst:role:: mat:obj

   An object of any type.

.. rst:role:: mat:const

   An object of any type (no object type uses it).

.. rst:role:: mat:enum

   An object of any type (enumeration values are attributes; prefer
   ``mat:attr``).

.. rst:role:: mat:sidecar

   A sidecar doc, by its path reference only
   (``:mat:sidecar:`+demo/guide.md```): a link to the document that renders
   it, with its title (its first heading) as text unless one is given.

Indices
-------

The domain adds the *MATLAB Folder Index*, which lists the documented
folders: link to it with ``:ref:`mat-folderindex```
(:ref:`mat-folderindex`). The general index (``genindex``) has an entry for
every documented object.
