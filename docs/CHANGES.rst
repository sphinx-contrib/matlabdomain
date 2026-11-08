Release notes
=============

1.0.0 (Unreleased)
------------------

The first stable release; from here on the project follows semantic
versioning. 1.0 is a rewrite and breaks with 0.x in many places: read
"Migrating from 0.22 and earlier" in the documentation before upgrading.
The changes below are relative to 0.22.1.

Highlights
^^^^^^^^^^

* MATLAB names as MATLAB forms them (namespaces, class folders,
  ``private/``) and a path reference for every file.
* Fast builds of large projects: an index of the source files, parsing only
  when a page needs a file, incremental and parallel (``-j``) builds.
* One command, ``scmd``: ``quickstart`` sets up a project, ``apidoc`` writes
  the API pages, ``skills`` copies agent skills into a project.
* A ``matlab-api-check`` builder that audits the help text.
* Simulink files, sidecar docs (Markdown and reST notes next to the code)
  and stable addresses for every documented object.
* Rewritten documentation: getting started, a user guide, a reference of
  every configuration value, directive, role, option and warning, and a
  developer guide. Examples are rendered by the documentation's own build.
  It also covers several projects and versions (sphinx-multiversion,
  sphinx-multiproject) and one search over several sites.

Requirements
^^^^^^^^^^^^

* Python 3.11 or later and Sphinx 8.0 or later (support for Python 3.10 and
  Sphinx 7 and earlier is dropped).
* Source files are parsed with tree-sitter (``tree-sitter`` 0.26 and
  ``tree-sitter-matlab`` 1.3.3) instead of a Pygments lexer; the module
  ``sphinxcontrib.mat_lexer`` is removed.
* ``sphinxcontrib`` is a native (PEP 420) namespace package, like in the
  other ``sphinxcontrib-*`` packages: ``sphinxcontrib/__init__.py`` is no
  longer shipped. It imported ``pkg_resources``, so without setuptools the
  package, and Sphinx's own ``sphinxcontrib`` extensions, failed to import.
* Markdown sidecar docs need the new ``markdown`` extra (myst-parser).
* ``sphinxcontrib.matlab`` sets up ``sphinx.ext.autodoc`` itself; it no
  longer needs to be in ``extensions``.
* Environments pickled by 0.x are rebuilt.

Breaking changes
^^^^^^^^^^^^^^^^

Names and references:

* Objects are identified by path reference, the path relative to the
  project root with its extension (``target/+package/ClassBar.m``, members
  ``target/+package/ClassBar.m.myMethod``, folders ``target/+package/``).
  Signatures and the inventory's display names show the MATLAB name
  (``package.ClassBar``). Cross-references resolve an exact path reference,
  then relative to the current folder (including its ``private/``), then a
  unique MATLAB name; an ambiguous name warns and lists the matching
  references. There is no found-first precedence.
