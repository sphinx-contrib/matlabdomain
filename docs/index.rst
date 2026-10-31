.. sphinxcontrib-matlabdomain documentation master file, created by
   sphinx-quickstart on Tue Jul 17 11:53:15 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

sphinxcontrib-matlabdomain
==========================

**sphinxcontrib-matlabdomain** is `Sphinx`_ extension to generate API
documentation for `MATLAB`_, it also provides *autodoc* facilities, that lets
you generate documentation *automatically* from MATLAB source files. It works
similar to the  `Python Domain`_.


Getting started
---------------

If you are completely new to `Sphinx`_, follow this `Tutorial`_.

Install **sphinxcontrib-matlabdomain** with

::

   pip install sphinxcontrib-matlabdomain

It needs Python 3.11 or newer and Sphinx 8.0 or newer, and is tested on Linux,
Windows and macOS. Path references and patterns are case-sensitive on every
system; on a case-insensitive file system (the Windows and macOS default),
names that differ only by case are handled on a best-effort basis.

In order for the Sphinx MATLAB domain to auto-document MATLAB source code, set
the config value of ``matlab_src_code_project_root`` to the root folder of the
MATLAB sources. A relative path is relative to the Sphinx source directory
(the folder with ``index.rst``). All subfolders of the root are searched,
unless patterns select the files (see `Source files and builds`_).
``matlab_src_dir`` was removed: setting it is an error; use
``matlab_src_code_project_root``.

For convenience the `primary domain <http://sphinx-doc.org/config.html#confval-primary_domain>`_
can be set to ``mat``.

Assuming that the directory structure of the project is ike this:

::

   docs/
       conf.py
       index.rst
       make.bat
       Makefile
   src
       <matlab source files>

The ``docs/conf.py`` would look like this:

.. code-block:: python

   # other statements

   extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.matlab']
   matlab_src_code_project_root = '..'
   primary_domain = 'mat'

Example
-------

.. autofolder:: src

.. autofunction:: times_two

.. autofunction:: times_two_napoleon

Using auto-directives
---------------------

* Creating a Sphinx project
* Modifying ``conf.py`` to include **sphinxcontrib-matlabdomain**  and autodoc.
* Add ``matlab_src_code_project_root`` with root of MATLAB sources
* List directives and options
* Using auto-directives
* Using napoleon - different style docstrings, that are almost like MATLAB
* Examples

  * Function
  * Function in package
  * Class with inheritance and properties
  * Class folder (have to use autofunction)

* Known limitations

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   CHANGES.rst
   DEVELOPMENT.rst


MATLAB names and link anchors
-----------------------------

Every documented object is identified by its *path reference*: its path
relative to ``matlab_src_code_project_root``, with ``/`` separators, Unicode
NFC and the file extension. Members follow the file with ``.``; folders end
with ``/`` and the root is ``./``.

.. list-table::
   :header-rows: 1

   * - Source
     - Path reference
     - MATLAB name (displayed)
   * - ``target/+package/ClassBar.m``
     - ``target/+package/ClassBar.m``
     - ``package.ClassBar``
   * - its method ``myMethod``
     - ``target/+package/ClassBar.m.myMethod``
     - ``package.ClassBar.myMethod``
   * - ``src/+pkg/@Cls/Cls.m``
     - ``src/+pkg/@Cls/Cls.m``
     - ``pkg.Cls``
   * - ``src/private/helper.m``
     - ``src/private/helper.m``
     - ``helper``
   * - folder ``target/+package``
     - ``target/+package/``
     - ``package``

Signatures and the inventory's display names show the MATLAB name, formed the
way MATLAB forms it: ``+pkg`` folders are namespaces, ``@Cls`` folders define
class ``Cls``, and files in plain folders are global names. ``matlab_version``
(default ``"R2026a"``, oldest ``"R2025a"``) selects release-dependent rules,
and ``matlab_namelengthmax`` (``63`` or ``2048``; default derived from
``matlab_version``) the identifier length limit. Files MATLAB cannot call
(keyword namespaces such as ``+for``, invalid file names, class files that do
not match their ``@`` folder, ``@C/sub`` files from R2026a, ...) have no
MATLAB name: they are documented and displayed by path, with one
``mat.not_callable`` warning each, which ``suppress_warnings`` can turn off.
Files below ``private/`` never warn.

Auto directives, cross-references (``:mat:func:`...```), auto-links and "See
also" entries resolve a name in this order:

