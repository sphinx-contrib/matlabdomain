Help text
=========

The documentation of a MATLAB object is its help text: the comment block
that MATLAB's ``help`` command shows. This page explains which comments are
used, how they are turned into documentation, and how to write help that
reads well in both MATLAB and HTML.

Which comments are the help
---------------------------

The rules follow ``help`` in MATLAB R2026a, and were checked against it:

* **A file's function or class:** the first comment block *before* the
  ``function`` or ``classdef`` line wins; without one, the block *after*
  the declaration line. Blank lines may separate either block from the
  declaration. A licence or copyright header at the top of a file
  therefore becomes the help, as in MATLAB.
* **Methods and local functions:** only the block after their ``function``
  line; a block before it is ignored. A function's help is its own: nested
  functions add nothing to it.
* **After the declaration:** the block may follow blank lines and an
  ``arguments`` block. A comment on the declaration line itself is not
  help, nor is a comment after the first line of code.
* **Properties, enumeration values and arguments:** a comment block that
  ends on the line before the member, else a comment on the member's line,
  else a block that starts on the next line. Property and enumeration help
  is shown with the member. Comments in ``arguments`` blocks are not shown,
  as in MATLAB's ``help``; ``matlab-api-check`` counts them as
  documentation of the arguments (:doc:`api-check`).
