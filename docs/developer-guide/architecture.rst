Architecture
============

How the extension fits into Sphinx, for contributors. The modules are in
``sphinxcontrib/``.

Modules
-------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Module
     - Role
   * - ``matlab.py``
     - ``setup()``: configuration values, events, the builder, the auto
       directives. ``MATLABDomain``: directives, roles, cross-reference
       resolution, the folder index and the domain data.
   * - ``mat_types.py``
     - The index stage (``IndexSettings``, ``build_index``, ``SourceIndex``,
       ``analyze``), the lazy parse (``resolve``), incremental-build hooks,
       and the object model (``MatObject`` and subclasses).
   * - ``mat_naming.py``
     - Path references, anchors, MATLAB names (``form_matlab_name``, a port
       of MATLAB's own naming rules) and the release-dependent rules
       (``MATLAB_VERSION_RULES``).
   * - ``mat_classify.py``
     - ``classify()`` (script, function, class or unknown, from the first
       line of code), ``decode_source()`` (encodings as MATLAB reads them),
       the special files.
   * - ``mat_handlers.py``
     - The file-type registry: one handler per extension (``.m``,
       ``.mlapp``).
   * - ``mat_tree_sitter_parser.py``
     - tree-sitter queries: signatures, members, arguments and help text.
   * - ``mat_documenters.py``, ``mat_directives.py``
     - The autodoc documenters behind ``mat:auto*``.
   * - ``mat_api_check.py``
     - The ``matlab-api-check`` builder.
   * - ``matlab_apidoc/``
     - ``sphinx-matlab-apidoc``: the command line, the page model, output
       names and the templates.

Two stages: index, then parse on demand
---------------------------------------

Reading and classifying text is cheap; tree-sitter parses are not.

1. **Index** (``analyze`` on ``builder-inited``): ``build_index`` walks the
   project root once (include and exclude patterns, links, hidden folders),
   reads each file through its handler, decodes and classifies it, and names
   every file and folder. An index record, keyed by source path, holds the
   reference, type, modification time, size, warnings, MATLAB name,
   ``private`` and the folder the name is visible from. A record whose time
   and size did not change is reused without reading the file.
2. **Parse** (``resolve``): a file is parsed when a documenter, a lookup
   that needs members, or an auto-link asks for it, and cached in
   ``parse_cache`` by ``(path, mtime, size)``. A class folder is parsed as
   one unit. Lookups decide from the index records whenever they can.

``build_index`` needs no Sphinx application, so ``sphinx-matlab-apidoc``
shares the index stage: it agrees with the build on files, references,
types, names and warnings, and never parses.

State and Sphinx's lifecycle
----------------------------

All state that outlives a build is in the domain's data
(``env.domaindata["mat"]``), which Sphinx pickles:

* per page: ``objects`` (documented objects), ``folders`` and
  ``doc_sources`` (the source files each page used, with time and size);
* rebuilt by each index stage: ``index``, ``entities_table`` (path
  reference to object), ``matlab_names`` (MATLAB name to references);
* caches: ``parse_cache`` and ``parse_warnings``, pruned to files still in
  the index.

tree-sitter objects are never pickled (``MatObject.__reduce_ex__``). The
decoded text of the index stage stays in memory for the parse
(``text_cache``, not pickled). ``data_version`` is bumped whenever this
layout or the cached objects change.

The events ``setup()`` connects:

* ``config-inited``: ``ensure_configuration`` (removed values, patterns,
  version), ``check_encoding``, ``mat_api_check.check_config``;
* ``builder-inited``: ``analyze``, the index stage;
* ``env-get-outdated``: ``outdated_docs``, the pages to read again because
  a source file they used changed, or because files were added, removed or
  changed type;
* ``env-before-read-docs``: ``note_read_docs``;
* ``env-updated``: ``warn_parsed_sources``, the parse-stage warnings;
* ``build-finished``: ``mat_api_check.set_status``, the exit status.

Sphinx calls the domain's ``clear_doc`` and ``merge_domaindata``. Parallel
reads parse in the worker processes; ``merge_domaindata`` keeps their
parses when the file is still current.

Names and references
--------------------

``mat_naming.py`` is the only place that turns paths into references,
anchors and MATLAB names, so directives, documenters, roles,
``sphinx-matlab-apidoc`` and ``matlab-api-check`` agree. The reference
scheme and the anchors are a public contract
(:doc:`../user-guide/referencing`). Cross-reference resolution is
``MATLABDomain.find_obj``: exact reference, then relative to the current
folder, then a unique MATLAB name, then a folder path.

The file-type registry
----------------------

A handler (``mat_handlers.Handler``) owns one extension and provides:
``discover`` (is the file of this type), ``classify`` (its index type),
``read`` (index stage: type, decoded text, warnings), ``parse`` (the parsed
object) and ``document`` (the auto directive for a type). ``register`` adds
a handler; registration order is lookup order. A new file type is a new
handler, not a change to the index or the domain (:doc:`roadmap`).

Fault tolerance
---------------

Reading, classifying, parsing and help extraction run per file inside
``try``/``except``. A failure gives one warning (``mat.parse_error`` and
others, :doc:`../user-guide/warnings`) and a placeholder object of the
file's type, so references still resolve. Content failures are cached like
successes; read failures are retried on the next build.

The shift from 0.x
------------------

Version 0.x mirrored Python: dotted module names, a module per folder, and
every file parsed when the build started. This version names objects as
MATLAB does (from the folder layout, ported from a MATLAB reference
implementation that was checked against MATLAB on 66,000 files), indexes
cheaply up front, and lets Sphinx's events pull parses only when needed.
