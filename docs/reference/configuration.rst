Configuration values
====================

The values the extension adds to ``conf.py``. :doc:`../user-guide/configuration`
explains how to use them. Unless noted, changing a value makes Sphinx read
every page again.

Source files
------------

.. confval:: matlab_src_code_project_root
   :type: ``str`` or ``None``
   :default: ``None``

   The folder all MATLAB source lives below. Every path reference is
   relative to it. A relative path is relative to the Sphinx source folder.
   ``None`` indexes no files. Required when
   :confval:`matlab_src_include_patterns` differs from its default or
   :confval:`matlab_src_exclusion_patterns` is set.

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
   :default: ``[]``

   Glob patterns of files and folders to leave out, with the rules of
   :confval:`matlab_src_include_patterns`. An excluded folder is not
   searched.

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
   R2025a or newer (``ConfigError`` otherwise). It selects release-dependent
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
   :default: ``False``

   Show a property's default value after its name. A default that spans
   lines is shortened to its first and last line.

.. confval:: matlab_show_property_specs
   :type: ``bool``
   :default: ``False``

   Show a property's size, class and validators after its name.

.. confval:: matlab_class_signature
   :type: ``bool``
   :default: ``False``

   Show the constructor's arguments in the class signature.

.. confval:: matlab_auto_link
   :type: ``None``, ``"basic"`` or ``"all"``
   :default: ``None``

   Turn names in help text into links. ``"basic"`` (any true value other
   than ``"all"``): the entries of "See also" lines and of the property and
   method lists of class help. ``"all"``: also every documented class and
   function name anywhere in help text. See
   :doc:`../user-guide/help-text`.

``matlab-api-check``
--------------------

Changing these reads no page again.

.. confval:: matlab_api_check_rules
   :type: ``dict[str, str]``
   :default: ``{}``

   Rule name to severity, ``"error"``, ``"warning"`` or ``"ignore"``,
   merged over the defaults (every rule ``"error"``). Rules:
   ``description``, ``method-description``, ``inputs``, ``outputs``,
   ``name-value``. A value that is not a dictionary, an unknown rule or an
   unknown severity is a ``ConfigError``.

.. confval:: matlab_api_check_enabled
   :type: ``bool``
   :default: ``True``

   ``False`` checks nothing; the reports say so.

.. confval:: matlab_api_check_ignore_patterns
   :type: ``list[str]``
   :default: ``[]``

   Glob patterns, with the rules of
   :confval:`matlab_src_exclusion_patterns`, of objects not to check,
   matched against the path references of files and methods
   (``+pkg/Cls.m.helper``).

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
``add_function_parentheses``, ``add_module_names`` and ``primary_domain``.