* Anchors are ``mat-`` followed by the escaped path reference
  (``#mat-target/+package/ClassBar.m``); inventory names are path
  references. Dotted anchors, ``module-`` anchors and aliases are gone, so
  existing deep links and intersphinx references change.
* ``mat:module``, ``mat:automodule``, ``mat:currentmodule`` and
  ``:mat:mod:`` are replaced by ``mat:folder``, ``mat:autofolder``,
  ``mat:currentfolder`` and ``:mat:folder:``. A valid ``+`` folder shows
  ``namespace <name>``, any other folder ``folder <path>``; ``@Class``
  folders are documented through their class. The module index is now the
  folder index (``mat-folderindex.html``).
* Files MATLAB cannot call for :confval:`matlab_version` (keyword
  namespaces, invalid names, ``@C/sub`` files from R2026a, ...) are
  documented by path with one ``mat.not_callable`` warning each that says
  why; files below ``private/`` never warn.
* A folder named like a file the extension reads (``.m``, ``.mlapp``,
  ``.slx``, ``.mdl``, ``.xml``, ``.md``, ``.rst``, any case) is not
  documented and logs the error ``mat.folder_name``.

Configuration:

* ``matlab_src_dir`` is replaced by ``matlab_src_code_project_root``
  (relative to the Sphinx source folder). Setting ``matlab_src_dir``,
  ``matlab_keep_package_prefix`` or ``matlab_short_links`` is a
  ``ConfigError``; one error names every removed value that is set.
* A ``matlab_*`` name that is not a configuration value (a typo, a helper
  variable) is a ``ConfigError`` in the build and in ``scmd apidoc``, with
  the closest value as a suggestion, also when another extension sets it
  while the configuration is read (sphinx-multiproject's ``config``
  option).
* :confval:`matlab_show_property_default_value` and
  ``matlab_show_property_specs`` default to ``True``: properties show their
  default value, size, class and validators. Set them to ``False`` for the
  0.x output.
* ``matlab_add_namespace_names`` (default ``True``) replaces Sphinx's
  ``add_module_names`` for MATLAB signatures; the MATLAB domain no longer
  reads ``add_module_names``.
* ``matlab_src_encoding`` is applied (it was ignored). A byte-order mark
  selects UTF-8/16/32; otherwise the configured codec, or by default UTF-8,
  where a file that is not valid UTF-8 uses the Windows ANSI code page on
  Windows or ISO-8859-1 elsewhere, like MATLAB R2026a, with a suppressible
  ``mat.encoding`` warning. An unknown or non-text codec is a
  ``ConfigError``.

Help text:

* Docstrings follow MATLAB ``help`` (R2026a). A comment block before a
  file's ``function`` or ``classdef`` line wins over the block after it, so
  licence and copyright headers become the docstring (#269). Blank lines
  between a declaration and its block are allowed. Methods keep using the
  block after their ``function`` line. Like MATLAB ``help``, the text is
  the first run of ``%`` lines, so a ``%{ ... %}`` block comment gives
  ``{``.
* Relative paths in help text are relative to the folder of the code file,
  as in sidecar docs: images, figures, downloads, ``literalinclude``,
  ``include`` and hyperlinks. They were relative to the documentation page.
  Links with a URI scheme (an e-mail address, ``matlab:``) are left as they
  are.
* ``.m`` files are classified by their first line of code, as MATLAB does:
  a script with local functions is a script, not a function.

Classes:

* The ``mat:classmethod`` directive is removed: MATLAB has no class methods
  apart from static methods; use ``mat:staticmethod``.
* A method in its own file of a class folder takes the attributes of its
  signature in the ``classdef`` (``methods (Static)`` with ``out =
  make(x)``): it is documented as ``mat:staticmethod`` when static, and
  ``mat:autoclass`` leaves it out when it is private, protected,
  access-listed or hidden, unless an option adds it (#44, #299). Such
  methods were all public and non-static before, so a page that links to
  one needs the option that documents it (``:private-members:``, ...).
* The signature of a static method keeps a first input named ``obj`` or
  ``self`` (``static make(obj, y)``): a static method has no object, so
  that input is a real one.
* The function files of a class folder ``@X/`` are methods only if ``X.m``
  is a classdef. In any other ``@`` folder (an old-style class, a classdef
  named differently, no class file) they are documented as functions.

Directives and options:

* Python-domain features that do not apply to MATLAB are removed: the
  ``mat:decorator``, ``mat:decoratormethod``, ``mat:exception`` and
  ``mat:autoexception`` directives, the ``:mat:exc:`` role, and the
  ``:special-members:`` and ``:inherited-members:`` options of
  ``mat:autoclass`` (``:inherited-members:`` crashed the build). Names in
  ``:raises:`` fields link to classes.
* The auto directives accept only the options that do something.
  ``mat:autofolder`` no longer accepts ``:inherited-members:``,
  ``:special-members:``, ``:imported-members:``, ``:ignore-module-all:``
  and ``:no-value:``; ``mat:autodata`` no longer accepts ``:annotation:``
  and ``:no-value:``; no auto directive accepts ``:no-index-entry:``.

Contributors:

* The ``dev`` and ``rtd`` extras are dependency groups (``dev``, which
  includes ``test`` and ``docs``); ``uv sync`` installs ``dev``. With pip:
  ``pip install -e . --group dev`` (pip 25.1 or later).

New features
^^^^^^^^^^^^

Commands:

* New command ``scmd`` (also installed as ``sphinxcontrib-matlabdomain``)
  with the subcommands ``quickstart``, ``apidoc`` and ``skills``. All
  options have short and long forms.
* ``scmd quickstart`` sets up Sphinx documentation for a MATLAB project. It
  asks one question per choice, with defaults read from the project (the
  MATLAB release in its CI files and README, git submodules, the MATLAB
  project path, uv, Markdown notes next to the code, a survey of the help
  headings for ``napoleon_custom_sections``), and writes ``conf.py``,
  ``index.rst``, ``Makefile``, ``make.bat``, a build guide and the API
  pages. In a uv project it adds the docs dependencies with ``uv add
  --frozen --group docs``, the matlabdomain requirement copied from how
  matlabdomain is installed; it adds lines to ``.gitignore`` and
  ``.gitattributes``, and stops if one of these files has uncommitted
  changes. ``-n`` writes nothing and prints what it would write;
  ``--answers FILE`` reads saved answers; ``-q`` asks nothing. It prints a
  report: the inventory, the help headings, the copyright blocks that run
  into help, and the next steps.
* ``scmd apidoc`` writes reST pages with ``mat:auto*`` directives for the
  MATLAB files of a project, from Jinja templates that can be replaced
  (``matlab_apidoc_templatedir``). By default (``matlab_apidoc_group =
  "namespace"``) it writes one page per namespace, merging all its
  folders, and Global for the files outside any namespace, listed flat on
  the root page; sections Functions, Classes, Scripts, Apps, the Simulink
  sections and the sidecar docs; at most ``matlab_apidoc_page_size``
  entries (default 100) per page; ``private/`` files are left out
  (``matlab_apidoc_private = True`` lists them with the folder above).
  ``matlab_apidoc_group = "folder"`` writes one page per folder with files,
  titled by path. It reads every setting from ``conf.py`` (``-c DIR``,
  default the current folder): the source settings of the build and the
  ``matlab_apidoc_*`` values (output folder, grouping, page size, one page
  per file, toctree depth, root page, suffix, templates, removal of stale
  pages). Its flags only control a run: ``-f``, ``-n``, ``--check``
  (exits with 1 when the pages are out of date), ``-q``. Generated pages
  (those that start with its marker line) are rewritten when they change
  and removed when they are no longer pages; a page that differs only in
  line endings is unchanged. Its template context is a public interface:
  renaming or removing a key is a breaking change. See
  ``examples/apidoc``. For full control, a script calls the Python API
  (``IndexSettings``, ``build_index``, ``generate``, ``ApidocOptions``).
  It does not run inside ``sphinx-build``; run it before the build.
* ``scmd skills install`` copies the agent skills that ship with the
  package (``setting-up-a-project``, ``migrating-from-0x``) into a project,
  by default to ``.github/skills``; ``scmd skills list`` lists them.

Checking help text:

* New builder ``matlab-api-check`` (``sphinx-build -b matlab-api-check``):
  checks the help text of every indexed function, class, public method,
  script and app (the H1 line; inputs, outputs and name-value sections, or
  ``arguments``-block comments; examples; property and event descriptions;
  sidecar docs), logs each finding as ``mat.api_check``, writes
  ``api-check.txt`` and ``api-check.json``, and exits with status 1 when a
  rule with severity ``error`` finds something. Configuration:
  ``matlab_api_check_rules``, ``matlab_api_check_ignore_patterns`` and
  ``matlab_api_check_section_labels`` (the labels each section accepts;
  ``"<built-in>"`` adds the built-in ones back). Hidden classes and
  members and abstract methods are not checked.
* ``matlab_api_check_files`` and ``matlab_api_check_files_from`` check only
  the selected files (paths or glob patterns relative to the project root;
  ``folder/`` for the files below a folder), for example the files a
  change touches; the index, pages and links stay those of the whole
  project. An entry that selects no file is an error unless
  ``matlab_api_check_ignore_unmatched`` is ``True``.

Source files:

* ``matlab_src_include_patterns`` (default ``["**/*"]``) and
  ``matlab_src_exclude_patterns`` (default: the root files ``README.*``,
  ``CHANGES.*``, ``CHANGELOG.*``, ``LICENSE.*``, ``CONTRIBUTING.*``,
  ``CODE_OF_CONDUCT.*`` and ``SECURITY.*``) select the files: globs
  relative to the project root, matched like ``exclude_patterns``,
  case-sensitive (#271). A link below the root that leaves it is skipped
  with a ``mat.outside_root`` warning.
* Folders whose names start with ``_`` are documented like any other
  folder (#337). Hidden folders (``.git``) and Sphinx output are skipped:
  the ``_build`` folder of the Sphinx source folder, and folders with
  Sphinx's ``.buildinfo``, ``environment.pickle`` or ``doctrees``.
* :confval:`matlab_version` (default ``"R2026a"``, oldest supported
  ``"R2024a"``) selects version-dependent MATLAB naming rules: scripts and
  functions in a subfolder of a class folder (``@C/sub/x.m``) are callable
  before R2026a only; identifiers may have 2048 characters from R2025a on,
  63 before.
* ``Contents.m``, ``slblocks.m``, ``sl_customization.m``, ``pathdef.m``,
  ``matlabrc.m`` and ``rtwmakecfg.m`` are left out of ``mat:autofolder``
  members; an explicit directive still documents them.
* Source files are found through a file-type handler registry (``.m``,
  ``.mlapp``, Simulink files), the extension point for more file types.

Builds:

* Each build indexes the source files (reads and classifies each file once)
  and parses a file with tree-sitter only when a page needs it. Parses are
  cached in the Sphinx environment by path, modification time and size;
  only pages that used a changed file are read again (#282). Parallel
  builds (``-j``) are supported (#147).
* One bad source file no longer stops the build. A file that cannot be
  read or parsed (permissions, a corrupt ``.mlapp``, a parser error) gets
  one suppressible ``mat.parse_error`` warning, with the line of the
  innermost syntax error when tree-sitter finds one, and is documented
  without content; references to it still resolve. An unreadable folder or
  a file name that is not valid UTF-8 warns the same way. Parse warnings
  are reported for the files that pages use, once per build; index
  warnings (``mat.encoding``, ``mat.empty_code_file``,
  ``mat.not_callable``) on every build.
* New warnings: ``mat.invalid_matlab`` when the type of a ``.m`` file and
  its parse disagree, for a ``function`` with a dotted name (documented
  under its file name, as MATLAB names it) and for a file with NUL bytes;
  ``mat.empty_code_file`` for empty files, which are documented as
  scripts. A help file (comments only) is documented as a script, or as a
  function when a MEX file of the same name is next to it.
* A Sphinx warning about help text names the file and the line of the help
  in it (``<file>:docstring of <reference>:<line>``).
* An auto directive that matches no object warns with ``mat.not_found``
  and the page and line of the directive.

Classes:

* Events are documented: an "Event Summary" section in ``mat:autoclass``,
  ``mat:autoevent``, the ``mat:event`` directive and the ``:mat:event:``
  role (#53). ``ListenAccess`` and ``Hidden`` filter them as ``Access`` and
  ``Hidden`` filter methods.
* Enumeration values are listed under "Enumeration Values" with their help
  (#54), and with their constructor arguments (``Red (1, 0, 0)``) when
  :confval:`matlab_show_property_default_value` is true.
* Abstract methods (declared without a body) are documented, marked
  ``abstract``, with their help found as for properties (#222).
* Signatures show MATLAB attributes: ``abstract`` and ``sealed`` classes
  and methods; ``abstract``, ``constant``, ``dependent`` and ``read-only``
  properties. New flag options of ``mat:class``, ``mat:method``,
  ``mat:staticmethod`` and ``mat:attribute`` (``:abstract:``,
  ``:sealed:``, ``:constant:``, ``:dependent:``, ``:read-only:``); the auto
  directives set them.
* ``mat:autoclass`` option ``:access-list-members:`` (MATLAB access lists:
  ``Access = ?Cls`` or ``{?A, ?B}``) replaces ``:friend-members:``, which
  is still accepted. A property or event whose read access (``GetAccess``,
  ``ListenAccess``) is an access list is left out unless this option adds
  it. ``mat:autofolder`` accepts ``:protected-members:``,
  ``:hidden-members:`` and ``:access-list-members:`` for the classes it
  documents.

Linking:

* References to another project's MATLAB objects
  (``sphinx.ext.intersphinx``) resolve by MATLAB name too
  (``:mat:class:`geom.Circle```), not only by path reference. The
  user-guide page "Linking between projects" gives the setup.
* HTML builds write a stable address for every documented object,
  ``mat/name/<MATLAB name>.html`` and ``mat/ref/<path reference>.html``,
  which redirect to the page the object is on; the "¶" link of an object
  and its entry in ``objects.inv`` point to it, so links survive page
  splitting. A copied address that no longer has the object, or a page
  that is gone (``404.html``), opens the object's stable address.
  ``matlab_stable_urls`` (default ``True``) turns it off. Incremental HTML
  builds remove the pages whose ``scmd apidoc`` source is gone.
* :confval:`matlab_link_shadowed_files_to_chooser_pages`: a name of
  several objects (two global ``helper.m``, ``foo.m`` and ``foo.slx``)
  links to a page that lists them, locally and through intersphinx.
* ``matlab_external_names``: regular expressions of names the project does
  not document; a reference to such a name is text, without a "reference
  target not found" warning. The default covers MATLAB's own classes and
  namespaces (``handle``, ``matlab.*``, ``double``, ...), so "Bases:
  handle" no longer needs a ``nitpick_ignore``.
* Types in ``:type x:`` and ``:vartype v:`` fields (as written by
  ``sphinx.ext.napoleon``) link to documented objects and are plain text
  otherwise, without nitpicky warnings.
* ``matlab_auto_link`` links "See also" entries only on a line that starts
  with "See also"; names between ``|`` bars (MATLAB's code markup) or next
  to ``/`` are not linked.
* Help lines that start with ``%%`` (a section start) lose both ``%``, as
  in MATLAB's ``help`` (#350): ``%% Inputs:`` gives ``Inputs:``.

Simulink files:

* The index reads Simulink models, libraries and subsystem files
  (``.slx``, ``.mdl`` and ``.xml`` exported by ``save_system``) without
  MATLAB, from every release since R2006a. They get MATLAB names as
  Simulink runs them, and a block of a library is referenced by its
  Simulink path after the file (``lib.slx/Group/Gain``).
* New directives ``mat:autosimulink_model``, ``mat:autosimulink_library``,
  ``mat:autosimulink_subsystem_reference`` and
  ``mat:autosimulink_library_block`` (and their description directives and
  roles) document the description, mask type, mask description and Help,
  metadata (:confval:`matlab_simulink_metadata`), mask parameters and
  ports. ``:members:`` of a library documents its blocks;
  ``:references:`` lists the model references, subsystem references and
  library links of a model. A ``.md`` or ``.rst`` file next to a Simulink
  file with its name adds documentation
  (:confval:`matlab_simulink_doc_suffixes`).
* ``scmd apidoc`` lists Simulink files in their own sections;
  ``matlab-api-check`` counts them as not checked. ``scmd quickstart`` adds
  ``+sphinxcontrib/+matlabdomain/simulinkDocumentationLinker.m`` to a
  project with Simulink files: Help fields call it to open the page of a
  model or block on the local build, the sphinx-autobuild server
  (:confval:`matlab_simulink_autobuild_server`) or the published site;
  ``sphinxcontrib.matlabdomain.setSimulinkHelp`` writes those Help fields.

Sidecar docs:

* Tutorials and notes as ``.md`` and ``.rst`` files among the MATLAB
  files, selected by ``matlab_src_sidecar_suffixes`` (default ``[]``, off)
  and the include and exclusion patterns. The directive
  ``mat:autosidecar`` renders one into a document, with relative images,
  downloads, includes and Markdown links resolved from its folder; the
  role ``:mat:sidecar:`` links to one. ``scmd apidoc`` writes a page for
  each and uses a folder's README as its introduction. New warning subtype
  ``mat.sidecar``.

Fixes
^^^^^

* The extension reports its version to Sphinx (#264).
* Member selection of ``mat:autoclass`` and ``mat:autofolder``: at the
  project root, members without help were listed without
  ``:undoc-members:``; ``Access = 'private'`` (quoted) counted as public;
  ``:members: a, b`` on a class documented nothing; ``autoclass_content =
  "both"`` added "The type of the None singleton." to a class without a
  constructor; ``mat:autofolder`` listed files in the file system's order
  (now sorted by name).
* ``matlab_auto_link``: a link next to a character that cannot border
  inline markup (``y=f(1)``) broke the reST; a line without a name (such
  as ``---``) after "See also" crashed the build; links and "Bases:"
  entries did not link without ``primary_domain = "mat"``.
* Parsing: attributes written ``~Hidden`` made a class fail to parse, and
  logical values written as numbers or with ``~`` (``Hidden = 0``,
  ``Static = ~true``) were read as ``true``; ``arguments`` blocks with
  ``~`` entries crashed; ``...`` between ``classdef``, the attributes, the
  name and the superclasses lost the superclasses, docstring and members;
  nested functions added their outputs, arguments and help to the
  enclosing function; help of only blank ``%`` lines crashed the build; an
  old-style property without a default (``p@double vector``) lost its type
  and size.
* Help text follows MATLAB R2026a: a lone CR ends a line; after ``...`` at
  the end of the superclasses, a comment on the continued line is not
  help; an ``arguments`` entry ending with ``;`` takes the comment after
  it, like a property.
* An invalid option of a ``mat:auto*`` directive is reported at the right
  file.
* The package metadata names the license in ``LICENSE``, BSD-2-Clause (it
  said BSD-3-Clause).

Project
^^^^^^^

* Jason H. Nicholson, author of the 1.0 rewrite, maintains the project;
  Jørgen Cederberg is a former maintainer (``AUTHORS``).
* Build, test and static-analysis policy is in ``pyproject.toml`` (Ruff,
  Pyright, tox); CI runs on Windows, macOS and Linux.

0.22.1 (2024-08-17)
-------------------

* Fixed `Issue 262`_. The API for
  ``sphinx.environment.BuildEnvironment.doc2path`` was changed to return a
  path-like object in Sphinx 8.0.2.

.. _Issue 262: https://github.com/sphinx-contrib/matlabdomain/issues/262


0.22.0 (2024-07-17)
-------------------

* Fixed `Issue 249`_. Parsing of multiline property default values.
* Fixed `Issue 252`_. Added missing class and method attributes.
* Fixed `Issue 243`_. Fixed issue with autolinking when the *short name* matches
  a module name.
* Fixed `Issue 250`_. Removed unused and undocumented
  ``MatInstanceAttributeDocumentor``, which hindered *Napoleon* to apply styling
  to inline on property comments.
* Added new configuration: ``matlab_show_property_specs``. When set to ``True``
  it will print the property specification for class properties.

.. _Issue 243: https://github.com/sphinx-contrib/matlabdomain/issues/243
.. _Issue 249: https://github.com/sphinx-contrib/matlabdomain/issues/249
.. _Issue 250: https://github.com/sphinx-contrib/matlabdomain/issues/250
.. _Issue 252: https://github.com/sphinx-contrib/matlabdomain/issues/252


0.21.5 (2024-02-10)
-------------------

* Fixed `Issue 240`_, where links in literal blocks where not detected
  correctly.

.. _Issue 240: https://github.com/sphinx-contrib/matlabdomain/issues/240


0.21.4 (2024-01-04)
-------------------

* Fixed issue with warning if there is a mismatch between filename and
  classname, if the classname is a reserved word (like arguments).
* Fixed a problem with `PR 230`_ introduced in solving `Issue 204`_: when more
  than one (sub)directory in the project had the same name, a dict was added to
  ``entities_table`` that broke autolinking (see also `Issue 235`_).

.. _PR 230: https://github.com/sphinx-contrib/matlabdomain/pull/230
.. _Issue 235: https://github.com/sphinx-contrib/matlabdomain/issues/235


0.21.3 (2024-01-02)
-------------------

* Fix issue with parsing of MATLAB files, where keywords were used in ``struct``
  fieldnames. E.g. ``a = pkg.arguments``. These were mistaken as ``keyword``
  tokens and could result in warnings with ``Check if valid MATLAB code.``.
* Bump copyright to 2024.


0.21.2 (2023-12-17)
-------------------

* Interpret ``matlab_src_dir`` relative to the Sphinx source directory to be
  compatible with `sphinx-multiversion`_.

.. _sphinx-multiversion: https://pypi.org/project/sphinx-multiversion/


0.21.1 (2023-12-16)
-------------------

* Fixed `Issue 204`_, that caused an ``AttributeError`` to be thrown if a module
  was named the same as the short name for a class.

.. _Issue 204: https://github.com/sphinx-contrib/matlabdomain/issues/204


0.21.0 (2023-12-16)
-------------------

* Allow ``matlab_src_dir`` to be a relative path of the ``conf.py`` file. See
  `PR 224`_ and `PR 225`_.
* Fixed `Issue 220`_. Parsing of property docstring could throw warning if there
  were blank lines between comments.
* Fixed `Issue 221`_. Using builtin's in class folder definition for methods
  defined in other files, threw a parsing warning.
* Fixed `Issue 225`_. Empty ``@classfolder`` would throw an assertion error.

.. _Issue 220: https://github.com/sphinx-contrib/matlabdomain/issues/220
.. _Issue 221: https://github.com/sphinx-contrib/matlabdomain/issues/221
.. _Issue 225: https://github.com/sphinx-contrib/matlabdomain/issues/225
.. _PR 224: https://github.com/sphinx-contrib/matlabdomain/pull/224
.. _PR 225: https://github.com/sphinx-contrib/matlabdomain/pull/225


0.20.2 (2023-09-15)
-------------------

* Fixed `Issue 214`_ again. Any folder below a ``@classfolder`` must be ignored.


0.20.1 (2023-09-14)
-------------------

* Fixed `Issue 214`_. After fixing `Issue 56`_, we introduced a bug parsing
  ``private`` folders incorrectly.

.. _Issue 214: https://github.com/sphinx-contrib/matlabdomain/issues/214


0.20.0 (2023-09-13)
-------------------

* Fixed `Issue 188`_ and `Issue 189`_, which caused the extension to crash if
  the documentation contained ``:exclude-members:``.
* Added a new configuration: ``matlab_auto_links``. It will automatically
  convert the names of known entities (e.g. classes, functions, properties,
  methods) to links! This means that we can write class documentation as `MATLAB
  Class Help`_ suggests. Including property and methods lists in the class
  docstring.
* Fixed `Issue 56`_. `MATLAB Folder Class definitions`_, i.e. prefixed with
  ``@``, are now treated as normal classes. All methods defined in the class
  definition and in files in the ``@``-folder are available. Further, it can
  referenced by a shortened name. Before you had to explicitly write out the
  "module", class and methods. Now you can just write the class name. Only
  caveat is that `Issue 44`_ still applies.

.. _Issue 44: https://github.com/sphinx-contrib/matlabdomain/issues/44
.. _Issue 56: https://github.com/sphinx-contrib/matlabdomain/issues/56
.. _Issue 188: https://github.com/sphinx-contrib/matlabdomain/issues/188
.. _Issue 189: https://github.com/sphinx-contrib/matlabdomain/issues/189
.. _MATLAB Class Help:  https://mathworks.com/help/matlab/matlab_prog/create-help-for-classes.html
.. _MATLAB Folder Class definitions: https://mathworks.com/help/matlab/matlab_oop/organizing-classes-in-folders.html


0.19.1 (2023-05-17)
-------------------

* Fix parsing of classes with trailing ``;`` after ``end``
* Fix bug if extension is included, but ``matlab_src_dir`` is not set.


0.19.0 (2023-05-16)
-------------------

* Added new configuration: ``matlab_short_links``. Finally, we are getting
  closer to render documentation closer to how MathWorks does it. The parsing of
  MATLAB functions, clasess, etc. was rewritten. We now parse all MATLAB files
  in ``matlab_src_dir``. Further, you can now generate docs for files in the
  root folder (something that only worked for packages before).
* We also updated the class rendering to be closer to that of MathWorks. Instead
  of putting both properties and methods together, they are now grouped by:
  *Constructor Summary*, *Property Summary* and *Method Summary*.


0.18.0 (2023-04-14)
-------------------

* Improved rendering of class property default values when
  ``matlab_show_property_default_value = True``. Multiline default values are
  now truncated to one line. Excessive spacing is removed and values are just
  shown verbatim as they were parsed instead of in string.


0.17.1 (2023-04-12)
-------------------

* Fix issue with incorrect parsing of baseclasses with trailing comments.
  Reported in `Issue 172 <https://github.com/sphinx-contrib/matlabdomain/issues/172>`_.


0.17.0 (2023-03-24)
-------------------

* Replace ``directive.warn`` (deprecated) with ``logger.warning``. Reported in
  `Issue 166 <https://github.com/sphinx-contrib/matlabdomain/issues/166>`_.
* Fix property validation parsing reported in
  `Issue 167 <https://github.com/sphinx-contrib/matlabdomain/issues/167>`_.
* Updated Author to Jørgen Cederberg as agreed in
  `Issue 164 <https://github.com/sphinx-contrib/matlabdomain/issues/164>`_.


0.16.0 (2023-03-15)
-------------------

* Add new option, ``matlab_show_property_default_value``. Default is now to not
  show property values. If a property value is ``None``, is not shown anymore.


0.15.2 (2023-03-14)
-------------------

* Fix issue with not parsing property docstrings correctly with Pygments 2.13.
  `Issue 152 <https://github.com/sphinx-contrib/matlabdomain/issues/152>`_.


0.15.1 (2023-02-06)
-------------------

* Fix being unable to document methods with name ``get``.
  `Issue 151 <https://github.com/sphinx-contrib/matlabdomain/issues/151>`_.


0.15.0 (2023-01-02)
-------------------

* Pygments >= 2.14.0 is now supported. Pygments tokenization changed to return
  ``Token.Text.WhiteSpace`` for newline characters. This resulted in a infinite
  loop when parsing MATLAB files.


0.14.1 (2022-09-02)
-------------------

* Fix parsing of overloaded class parameters with validation functions.
  `Issue 145 <https://github.com/sphinx-contrib/matlabdomain/issues/145>`_.
* Fix link in readme file.


0.14.0 (2022-06-01)
-------------------

* Sphinx >= 5.0.0 is now supported. Fixed errors due to `deprecated Sphinx API`_.
* Fixed `<https://github.com/sphinx-contrib/matlabdomain/issues/134>`_.
  JupyterBook complains if a domain doesn't support resolve_any_ref_.

.. _`resolve_any_ref`: https://www.sphinx-doc.org/en/master/extdev/domainapi.html?highlight=resolve_any_xref#sphinx.domains.Domain.resolve_any_xref


0.13.0 (2022-02-13)
-------------------

* Explicit set ``parallel_read_safe`` to ``False`` to avoid error in parallel
  builds.
* Fixed `Issue 125 <https://github.com/sphinx-contrib/matlabdomain/issues/125>`_.
  Finally, we are able to support *long* docstrings for properties. It works as
  the same as MATLAB. Comment lines above a ``property`` are now treated as
  docstrings.


0.12.0 (2021-06-12)
-------------------

* Only Sphinx >= 4.0.0 is now supported.
* Only Python >= 3.6 is supported.
* Fixed numerous warnings due to `deprecated Sphinx API`_.
  * Use ``sphinx.ext.autodoc.directive.DocumenterBridge.record_dependencies`` instead of ``sphinx.ext.autodoc.directive.DocumenterBridge.filename_set``.
  * Use ``str.rpartition()`` instead of ``sphinx.util.rpartition()``
  * Remove use of ``sphinx.util.force_decode()``.
  * Use ``inspect.getmembers()`` instead of ``sphinx.util.inspect.safe_getmembers()``.
  * Remove use of encoding argument in ``autodoc.Documenter.get_doc()``.
* Fixed `Issue 101 <https://github.com/sphinx-contrib/matlabdomain/issues/101>`_.
* CI now tests on Python 3.6, 3.7, 3.8 and 3.9.


0.11.8 (2021-05-12)
-------------------

*  Limit to Sphinx < 4.0.0, due to too many breaking changes.
*  Last version to support Python 2.7


0.11.7 (2021-02-24)
-------------------

* Fixed `Issue 117 <https://github.com/sphinx-contrib/matlabdomain/issues/117>`_.
  Parsing errors due to `"..."`.  Fix `MatObject::_remove_line_continuations`
  to take MATLAB strings into account.


0.11.6 (2021-02-23)
-------------------

* Fixed `Issue 116 <https://github.com/sphinx-contrib/matlabdomain/issues/116>`_.
  Failure on parfor statements in class methods. Fix `MatFunction` class to
  also take `parfor` into account when counting `end`.


0.11.5 (2021-01-05)
-------------------

* Fixed `Issue 114 <https://github.com/sphinx-contrib/matlabdomain/issues/114>`_.
  NoneType AttributeError in import_object. It was caused by a bug when parsing
  method names with trailing spaces.


0.11.4 (2020-11-30)
-------------------

* Remove import of ``six``.


0.11.3 (2020-10-10)
-------------------

* Fixed `Issue 108 <https://github.com/sphinx-contrib/matlabdomain/issues/108>`_.
  Quote is not recognized as transpose after a closing curly brace.

* Fixed `Issue 109 <https://github.com/sphinx-contrib/matlabdomain/issues/109>`_.
  Sphinx 3.1.1 changed API causing tests to fail.

* Fixed `Issue 111 <https://github.com/sphinx-contrib/matlabdomain/issues/111>`_.
  fnable Function Arguments Support.



0.11.2 (2020-05-18)
-------------------

* Fixed `Issue 103 <https://github.com/sphinx-contrib/matlabdomain/issues/103>`_.
  If a double quoted string was followed by a single quoted string, the lexer
  would produce incorrect token, causing the a parser warning. Fixed by merging
  parts from pygments.


0.11.1 (2020-01-07)
-------------------

* Fixed bug when Python and MATLAB sources are in the same base folder. Reported
  by Alec Weiss. Historically we stored parsed MATLAB objects in
  ``sys.modules``. However, this conflicts with Python modules.


0.11.0 (2019-10-29)
-------------------

* Fixed `Issue 93 <https://github.com/sphinx-contrib/matlabdomain/issues/93>`_.
  If a package class inherited from another package class, the link to the base
  class was incorrect. This is fixed now.
* Merged `PR #96 <https://github.com/sphinx-contrib/matlabdomain/pull/96>`_,
  which adds the option ``matlab_keep_package_prefix``. Setting this option,
  strips the ``+`` from package names. This gives far better rendering of
  documentation, as now closer resembles the actual usage for the end user.
* Merged `PR #97 <https://github.com/sphinx-contrib/matlabdomain/pull/97>`_,
  which adds support for documenting MATLAB application files with a new
  directive ``application``. They are referenced with ``app``


0.10.0 (2019-10-23)
-------------------

* Fixed `Issue 63 <https://github.com/sphinx-contrib/matlabdomain/issues/63>`_.
  Finally, documents can have Python and MATLAB sources auto-documented
  together. Before, the MATLAB autodoc directives shadowed the Python
  directives, making it impossible for them to co-exist. The MATLAB modules now
  have their own module index generated.


0.9.0 (2019-05-29)
------------------

* Merge `PR #92 <https://github.com/sphinx-contrib/matlabdomain/pull/92>`_
  Fix autodoc parsing error when source matlab file is not encoded as UTF-8.
  This adds the option ``matlab_src_encoding``, where one can define a different
  source file encoding. Default is to use utf-8, where unknown characters are
  replaced with �. This fixes a long time issue with the parser failing with
  non utf-8 files.


0.8.0 (2019-05-11)
------------------

* Fixed `Issue 91 <https://github.com/sphinx-contrib/matlabdomain/issues/91>`_.
  Static methods in folder based classes.
* Replaced Pygments MATLAB lexer with own. Removes issues with functions being
  incorrectly parsed, handles double quoted string correctly.


0.7.1 (2019-04-03)
------------------

* Fixed `Issue 90 <https://github.com/sphinx-contrib/matlabdomain/issues/90>`_.
  Wrong function name parsed when method escapes first argument with ~.


0.7.0 (2019-03-29)
------------------
* Support for Sphinx >=2.0.0. Fixes
  `Issue 89 <https://github.com/sphinx-contrib/matlabdomain/issues/84>`_.


0.6.0 (2019-03-29)
------------------
* Limit to Sphinx <2.0.0 as a temporary fix, until support for Sphinx 2.0.0 is fixed.


0.5.0 (2019-02-02)
------------------

* Fixed `Issue 84 <https://github.com/sphinx-contrib/matlabdomain/issues/84>`_.
  Undocumented members are always included regardless of :undoc-members:.
* Fixed `Issue 85 <https://github.com/sphinx-contrib/matlabdomain/issues/65>`_.
  Matlab parsing "seems" to hang if code contains a bunch of "%" consecutively.
  Thanks to GulyasGergelyR for reporting and providing a much better solution.
* Fixed `Issue 86 <https://github.com/sphinx-contrib/matlabdomain/issues/86>`_.
  Handles the ``DeprecationWarning: `formatargspec` is deprecated since Python
  3.5. Use `signature` and the `Signature` object directly.``
* Fixed `Issue 87 <https://github.com/sphinx-contrib/matlabdomain/issues/87>`_.
  Strings in double quotes are not parsed correctly by pygments.
* Closed `Issue 82 <https://github.com/sphinx-contrib/matlabdomain/issues/82>`_.
  Instead of renaming getter and setter functions to `get_whatever`, they are
  not documented anymore. This is in line with MATLAB documentation
  https://se.mathworks.com/help/matlab/matlab_oop/property-access-methods.html,
  as these functions cannot be called directly.


0.4.0 (2018-10-05)
------------------

* Fixed `Issue 69 <https://github.com/sphinx-contrib/matlabdomain/issues/69>`_.
  Autodoc for script header. Thanks to Hugo Leblanc for this contribution.


0.3.5 (2018-09-28)
------------------

* Fixed `Issue 79 <https://github.com/sphinx-contrib/matlabdomain/issues/79>`_.
  Enumerations and events cause premature end of m-file parsing.


0.3.4 (2018-09-13)
------------------

* Adapt to Sphinx 1.8.


0.3.3 (2018-07-13)
------------------

* Fixed bug where a line continuation (...) in a string could cause the parser
  to fail.

* Fixed bug introduced in 0.3.2. The word 'function' was also replaced in
  docstrings.


0.3.2 (2018-07-12)
------------------

* Fixed bug where a MATLAB class method containing a variable starting with
  'function' would cause the parser to fail.


0.3.1 (2018-07-12)
------------------

* Fixed bug where a MATLAB script with only comments would cause an error.


0.3.0 (2018-04-10)
------------------

* Fixed `Issue 66 <https://github.com/sphinx-contrib/matlabdomain/issues/66>`_.
  Sphinx 1.7 broke autodoc :members: functionality.
* Changed the requirement to Sphinx >= 1.7.2!


0.2.17 (2018-04-09)
-------------------

* Fixed `Issue 66 <https://github.com/sphinx-contrib/matlabdomain/issues/66>`_.
  Sphinx 1.7 broke autodoc :members: functionality.
* In this release Sphinx is locked to versions below 1.7, the next release will
  require Sphinx > 1.7.
* Added tests of autodoc capabilities.


0.2.16 (2018-03-05)
-------------------

* Fixed `Issue 13 <https://github.com/sphinx-contrib/matlabdomain/issues/13>`_.
  crashes if filename and classname are different.
* Fixed `Issue 19 <https://github.com/sphinx-contrib/matlabdomain/issues/19>`_.
  crashes if classdef docstring is not indented
* Fixed `Issue #41 <https://github.com/sphinx-contrib/matlabdomain/issues/41>`_.
  Problem with non ascii characters.


0.2.15 (2018-02-25)
-------------------

* Fixed `Issue #30 <https://github.com/sphinx-contrib/matlabdomain/issues/30>`_.
  Some definition of attributes for the "properties" or "methods" blocks causes
  Sphinx to crash.
* Fixed `Issue #57 <https://github.com/sphinx-contrib/matlabdomain/issues/57>`_.
  Parser fails while parsing new syntax extensions for the class properties.


0.2.14 (2018-02-23)
-------------------

* Merge `PR #60 <https://github.com/sphinx-contrib/matlabdomain/pull/60>`_
  Dependency fix for Sphinx 1.7.
* Added cleobis to as contributor


0.2.13 (2018-01-12)
-------------------

* Fix bug when parsing a function without output and no parentheses.
* Better error messages during parsing of functions.


0.2.12 (2018-01-10)
-------------------

* Fixed `Issue #27 <https://github.com/sphinx-contrib/matlabdomain/issues/27>`_.
  An "events" block in a class causes Sphinx to hang.
* Fixed `Issue #52 <https://github.com/sphinx-contrib/matlabdomain/issues/52>`_.
  An "enumeration" block in a class causes Sphinx to hang
* Merge `PR #51 <https://github.com/sphinx-contrib/matlabdomain/pull/51>`_
  better exception, when input args contains "..."
* Added Christoph Boeddeker as author.


0.2.11 (2017-11-28)
-------------------

* Fixed `Issue #42 <https://github.com/sphinx-contrib/matlabdomain/issues/42>`_.
  Comment strings after a function docstring are not included in the docstring
  anymore.
* Fixed `Issue #50 <https://github.com/sphinx-contrib/matlabdomain/issues/50>`_.
  Added Lukas Drude as author.


0.2.10 (2017-11-27)
-------------------

* Add Jørgen Cederberg as maintainer.
* Change bitbucket links to github ditto.


0.2.9 (2017-11-23)
------------------

Development migrated to https://github.com/sphinx-contrib/matlabdomain

* Merge `PR #1 <https://github.com/sphinx-contrib/matlabdomain/pull/1>`_


0.2.8 (2016-12-15)
------------------

* merge PR #2 nested functions


0.2.6 (2014-11-10)
------------------

* fix issues #30


0.2.5 (2014-10-02)
------------------

* fix issues #21
* changeset 8f18a8f adds [+@]? to regular expression for matlab signatures
* add Octave to sphinx-contrib README and link to sphinxcontrib-matlabdomain on
  PyPI
* update and include CHANGES in README so they're in PyPI documentation


0.2.4 (2014-02-21)
------------------

* fix issues #17, #18
* vastly simplify regex used to remove ellipsis from function signatures
* save parsed mat_types in modules that are saved in sys.modules, and
  retrieve them instead of re-parsing mfiles every time!


0.2.3 (2014-02-20)
------------------

* fix critical bug in class properties, arrays and expressions with ellipsis
  were incorrectly handled


0.2.2 (2014-01-26)
------------------

* fix ellipsis in function in output arg
* fix bases getter method had no default, so crashing build
* add catchall warning if getter fails and no default in MatObject.getter()
* fix local path used to index sys.module, instead of full path, oops!
* fix left-strip dot if in basedir, root_mod is '', so join yields ".test_data"


0.2.1 (2014-01-24)
------------------

* allow property defaults to span multiple lines, even w/o ellipsis, and ignore
  ellipsis comments
* correct Pygments ellipsis not allowed in function signature error
* allow builtin names to be used as property names
* fix keyword-end counter bugs, add group incrementer counter, incl curly-braces
* fix module has no docstring attr bug in MatModuleAnalyzer
* allow empty property block
* allow no function return or empty input args


0.2 (2014-01-23)
----------------

* add autodoc capabilities for MATLAB domain


0.1 (2013-04-25)
----------------

* create a Sphinx domain for MATLAB
* override standard domain to remove py modules index

.. _`deprecated Sphinx API`: https://www.sphinx-doc.org/en/master/extdev/deprecated.html