* **Scripts:** the first comment block.
* ``%{ ... %}`` **block comments:** help is the first run of ``%`` lines,
  as in MATLAB, so a block comment gives just ``{``. Use ``%`` lines for
  help.

The first help line is the *H1 line*: MATLAB shows it in ``lookfor`` and
folder listings, and ``matlab-api-check`` requires it (:doc:`api-check`).

What kind of file is it?
------------------------

Each ``.m`` file is a script, function or class according to its first line
of code (blank lines and comments are skipped): ``function`` makes it a
function, ``classdef`` a class, anything else a script. A script with local
functions is a script. A file with only comments is a help file, documented
as a script with that help; next to a MEX file of the same name
(``fast.m`` beside ``fast.mexw64``) it is a function, because MATLAB runs
the MEX file and ``help fast`` shows the help of ``fast.m``. Two warnings
flag suspicious files (see :doc:`warnings`): ``mat.invalid_matlab`` when
this type and the parser disagree (for example a ``classdef`` without its
``end``), and ``mat.empty_code_file`` for an empty file.

MATLAB and Simulink read a few files by name: ``Contents.m`` (folder help),
``slblocks.m``, ``sl_customization.m``, ``pathdef.m``, ``matlabrc.m`` and
``rtwmakecfg.m`` (in any letter case). They are indexed and can be
documented with an explicit directive, but ``mat:autofolder`` with
``:members:`` and ``sphinx-matlab-apidoc`` leave them out, and they never
get ``mat.invalid_matlab``, ``mat.empty_code_file`` or ``mat.not_callable``.

Help text is reStructuredText
-----------------------------

The help text, without the ``%`` and the common indentation, is parsed as
`reStructuredText
<https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_
(reST), like a Python docstring. MATLAB help is plain text, and plain text
is usually valid reST, but not always:

* Lines with the same indentation run together into one paragraph, so a
  list of ``name - description`` lines becomes one line.
* Indentation starts a block quote or a definition list. A change in
  indentation without a blank line gives warnings such as "Unexpected
  indentation" or "Definition list ends without a blank line".
* ``*``, ``_``, ``|`` and backquotes are markup: ``x*y`` or ``name_`` can
  give "Inline emphasis start-string without end-string" or "Unknown target
  name".

Both functions below are valid MATLAB. The first is written in the usual
MATLAB style, and its input list runs together; the second adds blank lines
and ``*`` bullets, which read as well in MATLAB:

.. literalinclude:: ../src/help_styles/scaled.m
   :language: matlab

.. literalinclude:: ../src/help_styles/scaled_list.m
   :language: matlab

.. literalinclude:: ../snippets/help_styles.rst
   :language: rst

.. include:: ../snippets/help_styles.rst

For new help, use the second style, or field lists (``:param x:``, below):
they read well in MATLAB and render as lists. For the property and method
lists of class help (``Shape Properties:``), set ``matlab_auto_link =
"basic"``, which turns them into lists of links (see `Links in help text`_).

What to expect on an existing project:

* Documentation is built for every file, even when its help is not valid
  reST. The warnings name the file and the line in its help (``docstring of
  ...``); the text is still shown, sometimes with odd line breaks.
* Large projects written for MATLAB alone can produce many such warnings
  (thousands in projects with thousands of files). They do not stop a
  build unless ``-W`` turns warnings into errors.
* Fix the help where it matters, or build without ``-W``. These warnings
  come from docutils and have the type ``docutils``: ``suppress_warnings =
  ["docutils"]`` turns them off, for the pages too, so use it only when
  the help cannot be changed (third-party code).

A mode that shows help as preformatted text, without parsing it as reST, is
a possible later feature.

Richer help
-----------

Since help is reST, it can use any reST and Sphinx markup: field lists for
arguments (as in ``times_two``, :doc:`../getting-started/quickstart`),
roles that link to other objects (:doc:`referencing`), code samples after
``::``, and so on.

With ``sphinx.ext.napoleon`` in ``extensions``, Google- and NumPy-style
sections (``Args:``, ``Parameters:``, ``Returns:``) become field lists too:

.. literalinclude:: ../src/times_two_napoleon.m
   :language: matlab

.. include:: ../snippets/napoleon.rst

Napoleon's sections are its own headings (``Args:``, ``Returns:``, ...)
and those of ``napoleon_custom_sections``. A MATLAB heading such as
``Inputs:`` needs an entry there; ``("Inputs", "params_style")`` lists
one entry per name, which suits ``Outputs:`` too (``"returns_style"``
makes the whole section one entry). Napoleon only matches a heading made
of letters, digits, ``_`` and spaces, followed by ``:`` alone on its line,
with the entries indented below it. ``Name-Value Pairs:`` therefore never
becomes a section, whatever ``napoleon_custom_sections`` says, and stays
plain text; write ``Name Value Pairs:`` (with an entry) instead.
``matlab-api-check`` does not read ``napoleon_custom_sections``; see
:doc:`api-check`.

Types in these fields (``x (double)``, ``x ((1,1) string)``) link to a
documented class of that name and are text otherwise, without a warning
with ``-n``.

Paths in help text
------------------

Relative paths in help text are relative to the folder of the code file,
as in sidecar docs (:doc:`sidecars`), not to the documentation page:

.. code-block:: matlab

   function y = scale(x)
   % SCALE Scale a value.
   %
   % .. image:: img/plot.png
   %
   % The `guide <guide.md>`_ and the :download:`data <data/values.csv>`.

* images (``image``, ``figure``) and downloads (``:download:``) are copied
  into the output;
* ``literalinclude`` and ``include`` read files next to the code file;
* a hyperlink to a relative path goes to a sidecar doc's document, to a
  code file's API entry, or downloads any other file; a link to a file
  that does not exist is left as it is.

Absolute paths (``/img/logo.png``) stay relative to the Sphinx source
folder, and ``:doc:`` and ``:ref:`` name documents and labels, not files.
Content written in the page, inside an auto directive, stays relative to
the page.

Links in help text
------------------

:confval:`matlab_auto_link` turns names in help into links, so that help
written for MATLAB links without markup:

``"basic"``
   * The entries of a "See also" line, and of the lines that follow it up to
     a blank line: functions, classes, and the methods and properties of the
     documented class. Names that match nothing are shown as code.
   * In class help, the entries of MATLAB's ``<Class> Properties:`` and
     ``<Class> Methods:`` lists (``name - description``) become a bulleted
     list of links.

``"all"``
   Also every name of a documented class or function anywhere in the help
   (not in literal blocks or existing markup), ``Class.member`` names, and
   ``name()`` for methods of the class.

Names are looked up from the folder of the documented file, as in
:doc:`referencing`; a name several files share gets a ``mat.ambiguous``
warning and no link. ``shapes.Circle`` on :doc:`documenting` shows "See
also" links; ``shapes.Shape`` shows the class lists.

"See also" is recognized anywhere in a line, in any letter case, so a
sentence such as "... ignored). See also the manual." also starts a list.
Which lines MATLAB itself treats as "See also" lines has not been checked
yet.
