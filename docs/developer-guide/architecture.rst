Architecture
============

How the :term:`extension` fits into Sphinx, for contributors. The modules are in
``sphinxcontrib/``.

Modules
-------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Module
     - Role
   * - ``matlab.py``
     - ``setup()``: configuration values, events, the :term:`builder`, the
       auto :term:`directives <directive>`. ``MATLABDomain``: directives,
       :term:`roles <role>`, :term:`cross-reference` resolution, the folder
       index and the :term:`domain` data.
   * - ``mat_types.py``
     - The index stage (``IndexSettings``, ``build_index``, ``SourceIndex``,
       ``analyze``), the lazy parse (``resolve``), incremental-build hooks,
       and the object model (``MatObject`` and subclasses).
   * - ``mat_naming.py``
     - Path references, anchors, MATLAB names (``form_matlab_name``, a port
       of MATLAB's own naming rules; ``form_model_name`` for Simulink
       files) and the release-dependent rules (``MATLAB_VERSION_RULES``).
   * - ``mat_classify.py``
     - ``classify()`` (script, function, class or unknown, from the first
       line of code), ``decode_source()`` (encodings as MATLAB reads them),
       the special files.
   * - ``mat_handlers.py``
     - The file-type registry: one handler per extension (``.m``,
       ``.mlapp``, ``.slx``, ``.mdl``, exported Simulink ``.xml``).
   * - ``mat_simulink/``
     - The Simulink file reader: layouts, limits, parsers and the
       format-neutral content (see :doc:`simulink-file-formats`).
   * - ``mat_tree_sitter_parser.py``
     - tree-sitter queries: :term:`signatures <signature>`, members,
       arguments and help text.
   * - ``mat_documenters.py``, ``mat_directives.py``
     - The autodoc documenters behind ``mat:auto*``.
   * - ``mat_api_check.py``
     - The ``matlab-api-check`` builder.
   * - ``mat_sidecars.py``
     - Sidecar docs: the configuration check, ``mat:autosidecar``, the
       myst-parser renderer for Markdown sidecar docs and the link mapping.
   * - ``matlab_cli.py``
     - ``scmd``: the command and its subcommands.
   * - ``matlab_skills/``
     - ``scmd skills`` and the agent skills it copies, one folder with a
       ``SKILL.md`` each.
   * - ``matlab_apidoc/``
     - ``scmd apidoc``: the command line, the page model, output
       names and the templates.
   * - ``matlab_quickstart/``
     - ``scmd quickstart``: the project facts (``_detect.py``), the
       Sphinx :term:`source folder <source directory>` from its templates
       and the edits outside it
       (``_write.py``), the prompts and answers file (``_cli.py``), the
       report (``_report.py``). It builds the index and calls the
       generator of ``matlab_apidoc/``.

The main imports between the modules (an arrow points to the module that
is imported). Most modules also use ``mat_naming.py`` and
``mat_classify.py`` directly; those arrows are left out.

.. mermaid::

   flowchart TB
     sphinx(["sphinx-build"]) --> matlab
     scmd(["scmd"]) --> cli["matlab_cli.py"]
     cli --> apidoc
     cli --> quickstart["matlab_quickstart/"]
     cli --> skills["matlab_skills/"]
     quickstart --> apidoc
     matlab["matlab.py<br/>setup, MATLABDomain"] --> documenters["mat_documenters.py<br/>mat_directives.py"]
     matlab --> apicheck["mat_api_check.py"]
     matlab --> sidecars["mat_sidecars.py<br/>sidecar docs"]
     documenters --> types
     apicheck --> types
     sidecars --> types
     apidoc["matlab_apidoc/"] --> types
     types["mat_types.py<br/>index, parse, objects"] --> naming["mat_naming.py<br/>references, MATLAB names"]
     types --> parser["mat_tree_sitter_parser.py"]
     naming --> handlers["mat_handlers.py<br/>file types"]
     handlers --> classify["mat_classify.py<br/>file kind, decoding"]
     handlers --> simulink["mat_simulink/<br/>Simulink files"]
     handlers -. "when parsing" .-> types
     parser --> treesitter[("tree-sitter-matlab")]

``mat_handlers.py`` imports ``mat_types`` inside its functions (dotted
arrow), which breaks the import cycle.

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

``build_index`` needs no Sphinx application, so ``scmd apidoc``
shares the index stage: it agrees with the build on files, references,
types, names and warnings, and never parses.

Sidecar docs (:doc:`../user-guide/sidecars`) are found by the same walk
but kept apart: ``SourceIndex.sidecars`` records their reference, time and
size, without reading them. They are no members of their folder and have
no MATLAB name, so they never shadow code. ``mat:autosidecar`` reads one when
a document renders it and notes it as a dependency of that document.

State and Sphinx's lifecycle
----------------------------

All state that outlives a build is in the domain's data
(``env.domaindata["mat"]``), which Sphinx pickles:

* per page: ``objects`` (documented objects), ``folders``,
  ``doc_sources`` (the source files each page used, with time and size),
  ``sidecar_docs`` (the sidecar docs it renders) and ``sidecar_issues``
  (their broken links and missing images, for ``matlab-api-check``);
* rebuilt by each index stage: ``index``, ``sidecars``, ``entities_table``
  (path reference to object), ``matlab_names`` (MATLAB name to
  references);
* caches: ``parse_cache`` and ``parse_warnings``, pruned to files still in
  the index.

tree-sitter objects are never pickled (``MatObject.__reduce_ex__``). The
decoded text of the index stage stays in memory for the parse
(``text_cache``, not pickled). ``data_version`` is bumped whenever this
layout or the cached objects change.

The events ``setup()`` connects:

* ``config-inited``: ``ensure_configuration`` (removed values, patterns,
  version), ``check_encoding``, ``mat_sidecars.check_config`` (sidecar
  suffixes;
  with the root inside the source folder, the sidecar docs are added to
  ``exclude_patterns`` here, because a later change would make Sphinx
  read every page again on every build), ``mat_api_check.check_config``;
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
``scmd apidoc`` and ``matlab-api-check`` agree. The reference
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
