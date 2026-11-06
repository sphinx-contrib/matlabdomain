Configuration values
====================

The values the extension adds to ``conf.py``. :doc:`../user-guide/configuration`
explains how to use them. Unless noted, changing a value makes Sphinx read
every page again.

Every name in ``conf.py`` that starts with ``matlab_`` must be one of the
values below. Any other one (a typo, or a value this version does not have)
is a ``ConfigError`` in the build and in ``sphinx-matlab-apidoc``, which
suggests the closest value. Give helper variables another name, such as
``_matlab_root``.

Source files
------------

.. confval:: matlab_src_code_project_root
   :type: ``str`` or ``None``
   :default: ``None``

   The folder all MATLAB source lives below. Every path reference is
   relative to it. A relative path is relative to the Sphinx source folder.
   ``None`` indexes no files. Required when
   :confval:`matlab_src_include_patterns` differs from its default,
   :confval:`matlab_src_exclusion_patterns` is set to a list other than
   its default or ``[]``, or :confval:`matlab_src_sidecar_suffixes` is set.

.. confval:: matlab_src_include_patterns
   :type: ``list[str]``
   :default: ``["**/*"]``

   Glob patterns, relative to :confval:`matlab_src_code_project_root`, of
   the files to index. A file is indexed if its path reference matches one
   of them; ``[]`` selects no files. Patterns use ``/``, match like
   ``exclude_patterns`` (``**`` crosses folders, ``**/x`` also matches
   ``x``) and are case-sensitive. An absolute pattern, a drive, a ``\``, an
   empty pattern, or ``..`` that leaves the root or follows a wildcard is a
   ``ConfigError``.

.. confval:: matlab_src_exclusion_patterns
   :type: ``list[str]``
   :default: ``["README.*", "CHANGES.*", "CHANGELOG.*", "LICENSE.*", "CONTRIBUTING.*", "CODE_OF_CONDUCT.*", "SECURITY.*"]``

   Glob patterns of files and folders to leave out, with the rules of
   :confval:`matlab_src_include_patterns`. An excluded folder is not
   searched. The default leaves out the project's own files at the root
   (in upper case only), which are neither code nor
   :doc:`sidecar docs <../user-guide/sidecars>`; a list of your own replaces it, so
   copy these patterns into it if you want to keep them.

.. confval:: matlab_src_sidecar_suffixes
   :type: ``list[str]``
   :default: ``[]``

   The suffixes of the sidecar docs: ``".md"`` (needs
   ``myst_parser`` in ``extensions``) and ``".rst"``. ``[]`` indexes no
   sidecar docs. They follow the include and exclusion patterns and are read
   as UTF-8. The root must not be the Sphinx source folder. See
   :doc:`../user-guide/sidecars`. Any other suffix, a missing root or
   ``myst_parser``, or the root equal to the source folder is a
   ``ConfigError``.

.. confval:: matlab_src_encoding
   :type: ``str`` or ``None``
   :default: ``None``

   The Python codec for files without a byte-order mark. ``None`` reads them
   as UTF-8, falling back to the Windows ANSI code page (Windows) or
   ISO-8859-1 (elsewhere) for files that are not valid UTF-8, like MATLAB.
   An unknown or non-text codec is a ``ConfigError``.

.. confval:: matlab_src_cache_text
   :type: ``bool``
   :default: ``True``

   Keep the text read by the index in memory until the file is parsed,
   during one build. ``False`` reads the file again to parse it. Changing it
   reads no page again.

MATLAB semantics
----------------

.. confval:: matlab_version
   :type: ``str``
   :default: ``"R2026a"``

   The MATLAB release the code targets, ``R<year>a`` or ``R<year>b``,
   R2024a or newer (``ConfigError`` otherwise). It selects release-dependent
   naming and callability rules and the default of
   :confval:`matlab_namelengthmax`.

.. confval:: matlab_namelengthmax
   :type: ``int`` or ``None``
   :default: ``None``

   The longest valid MATLAB name, like MATLAB's ``namelengthmax``: ``63``
   or ``2048`` (``ConfigError`` otherwise). ``None`` derives it from
   :confval:`matlab_version`: 2048 from R2025a on, else 63. An explicit
   value always wins.

Output
------

.. confval:: matlab_show_property_default_value
   :type: ``bool``
   :default: ``True``

   Show a property's default value after its name. A default that spans
   lines is shortened to its first and last line. Also shows the
   constructor arguments of an enumeration value (``Red (1, 0, 0)``).

.. confval:: matlab_show_property_specs
   :type: ``bool``
   :default: ``True``

   Show a property's size, class and validators after its name.

.. confval:: matlab_class_signature
   :type: ``bool``
   :default: ``False``

   Show the constructor's arguments in the class signature.

