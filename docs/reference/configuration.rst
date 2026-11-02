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
   :default: ``True``

   Show a property's default value after its name. A default that spans
   lines is shortened to its first and last line.

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
   ``name-value``, ``sidecar-documented``, ``sidecar-links``. A value that is
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

``sphinx-matlab-apidoc``
------------------------

Read by ``sphinx-matlab-apidoc`` (:doc:`cli`); the build ignores them,
so changing them reads no page again. No flag overrides them. Paths are
relative to the folder of ``conf.py``. The toctree depth (4), the name of
the root page (``index``), the suffix (``.rst``) and the removal of stale
pages are fixed; ``matlab_apidoc_maxdepth``, ``matlab_apidoc_tocfile``,
``matlab_apidoc_suffix`` and ``matlab_apidoc_remove_old`` are errors
(:ref:`apidoc-write-your-own` sets them from a script).

.. confval:: matlab_apidoc_output_dir
   :type: ``str`` or ``None``
   :default: ``None``

   The folder for the generated pages. Required.

.. confval:: matlab_apidoc_separate
   :type: ``bool``
   :default: ``False``

   One page per file; folder pages list them in toctrees.

.. confval:: matlab_apidoc_templatedir
   :type: ``str`` or ``None``
   :default: ``None``

   A folder with templates that replace the defaults (:doc:`templates`).

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