1. an exact path reference (``target/+package/ClassBar.m``);
2. relative to the current folder (set by ``mat:folder`` or
   ``mat:currentfolder``; inside a docstring, the documented file's folder):
   a path below it (``ClassBar.m``) or a MATLAB name visible from it,
   including the folder's ``private/`` files, like MATLAB;
3. a MATLAB name (``package.ClassBar``, ``package.ClassBar.myMethod``) that
   exactly one object has; ``private/`` files are not considered. If several
   objects have the name, a ``mat.ambiguous`` warning lists their path
   references, which you can use instead.

Folders use one directive, ``mat:folder`` (and ``mat:autofolder``); refer to
them with ``:mat:folder:``. A valid ``+`` folder shows ``namespace
package.sub`` and can also be referred to by that name; any other folder shows
``folder target/`` and is referred to by path. A folder path may omit its
trailing ``/``; that form is tried last, after MATLAB names. ``@Cls`` folders
are documented through their class. ``mat:currentfolder`` sets the current
folder without documenting it (``.`` is the root, ``None`` clears it).

The HTML anchor of an object is ``mat-`` followed by its path reference, in
which every ASCII character other than letters, digits and
``- . _ ! $ & ' ( ) * + , ; = : @ /`` is written as ``~XX`` per UTF-8 byte
(for example ``#mat-target/+package/ClassBar.m`` and
``#mat-my~20folder/f.m``). Distinct references never share an anchor. This
scheme is a stable contract: anchors, deep links and intersphinx inventories
only change if a file moves.

``matlab_keep_package_prefix`` and ``matlab_short_links`` were removed;
setting them is an error.

Help text, file types and warnings
----------------------------------

Docstrings follow MATLAB ``help`` (checked on R2026a):

* For a file's ``function`` or ``classdef``, the first comment block before
  the declaration is the docstring; without one, the block after the
  declaration line is. Blank lines may separate either block from the
  declaration. A license or copyright header at the top of a file therefore
  becomes the docstring, as in MATLAB.
* Methods use only the block after their ``function`` line; a comment block
  before them is ignored.
* A comment on the declaration line itself is not part of the docstring.
* Help text is the first run of ``%`` lines, as in MATLAB: a ``%{ ... %}``
  block comment gives only ``{``, because MATLAB stops at its first line
  that does not start with ``%``.

Each ``.m`` file is a script, function or class according to its first line
of code (blank lines, ``%`` comments and ``%{``/``%}`` blocks are skipped);
``function`` and ``classdef`` must be whole words (``functions = 1;`` is a
script). A script with local functions is a script.
Two warnings, which ``suppress_warnings`` can turn off, flag files to check:

* ``mat.invalid_matlab``: that type and the tree-sitter parse disagree, for
  example a ``classdef`` missing an ``end`` or ``function = 1;``. The file is
  probably not valid MATLAB; it is still documented, as what tree-sitter
  parsed.
* ``mat.no_code``: the file is empty or has only comments; it is documented
  as a script.

A file that is hard to read never stops the build: it gets one warning with
its path reference (and, where known, its source location), the build goes
on, and every other file is documented as usual (when each warning appears:
see `Source files and builds`_).

* ``mat.parse_error``: the file cannot be read (for example no permission),
  an ``.mlapp`` is not a valid App Designer file, or the parser fails. The
  file is still indexed, with the type of its first line of code (an
  unreadable file has type ``unknown``), and documented without content, so
  references to it still resolve. An unreadable file is retried on every
  build. A folder that cannot be listed, or a file name that is not valid
  UTF-8, gets the same warning and is left out.
* ``mat.encoding``: see below.
* A ``function`` declared with a dotted name (``function y = pkg.f(x)``)
  raises ``mat.invalid_matlab``. MATLAB (R2026a) names such a file by its
  path, shows its help, and refuses to run it ("Dotted names can be used
  only within a CLASS block"); it is documented the same way, under its
  file name. Converter methods with dotted names inside a ``classdef`` are
  valid MATLAB but are not documented, like ``set.``/``get.`` methods.

Source files are read as MATLAB R2026a reads them. A byte-order mark selects
UTF-8, UTF-16 or UTF-32. Otherwise ``matlab_src_encoding`` (default ``None``),
a Python text codec, decodes every ``.m`` file; an unknown codec is a
configuration error. Without it, files are read as UTF-8, and a file that is
not valid UTF-8 is read using the Windows ANSI code page on Windows or
ISO-8859-1 (Latin-1) elsewhere, the whole file, with one ``mat.encoding``
warning that gives the line of the first invalid byte. These fallbacks were
checked with MATLAB R2026a on Windows and Linux: on Windows with code page
1252, byte ``0x80`` becomes ``€``; on Linux it becomes U+0080. A UTF-8 ``é``
elsewhere in such a file shows as ``Ã©`` on either system. Bytes that the
selected codec cannot decode are shown as U+FFFD, with a ``mat.encoding``
warning (MATLAB rejects invalid bytes after a byte-order mark).

MATLAB and Simulink read some files by name: ``Contents.m`` (folder help),
``slblocks.m``, ``sl_customization.m``, ``pathdef.m``, ``matlabrc.m`` and
``rtwmakecfg.m`` (any letter case). They are indexed and can be documented
with an explicit directive, but ``mat:autofolder`` with ``:members:`` leaves
them out and they never raise ``mat.invalid_matlab``, ``mat.no_code`` or
``mat.not_callable``.

Source files are found by extension through a file-type registry. ``.m`` and
``.mlapp`` (App Designer) files are supported; Simulink (``.slx``, ``.mdl``,
``.xml``) and Simscape (``.ssc``) files are planned.

Source files and builds
-----------------------

Two glob lists select the source files below
``matlab_src_code_project_root``:

* ``matlab_src_include_patterns`` (default ``["**/*"]``, every file): a file
  is documented if its path reference matches one of them. ``[]`` selects no
  files.
* ``matlab_src_exclusion_patterns`` (default ``[]``): files and folders that
  match one of them are left out, e.g. ``["**/tests/**"]`` or
  ``["**/tests"]``.

Patterns are matched like Sphinx's ``exclude_patterns``, against path
references: ``**`` matches across folders, ``*`` and ``?`` within one, and
``**/x`` also matches ``x``. Matching is case-sensitive on every operating
system. A pattern is relative to the project root and uses ``/``; an
absolute path, a drive, a ``\``, or ``..`` that leaves the root (or follows
a wildcard) is a configuration error, and so is setting either list without
``matlab_src_code_project_root``, or a pattern whose leading folders lead
out of the root through a link. Folders whose names start with ``.`` or
``_`` are never searched. A link (or Windows junction) found below the root
that points outside it is left out with one ``mat.outside_root`` warning.

Each build first *indexes* the selected files: it reads each file once,
decodes it and finds its type from its first line of code. A file is parsed
with tree-sitter only when a page needs it, for example to document it, to
show its base classes, or to link a name in a docstring. Parses are kept in
the environment while a file's path, modification time and size do not
change, so the next build neither reads nor parses an unchanged file again.
With
``matlab_src_cache_text`` (default ``True``), the text the index read is
kept in memory for the parse, during that build only.

Only pages that used a changed file are read again. When files or folders
are added, removed, or change type, every page that looks up MATLAB sources
is read again. Parallel builds (``-j``) are supported.

Warnings about the source files appear at two times:

* On every build, for every indexed file: ``mat.encoding``, ``mat.no_code``,
  ``mat.not_callable``, ``mat.outside_root``, and ``mat.parse_error`` for a
  file or folder that cannot be read.
* When a page read in this build uses the file, once per build:
  ``mat.invalid_matlab`` and ``mat.parse_error`` for a file that cannot be
  parsed. A file that no page uses is not parsed, so these do not appear
  for it.

Generating pages: ``sphinx-matlab-apidoc``
------------------------------------------

``sphinx-matlab-apidoc`` writes reST pages that document every MATLAB file
below a project root with the auto-directives, so a large project needs no
hand-written directives. ``examples/apidoc`` in the repository is a worked
example with a sample project, its generated pages and edited templates.

::

   sphinx-matlab-apidoc [OPTIONS] -o OUTPUT_DIR ROOT
   python -m sphinxcontrib.matlab_apidoc [OPTIONS] -o OUTPUT_DIR ROOT

``ROOT`` is the folder ``matlab_src_code_project_root`` points to. The
command indexes the files like a build does (it does not parse them) and
reads no ``conf.py``: keep ``--include``, ``--exclude``,
``--matlab-version`` and ``--encoding`` equal to
``matlab_src_include_patterns``, ``matlab_src_exclusion_patterns``,
``matlab_version`` and ``matlab_src_encoding``. Then add the root page
(``index`` in ``OUTPUT_DIR``) to a toctree.

Pages:

* One page per folder with a file to document at or below it, at
  ``OUTPUT_DIR/<folder path>/index.rst``; the root folder's page is the toc
  file. Characters other than ``A-Z a-z 0-9 _ . + @ -`` in a folder or
  file name become ``~XX`` per UTF-8 byte in the output names.
* A page is titled with the folder's signature (``namespace pkg.sub`` or
  ``folder src/util/``), has ``mat:autofolder``, a local table of contents,
  the sections Classes, Functions, Scripts and Apps, and a toctree of its
  subfolders' pages (namespaces, then folders, then ``private/``).
* Each file gets a heading (its MATLAB name, or its path if MATLAB cannot
  call it) and ``mat:autoclass`` (with ``:members:``, ``:undoc-members:``
  and ``:show-inheritance:``), ``mat:autofunction``, ``mat:autoscript`` or
  ``mat:autoapplication`` with its path reference.
* ``@`` class folders are listed on the page of the folder above them. The
  function files of a class folder ``@X/`` whose ``X.m`` is a classdef are
  documented as methods of that class. Any other ``@`` folder (an old-style
  class, a classdef named differently, no class file) is not a class: all
  its files are listed. ``Contents.m`` and the other special files are left
  out.

Options:

* ``--include PATTERN``, ``--exclude PATTERN`` (repeatable),
  ``--matlab-version``, ``--encoding``: as the configuration values above.
* ``-f``, ``--force``: overwrite existing files. Without it, existing files
  are kept. Files are written as UTF-8 with ``\n`` line ends, and only when
  their text changes, so unchanged pages are not read again by Sphinx.
* ``-n``, ``--dry-run``: write and delete nothing; list what would change.
* ``-e``, ``--separate``: one page per file; folder pages list them in
  toctrees.
* ``-d``, ``--maxdepth`` (default 4): ``:maxdepth:`` of the toctrees.
* ``--tocfile`` (default ``index``), ``--suffix`` (default ``rst``).
* ``-t``, ``--templatedir``: a folder with ``folder.rst.jinja`` and/or
  ``object.rst.jinja`` that replace the default templates.
* ``--remove-old``: delete the files with the current suffix below
  ``OUTPUT_DIR`` that start with the generated marker line (``.. Generated
  by sphinx-matlab-apidoc.``) and were not generated by this run, and the
  folders this leaves empty. Files without the marker, other suffixes and
  folders whose names start with ``.`` or ``_`` are never touched.
* ``-q``, ``--quiet``: print only warnings. ``--version``.

The exit status is 0 on success, also with warnings, and 2 for usage or
setting errors.

To change the output, copy the templates from
``sphinxcontrib/matlab_apidoc/templates/``, edit them and pass their folder
with ``-t``. The template context is a public interface: keys may be added,
but renaming or removing one is a breaking change. ``folder.rst.jinja``
gets:

* ``docname`` (the page, relative to ``OUTPUT_DIR``), ``ref`` (the folder's
  path reference), ``title``, ``kind`` (``namespace``, ``folder`` or
  ``root``), ``is_root``;
* ``sections``: ``(title, entries)`` pairs;
* ``subfolders``: the docnames of the subfolders' pages, relative to this
  page;
* ``separate`` and ``maxdepth``: the options.

Each entry has ``ref``, ``kind`` (``class``, ``function``, ``script``,
``application``), ``directive`` (e.g. ``mat:autoclass``), ``options`` (a
dict of directive options), ``title`` (the heading), ``display`` (the name
signatures show), ``matlab_name`` (``None`` if MATLAB cannot call the
file), ``callable``, ``private`` and ``docname`` (with ``--separate``, its
page relative to the folder page; else ``None``). ``object.rst.jinja``
(with ``--separate``) gets the keys of one entry, with ``docname`` relative
to ``OUTPUT_DIR``. Both templates are rendered with Sphinx's
``ReSTRenderer``, which adds the ``e`` (escape) and ``heading`` filters.

Checking help text: ``matlab-api-check``
----------------------------------------

The ``matlab-api-check`` builder checks the help text of the MATLAB sources,
for example in CI::

   sphinx-build -b matlab-api-check docs docs/_build/api-check

It reads the pages like any builder (give it the ``-d`` folder of the HTML
build to avoid reading them twice), but it checks every indexed file, whether
a page documents it or not, on every run, and writes no pages. It checks
functions, classes, scripts, apps and public methods: static methods and
constructors, not ``Access = private``, ``protected`` or an access list,
not ``Hidden``; ``get.`` and ``set.`` methods are not checked. Files below
``private/`` are checked; ``Contents.m`` and the other special files, files
that cannot be read and files that cannot be parsed are not.

.. list-table::
   :header-rows: 1

   * - Rule
     - Checks
     - Passes when
   * - ``description``
     - functions, classes, scripts, apps
     - the first help line (MATLAB's H1 line) is not blank
   * - ``method-description``
     - methods
     - the same
   * - ``inputs``
     - functions and methods with inputs
     - the help has an inputs section, or every input has an
       ``arguments``-block comment
   * - ``outputs``
     - functions and methods with outputs
     - the help has an outputs section, or every output has an
       ``arguments (Output)`` comment
   * - ``name-value``
     - functions and methods with name-value arguments
     - the help has a name-value section, or every name-value argument has an
       ``arguments``-block comment

Inputs are the named inputs except ``~``, the object of a method that is not
static or a constructor, and the structure of name-value arguments;
``varargin`` counts. A constructor's output (the object) does not count;
``varargout`` does. Name-value arguments are the ``opts.Name`` entries of
``arguments`` blocks; name-value pairs that the code parses itself
(``varargin``, ``inputParser``) are not detected.

A section starts with a help line that begins with one of these labels, in
any letter case:

* inputs: ``Input``, ``Inputs``, ``Input(s)``, ``Input Arguments``, ``Input
  Parameters``, ``Arguments``, ``Parameters``, ``Params``, ``Required
  Inputs``, ``Required Arguments``, ``Optional Inputs``, ``Optional
  Arguments``, ``Optional Parameters``;
* outputs: ``Output``, ``Outputs``, ``Output(s)``, ``Output Arguments``,
  ``Output Parameters``, ``Returns``, ``Return Values``, ``Return
  Arguments``;
* name-value: ``Name-Value Arguments``, ``Name-Value Pairs``, ``Name/Value
  Pair Arguments``, ``Name-Value Options`` (``-``, ``/``, a space or nothing
  between the words; also with ``Optional`` before them), ``Options``,
  ``Optional Inputs``, ``Optional Arguments``, ``Optional Parameters``;
  ``Input Arguments (Name-Value Arguments)`` counts for inputs and
  name-value arguments.

The label is followed by ``:`` and anything (``Inputs: x - data``,
``Options::``), or by a short qualifier and a ``:`` that ends the line
(``Inputs (all optional):``, ``Parameters and their meaning:``), or stands
alone (``INPUTS``, or ``Parameters`` underlined with ``---``). A lowercase
label alone right after a line of text is a wrapped word of prose, not a
header. A label that is the name of one of the function's arguments and has
text after its ``:`` is that argument's entry (``input: the data``), not a
header.

Configuration (changing it does not make Sphinx read pages again):

* ``matlab_api_check_rules`` (default ``{}``): rule name to severity,
  ``"error"``, ``"warning"`` or ``"ignore"``, over the default ``"error"``
  of every rule, for example ``{"method-description": "warning", "name-value":
  "ignore"}``. An unknown rule or severity is a configuration error.
* ``matlab_api_check_enabled`` (default ``True``): ``False`` checks nothing;
  the reports say so.
* ``matlab_api_check_ignore_patterns`` (default ``[]``): globs, with the
  rules of ``matlab_src_exclusion_patterns``, matched against path
  references of files and of methods (``+pkg/Cls.m.helper``); matching
  objects are not checked.

Each finding is logged with its path reference, MATLAB name and rule, at the
line of its declaration, as an ``ERROR`` (severity ``error``) or a
``WARNING`` (``warning``) of type ``mat.api_check``. The output folder gets
``api-check.txt`` (one line per finding, then a summary) and
``api-check.json`` (``summary``: ``enabled``, ``rules``, ``checked`` per
kind, ``not_checked``, ``findings`` per rule and severity, ``errors``,
``warnings``; ``findings``: ``reference``, ``name``, ``kind``, ``rule``,
``severity``, ``line``, ``message``). The exit status is 1 when a finding
has the severity ``error``; with ``-W``, any finding fails the build, like
any warning.

Directives
----------

Indices and tables
==================

* :ref:`genindex`
* :ref:`mat-folderindex`
* :ref:`search`

.. _Sphinx: https://http://www.sphinx-doc.org
.. _Python Domain: http://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#the-python-domain
.. _Tutorial: http://www.sphinx-doc.org/en/1.7/tutorial.html
.. _MATLAB: https://mathworks.com