.. confval:: matlab_add_namespace_names
   :type: ``bool``
   :default: ``True``

   Show the namespace before the name in signatures (``shapes.Circle``);
   ``False`` shows the name alone (``Circle``). It replaces Sphinx's
   ``add_module_names``, which the MATLAB domain does not read.

.. confval:: matlab_auto_link
   :type: ``None``, ``"basic"`` or ``"all"``
   :default: ``None``

   Turn names in help text into links. ``"basic"`` (any true value other
   than ``"all"``): the entries of "See also" lines and of the property and
   method lists of class help. ``"all"``: also every documented class and
   function name anywhere in help text. A false value (``None``, ``""``)
   turns it off. See
   :doc:`../user-guide/help-text`.

.. confval:: matlab_external_names
   :type: ``list[str]``
   :default: MATLAB's own names, below

   Regular expressions of names that the project does not document: a
   ``mat`` reference to a matching name that resolves to nothing (in the
   project or through intersphinx) is shown as text, without a "reference
   target not found" warning. Each expression must match the whole name.
   The default:

   .. code-block:: python

      [
          r"handle|dynamicprops",
          r"(matlab|Simulink|event|meta)\..+",
          r"double|single|u?int(8|16|32|64)|logical|char|string|cell|struct",
          r"function_handle|table|timetable|datetime|duration|calendarDuration",
          r"categorical|containers\.Map|dictionary|MException|missing|timeseries",
      ]

   To add the names of another toolbox, extend it:

   .. code-block:: python

      from sphinxcontrib.matlab import DEFAULT_EXTERNAL_NAMES

      matlab_external_names = [*DEFAULT_EXTERNAL_NAMES, r"sltest\..+"]

   ``[]`` turns it off. A value that is not a list of valid regular
   expressions is a ``ConfigError``. Changing it reads no page again.

.. confval:: matlab_stable_urls
   :type: ``bool``
   :default: ``True``

   HTML builds write a stable address for every documented object, which
   redirects to the page the object is on: ``mat/ref/<path
   reference>.html`` and, for a MATLAB name of non-private objects,
   ``mat/name/<MATLAB name>.html`` (a list of the objects when several have
   the name). The "¶" link of an object points to it, and so does its
   entry in ``objects.inv``; ``mat/refs.js``, a script on every page and
   ``404.html`` send an address of a page that no longer has the object to
   it. ``False`` writes no such files and keeps "¶"
   and the inventory on the page (:ref:`library-changes`).

``matlab-api-check``
--------------------

Changing these reads no page again.

.. confval:: matlab_api_check_rules
   :type: ``dict[str, str]``
   :default: ``{}``

   Rule name to severity, ``"error"``, ``"warning"`` or ``"ignore"``,
   merged over the defaults (``"warning"`` for ``property-description``,
   ``event-description``, ``example`` and ``method-example``, ``"error"``
   for the others). Rules: ``description``, ``method-description``,
   ``property-description``, ``event-description``, ``inputs``,
   ``outputs``, ``name-value``, ``example``, ``method-example``,
   ``sidecar-documented``, ``sidecar-links``. A value that is
   not a dictionary, an unknown rule or an unknown severity is a
   ``ConfigError``.

.. confval:: matlab_api_check_enabled
   :type: ``bool``
   :default: ``True``

   ``False`` checks nothing; the reports say so.

.. confval:: matlab_api_check_ignore_patterns
   :type: ``list[str]``
   :default: ``[]``

   Glob patterns, with the rules of
   :confval:`matlab_src_exclusion_patterns`, of objects not to check,
   matched against the path references of files, methods
   (``+pkg/Cls.m.helper``) and sidecar docs.

.. confval:: matlab_api_check_files
   :type: ``None``, ``list[str]`` or ``str``
   :default: ``None``

   The files to check. ``None`` checks every indexed file. A list selects
   the files and sidecar docs whose path references match one of its
   entries: paths or glob patterns, relative to
   :confval:`matlab_src_code_project_root`, with the rules of
   :confval:`matlab_src_include_patterns`; an entry that ends in ``/``
   selects the files below that folder. A file's methods and properties
   are checked with it. ``[]`` selects no file. A string is a list
   separated by commas or line breaks, as ``-D
   matlab_api_check_files=a.m,b.m`` gives it; blank entries are dropped.
   It narrows only the check: the index, the pages and the links stay
   those of the whole project. An entry that selects no file is an error:
   the build exits with status 1 (see
   :confval:`matlab_api_check_ignore_unmatched`). Any other type, or an
   entry that :confval:`matlab_src_include_patterns` would reject, is a
   ``ConfigError``.

.. confval:: matlab_api_check_files_from
   :type: ``str`` or ``None``
   :default: ``None``

   The path of a UTF-8 text file with more entries for
   :confval:`matlab_api_check_files`, one per line, such as a list of
   changed files: ``-D matlab_api_check_files_from=changed-files.txt``. A
   relative path is relative to the current folder. Blank lines and the
   spaces around a line are dropped; commas do not separate entries. Set
   alone, it selects only its lines (none for an empty file). A file that
   cannot be read, or a line that :confval:`matlab_src_include_patterns`
   would reject, is a ``ConfigError``.

