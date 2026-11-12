Warnings
========

The :term:`extension` never stops a build because of one bad file: the file gets a
warning, and everything else is documented as usual. Each warning has the
type ``mat`` and a subtype, starts with the path reference of the file, and
gives ``file:line`` where a line is known. :doc:`../reference/warnings`
lists them in a table.

Turning warnings off
--------------------

Sphinx's ``suppress_warnings`` turns off warnings by type and subtype:

.. code-block:: python

   suppress_warnings = [
       "mat.not_callable",  # one subtype
       "mat.empty_code_file",
   ]

``"mat"`` turns off every warning of this extension. ``scmd apidoc``
reads ``suppress_warnings`` from the same ``conf.py``. Warnings about help
text that is not valid :term:`reStructuredText` come from :term:`docutils <Docutils>` and have the
type ``docutils``, which covers every page, not only help text
(:doc:`help-text`).

What each warning means
-----------------------

``mat.parse_error``
   A file could not be read (no permission, for example) or parsed, an
   ``.mlapp`` file is not a valid App Designer file, a ``.slx`` or ``.mdl``
   file is not a Simulink model, library or subsystem file (or is a Git
   LFS pointer, or exceeds the size limits), a folder could not be listed
   or entered, or a file name is not valid UTF-8. A file that cannot be
   read or parsed is still indexed and documented, without content, so
   links to it work; it is tried again on every build. Where the parser
   found a syntax error, the warning gives its line and column. Two names
   in one folder that differ only by Unicode form (``é`` as one character
   and as ``e`` and an accent) have the same path reference: the first in
   the order of the names on disk is documented, the other is left out, and
   the warning shows both names with escapes (``'caf\xe9.m'``,
   ``'cafe\u0301.m'``). Rename one of them.

``mat.folder_name``
   An error, which ``suppress_warnings`` does not hide: a folder is named
   like a file the extension reads (``.m``, ``.mlapp``, ``.slx``, ``.mdl``,
   ``.md``, ``.rst``, in any case), so references and output
   names could take it for a file. The folder and everything in it are not
   documented; the build goes on. Rename the folder.

``mat.encoding``
   A file is not valid in its encoding: it was decoded with the fallback
   (Windows ANSI code page or Latin-1), or bytes were replaced. The warning
   gives the line of the first bad byte. Save the file as UTF-8, or set
   :confval:`matlab_src_encoding` (:doc:`configuration`).

``mat.invalid_matlab``
   The file is probably not valid MATLAB: its first line of code says one
   type and the parser found another (a ``classdef`` without its ``end``,
   ``function = 1;``), a ``function`` has a dotted name (``function y =
   pkg.f(x)``, which MATLAB refuses to run outside a ``classdef``), or a
   ``.m`` file contains NUL bytes (probably a binary file). It is
   documented as far as it could be parsed.

``mat.empty_code_file``
   The file is empty, or has only blank lines. It is documented as a
   script. A file with only comments is a help file and does not warn
   (:doc:`help-text`).

``mat.not_callable``
   MATLAB cannot call the file for :confval:`matlab_version`, so it has no
   MATLAB name; it is documented and linked by path (:doc:`referencing`).
   The warning says why (an invalid name such as ``my-file``, a keyword,
   a subfolder of a class folder, ...). Simulink cannot reference a model,
   library or subsystem file in a namespace folder by name
   (:ref:`simulink-namespaces`), and does not load one directly in
   ``private/`` or a class folder, even by its path, so these have no name. Their subfolders are plain folders
   for Simulink: a model in ``@C/sub/`` loads in every release, though
   ``.m`` files there are not callable from R2026a.
   Rename or move the file, or suppress the warning if that is intended.

``mat.outside_root``
   A link or Windows junction below the project root points outside it; it
   is not followed (:doc:`configuration`).

``mat.link_cycle``
   A link or Windows junction points to the folder it is in or to a folder
   above it, up to the project root, so following it would list the same
   files again and again. It is not followed; its folder is documented
   once, at its own path (:doc:`configuration`).

``mat.ambiguous``
   A name in a :term:`directive`, :term:`role`, "See also" line or auto-link
   matches several :term:`objects <object>`, or a reference matches objects in
   several intersphinx :term:`inventories <inventory>` (:doc:`linking-projects`).
   The warning lists their path
   references; use one of them. Copies of files (vendored code, symbolic
   links) are a common cause; exclude them with
   :confval:`matlab_src_exclude_patterns`. When the copies are intended,
   :confval:`matlab_link_shadowed_files_to_chooser_pages` links such names to the page
   that lists the objects and turns the warning off for them (an auto
   directive still has to name one object).

``mat.not_found``
   An auto directive (``mat:autofunction`` and the others) names no object
   of its kind below the project root ("don't know which object to
   document"), so it writes nothing. The warning gives the page and line
   of the directive. Check the name, the current folder
   (:doc:`referencing`) and :confval:`matlab_src_code_project_root`.
   Description directives (``mat:function``) never read a file and never
   get it (:doc:`documenting`). A name in ``:members:`` that the object
   does not have gets it too.

``mat.directive``
   A directive got an argument of the wrong kind: ``mat:folder`` names a
   class folder (document the class instead), or ``mat:autofolder`` has
   arguments or a return annotation (a folder has neither).

``mat.duplicate``
   The same object is described twice (add ``:no-index:`` to one of the
   descriptions), or two objects would get the same anchor, so the second
   cannot be linked.

``mat.apidoc``
   ``scmd apidoc``: a file that cannot be read was left out, two
   output names differ only by letter case, or an output path is longer
   than Windows allows.

``mat.api_check``
   A finding of the ``matlab-api-check`` builder (:doc:`api-check`), an
   ``ERROR`` or a ``WARNING`` depending on the rule's severity.

Files named ``Contents.m``, ``slblocks.m`` and the other special files
(:doc:`help-text`) never get ``mat.invalid_matlab``,
``mat.empty_code_file`` or ``mat.not_callable``.

When warnings appear
--------------------

* On every build, for every indexed file: ``mat.encoding``,
  ``mat.empty_code_file``, ``mat.not_callable``, ``mat.outside_root``,
  ``mat.link_cycle``, ``mat.invalid_matlab`` for NUL bytes, and
  ``mat.parse_error`` for a file or folder that cannot be read.
* Once per build, for the files that the pages read in that build use:
  ``mat.invalid_matlab`` and ``mat.parse_error`` found while parsing. A file
  that no page uses is not parsed, so it does not get these (the
  ``matlab-api-check`` builder parses every file, so it reports them all).

Other warnings
--------------

Messages from docutils and Sphinx themselves, such as an unknown directive
option, have no ``mat`` type. Fix the directive; ``suppress_warnings`` with
``mat`` does not hide them.