.. confval:: matlab_api_check_ignore_unmatched
   :type: ``bool``
   :default: ``False``

   ``True`` (``-D matlab_api_check_ignore_unmatched=1``): a selection entry
   that selects no file (a deleted file, a file that is not MATLAB code or
   is excluded) is listed in the reports as ``ignored``, without an error
   or exit status 1.

.. confval:: matlab_api_check_section_labels
   :type: ``dict[str, list[str]]``
   :default: ``{}``

   Section to the labels it accepts, replacing its built-in labels (see
   :doc:`../user-guide/api-check`); a section left out keeps them.
   Sections: ``inputs``, ``outputs``, ``name-value``, ``example``. A label
   is text without ``:``, matched in any case, with any spaces between its
   words. The entry ``"<built-in>"`` stands for the built-in labels, so
   ``["<built-in>", "Eingaben"]`` extends them. ``[]`` accepts no label. A
   value that is not a dictionary of lists, an unknown section or a label
   that is not text is a ``ConfigError``.

``sphinx-matlab-apidoc``
------------------------

Read by ``sphinx-matlab-apidoc`` (:doc:`cli`); the build ignores them,
so changing them reads no page again. No flag overrides them. Paths are
relative to the folder of ``conf.py``.

.. confval:: matlab_apidoc_output_dir
   :type: ``str`` or ``None``
   :default: ``None``

   The folder for the generated pages. Required.

.. confval:: matlab_apidoc_group
   :type: ``str``
   :default: ``"namespace"``

   How pages are grouped: ``"namespace"``, one page per namespace (all its
   folders) plus Global for the files outside any namespace; or
   ``"folder"``, one page per folder with files. Both list their pages flat
   on the root page (:doc:`../user-guide/apidoc`). Any other value is a
   ``ConfigError``.

.. confval:: matlab_apidoc_page_size
   :type: ``int``
   :default: ``100``

   The most entries (files and sidecar docs) on one namespace or folder
   page; a longer one gets several pages. Less than 1 is a
   ``ConfigError``. Which page an entry is on, and so its address, can
   change when files are added or removed; anchors and inventory names do
   not (:ref:`library-changes`).

.. confval:: matlab_apidoc_private
   :type: ``bool`` or ``None``
   :default: ``None``

   List the files of ``private/`` folders. ``None``: namespace grouping
   leaves them out, folder grouping lists them; ``True`` lists them in both
   (in namespace grouping, with the folder above); ``False`` leaves them
   out of both. Sidecar docs in ``private/`` are listed either way.

.. confval:: matlab_apidoc_separate
   :type: ``bool``
   :default: ``False``

   One page per file; namespace and folder pages list them in toctrees.
   A file's page is named by its path, so its address does not depend on
   :confval:`matlab_apidoc_page_size`.

.. confval:: matlab_apidoc_maxdepth
   :type: ``int``
   :default: ``4``

   The ``:maxdepth:`` of the generated toctrees.

.. confval:: matlab_apidoc_tocfile
   :type: ``str``
   :default: ``"index"``

   The name of the root page, without suffix.

.. confval:: matlab_apidoc_suffix
   :type: ``str``
   :default: ``"rst"``

   The suffix of the generated files, with or without the dot.

.. confval:: matlab_apidoc_templatedir
   :type: ``str`` or ``None``
   :default: ``None``

   A folder with templates that replace the defaults (:doc:`templates`).

.. confval:: matlab_apidoc_remove_old
   :type: ``bool``
   :default: ``True``

   Delete generated pages that are no longer pages, so the output stays
   accurate. Only files that start with the marker line are deleted.

Removed
-------

Setting one of these is a ``ConfigError`` that names the replacement
(:doc:`../user-guide/migration`).

.. confval:: matlab_src_dir
   :type: removed
   :default: ``None``

   Use :confval:`matlab_src_code_project_root` (relative to the Sphinx
   source folder) and, to select files,
   :confval:`matlab_src_include_patterns` and
   :confval:`matlab_src_exclusion_patterns`.

.. confval:: matlab_keep_package_prefix
   :type: removed
   :default: ``None``

   Objects are referenced by path (which keeps the ``+``); signatures show
   MATLAB names (without it).

.. confval:: matlab_short_links
   :type: removed
   :default: ``None``

   Signatures show MATLAB names.

Sphinx and autodoc values
-------------------------

The auto directives also read these values of Sphinx and
``sphinx.ext.autodoc`` (see their documentation):
``autoclass_content``, ``autodoc_docstring_signature``,
``autodoc_member_order``, ``autodoc_default_options``,
``add_function_parentheses`` and ``primary_domain``.
