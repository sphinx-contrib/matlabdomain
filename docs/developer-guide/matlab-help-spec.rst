Specification: a Sphinx site in the MATLAB help system
======================================================

Status: investigated, not scheduled (:doc:`roadmap`).

Question: can a ``sphinxcontrib-matlabdomain`` site become part of the
MATLAB documentation, so that one search in MATLAB finds both the
project's pages and MathWorks pages? Can sites link to each other the way
intersphinx links Sphinx projects? Plan: :doc:`matlab-help-plan`.

Evidence (2026-11-07):

- MathWorks R2026b pages: "Display Custom Documentation",
  "Display Custom Examples", ``builddocsearchdb``, ``doc``, "Interactively
  Create and Share Packages", ``matlab.addons.toolbox.ToolboxOptions``.
- R2026b source read in ``toolbox/matlab/helptools/+matlab/+internal/+doc``
  (``+project``, ``+search``, ``+services``, ``+url``, ``+reference``) and
  the page wrapper in ``help/customdoc/`` (``3pdoc.html``,
  ``customdoc.js``, ``customdoc_base.js``). Strings from the indexer binary
  ``bin/win64/mwdocsearch.exe`` (version 8.1.3 in R2026b, 6.2.9 in
  R2026a).
- Probe: the HTML build of this project's documentation plus a
  hand-written ``info.xml`` and ``helptoc.xml``, put on the path of R2026b
  and R2026a sessions, indexed, served and searched through the local doc
  server; synthetic pages to learn what the indexer reads. The probe
  scripts are not in the repository yet (plan task H9).
- Prior art: ``ilent2/sphinx-matlabdoc-builder`` (2019, BSD-2-Clause), read
  in full.

Labels used below: **verified** (probe ran), **source** (read in the
R2026b MATLAB code, not run), **documented** (MathWorks page only).

1. Short answer
---------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Question
     - Answer
   * - The site shows inside the MATLAB documentation
     - **Yes, cheap.** "Supplemental Software" custom documentation: an
       ``info.xml`` on the MATLAB path, a ``helptoc.xml`` and HTML files.
       A Sphinx HTML build displays with its CSS and JavaScript (verified,
       R2026a and R2026b).
   * - The site is searchable from MATLAB
     - **Yes, with** ``builddocsearchdb``. Results appear on a local
       "Supplemental Software" results page (verified, R2026a).
   * - One search returns the site's pages and MathWorks pages together
     - **No.** MATLAB keeps two result sets, MathWorks (``mw``) and
       Supplemental Software (``3p``). Each results page links to the
       other source; there is no merged, ranked list (source:
       ``searchresults.js``, ``DocPage.addSearchParam``). Not reachable
       from a third-party site: out of scope.
   * - ``doc myfunction`` or F1 opens the site's page
     - **No.** ``doc`` never shows third-party HTML for a function name;
       it renders the file's help text (documented).
       ``doc "<toolbox name>"`` opens the landing page (source), and
       ``helpview("<path to page.html>")`` opens any page of the site
       (verified URL).
   * - MathWorks pages link to the site
     - **No.** MathWorks content has no hook for third-party targets.
       Out of scope.
   * - The site links to MathWorks pages (like intersphinx)
     - **Yes, built by this project.** MathWorks publishes no
       ``objects.inv`` (verified 404). MATLAB installs a reference catalog
       (``help/docCatalog/referenceapi/*.json``: 78 products, 31,883
       entries in R2026b) from which a build can make one (Section 6).
   * - The site links to another custom site in MATLAB help
     - **Yes, by relative links.** All custom sites are served under one
       root, at a path computed from the ``info.xml`` name (Section 2.2).
   * - MATLAB Online
     - **No.** Custom documentation and ``builddocsearchdb`` are not
       supported there (documented).

Merged search is not possible and is out of scope. Embedding the site,
with its own search on the MATLAB side, takes a small builder plus a
MATLAB step (:doc:`matlab-help-plan`).

2. How MATLAB custom documentation works
----------------------------------------

2.1 Discovery
~~~~~~~~~~~~~

- MATLAB looks for ``info.xml`` and ``demos.xml`` on the path
  (``matlab.internal.doc.project.getFiles``) and rebuilds its list when
  the set of files changes (``getCustomToolboxes``, source). Adding the
  folder that holds ``info.xml`` was enough in the probe; the HTML folder
  itself was not on the path (verified). The MathWorks page asks for the
  HTML folder on the path too (documented); not needed by the code read.
- ``info.xml`` elements, in this order: ``matlabrelease`` (not used),
  ``name``, ``type``, ``icon`` (empty, required), ``help_location`` (folder
  with ``helptoc.xml``, relative to ``info.xml``), optional
  ``help_contents_icon``. Schema:
  ``matlabroot/sys/namespace/info/v1/info.xsd``. MATLAB reads it with
  ``readstruct``; only ``name`` and ``help_location`` are required by the
  code (source).
- ``helptoc.xml``: ``<toc version="2.0">`` with nested
  ``<tocitem target="page.html">Title``. The first ``tocitem`` is the
  landing page. Targets may carry anchors (``page.html#id``) and an
  ``image`` attribute (``HelpIcon.FUNCTION``, ``USER_GUIDE``,
  ``EXAMPLES``, ``BLOCK``, ``GETTING_STARTED``, ``DEMOS``,
  ``RELEASE_NOTES``), from MATLAB's template
  ``help/techdoc/matlab_env/examples/templates/helptoc_template.xml``.
  Without ``helptoc.xml`` the site is dropped silently (source; warnings
  only with the debug switch ``setDebugProjectDoc``).
- Display name: ``name``, plus " Toolbox" when ``type`` is ``toolbox``,
  plus " Blockset" when it is ``blockset`` (source). The MathWorks pages
  list the allowed types as ``matlab``, ``package``, ``simulink``,
  ``blockset``, ``links_targets``, ``other`` (R2026b renamed toolboxes to
  packages).

2.2 Serving and URLs
~~~~~~~~~~~~~~~~~~~~

- Short name: ``lower(regexprep(displayName,'\W','_'))``; unique id
  ``3ptoolbox::<shortName>``; URL path
  ``3ptoolbox/<shortName without underscores>/doc/`` (source,
  ``buildToolboxStruct.m``). The path must be alphanumeric after that, or
  the site is dropped. Example: "Sphinx Probe Docs" →
  ``3ptoolbox/sphinxprobedocs/doc/`` (verified).
- Two servers, same layout below ``.../help/``: the MATLAB connector
  (``https://127.0.0.1:<port>/help/3ptoolbox/...``, route added by
  ``connector.addStaticContentOnPath``) and the search server
  ``mwdocsearch`` (``http://127.0.0.1:<port>/static/help/3ptoolbox/...``)
  when the system browser is used without the connector (R2024b and
  later default; source ``InstalledDocHandler``). Relative links between
  two custom sites work in both, as both live under ``3ptoolbox/``.
- Each page is shown inside MATLAB's wrapper
  (``help/customdoc/3pdoc.html``): a header with a search box, the
  ``helptoc.xml`` tree on the left, and the page in a same-origin
  ``iframe`` with id ``doc_center_content`` (source, verified visually).
  The wrapper:

  - sets the iframe height to the page's ``body.scrollHeight``
    (``updateContentSize``), so the page should not scroll itself;
  - rewrites links once, when the page loads: same-host links get
    ``target="_parent"``, other hosts ``target="_blank"``, ``#fragment``
    links scroll inside the iframe, ``matlab:`` links run after a
    confirmation dialog (``showMatlabDialog``);
  - scrolls to the URL fragment after 300 ms.

- A page that navigates itself with JavaScript (``location.replace``)
  loads a second wrapper inside the iframe: verified with a stable address
  page (``mat/ref/...``, :confval:`matlab_stable_urls`), which showed the
  wrapper twice. Links that JavaScript adds after load (Sphinx
  ``search.html`` results) are not rewritten and do the same (source).
- ``doc "<display name>"``, ``doc <shortName>`` or the unique id opens the
  landing page (``getReferencePage`` → ``checkForProductOrToolbox`` →
  ``CustomDocPage``; source). ``helpview(<absolute path of an html
  file>)`` maps the file to its served URL (``parseDocPage``; verified
  URL). Both ``CustomDocPage`` and the local search pages support only
  the ``INSTALLED`` doc location, served locally, also when MathWorks
  pages come from the web (source).

2.3 Search index
~~~~~~~~~~~~~~~~

- ``builddocsearchdb(folder)`` writes ``custom_toolbox.json`` into the
  HTML folder, then runs ``mwdocsearch customdocindex -d <folder>``
  (source, ``+customdocindexer/index.m``). The result is a Bleve "scorch"
  index in ``helpsearch-v4_<lang>/`` (``index_meta.json``, ``root.bolt``,
  ``*.zap``; verified). R2021b and older write ``helpsearch-v3``; ship
  both to cover both (documented).
- The crawl root is ``LocationOnDisk`` in ``custom_toolbox.json``, not the
  ``-d`` folder (verified: a staging copy indexed the original folder
  until the JSON was rewritten).
- What the custom indexer stores per ``*.html`` file (verified with
  ``customdocindex -o json`` and searches):

  - every ``.html`` below the root, at any depth, ``_static/`` included;
  - ``title`` from ``<title>``; ``body`` = all text of ``<body>``:
    sidebars, navigation and footers included;
  - nothing else: ``summary``, ``description``, ``infotype``,
    ``breadcrumb`` stay empty. ``<meta name="description">``,
    ``<meta name="infotype">``, ``<meta name="refentity">``,
    ``<meta name="robots" content="noindex">`` and a
    ``<section id="doc_center_content">`` wrapper are ignored. (The binary
    holds those XPaths for MathWorks product indexing, not for custom
    docs.)
  - redirect stubs and pages with an empty body are indexed (the MathWorks
    page says untitled pages and pages whose text equals the title are
    skipped; not so in R2026b).

- Hence: no "Refine by Type" facets (functions, classes), no snippet
  under a result, and one hit per page (no anchor-level hits). Relevance
  rests on page titles and page text only.
- **Excluding pages works by staging**: copy the HTML without the pages
  to drop, point ``custom_toolbox.json`` at the copy, index it, move
  ``helpsearch-v4_en`` into the real folder. Stored paths are relative.
  Verified end to end (R2026a served the filtered index: stubs,
  ``genindex.html`` and ``_static`` gone from the results).
- Cross-release reading (verified): an index written by R2026b was
  searched by the R2024a and R2026a ``mwdocsearch search`` command and
  served by R2026a MATLAB. The MathWorks page says a database matches the
  release that built it; v4 has held since R2022a.
- ``mwdocsearch`` is a standalone executable with ``customdocindex``,
  ``search``, ``server`` and ``prodindex`` commands: an index can be built
  without starting MATLAB (no license check seen), but the command line
  is internal and undocumented.

2.4 Search user interface
~~~~~~~~~~~~~~~~~~~~~~~~~

- Web documentation (MathWorks pages from mathworks.com, the default
  when documentation is not installed): when custom docs exist, MATLAB
  adds ``searchPort=<port>`` to the doc URLs it opens (source,
  ``DocPage.addSearchParam``). The mathworks.com results page then shows
  "Search for X in Supplemental Software", which opens
  ``http://127.0.0.1:<port>/static/help/customdoc/searchresults.html``
  (source, ``searchresults.js``: "search is two completely separate
  processes").
- That local page with ``selectedsource=3p`` lists the site's hits with
  "Refine by Product" (one entry per custom site) and an empty "Refine by
  Type"; each hit opens the page in the wrapper (verified, R2026a). The
  search box in the wrapper header asks
  ``/help/search/suggest?...&selectedsource=3p``: an empty reply in
  R2026a; in R2026b the ``mwdocsearch`` process exited during that probe
  and the session's doc search stayed down (observed once; not
  reproduced).
- Installed documentation: one local results page with a source selector
  (``mw`` or ``3p``), still one source at a time (source; documented as
  "Refine by Source"). Not probed (no installed documentation here).

3. A Sphinx HTML build against these rules
------------------------------------------

From the probe of this project's documentation (Furo theme, 176 files):

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Sphinx output
     - Effect in MATLAB help
     - Needed
   * - Theme sidebar with the whole toctree, header, footer
     - Indexed in every page body: every page matches every title word;
       the iframe shows two navigations (theme and ``helptoc.xml``)
     - A help build without sidebars and chrome
   * - Theme layout with its own scrolling (Furo, PyData)
     - Inner scrollbar inside an auto-height iframe
     - A flow layout (the body scrolls)
   * - ``<title>`` = "Page - Project"
     - Every hit ends in the project name
     - Page title only
   * - Stable addresses ``mat/name/``, ``mat/ref/``
       (:confval:`matlab_stable_urls`) and the ``mat/refs.js`` redirector
     - Duplicate hits with the object name; clicking one nests the wrapper
     - Off in the help build; object entries in ``helptoc.xml`` point to
       anchors instead
   * - ``genindex.html``, ``search.html``, ``404.html``,
       ``mat-folderindex.html``
     - Indexed; ``search.html`` result links nest the wrapper
     - Not written, or left out of the index
   * - ``_sources/``, ``_static/``
     - ``_static/*.html`` indexed if any
     - Out of the index
   * - ``+pkg``, ``@Class`` folders below the HTML folder
     - Harmless: the HTML folder need not be on the path (2.1); if it is,
       they sit below it, not on it
     - Keep the HTML folder off the path, or verify
   * - Relative links, anchors, CSS, JavaScript, dark mode
     - Work (verified)
     - \-
   * - Search query ``?searchHighlight=`` on hits
     - Ignored by the site's pages
     - \-

4. Prior art: ``sphinx-matlabdoc-builder``
------------------------------------------

A ``StandaloneHTMLBuilder`` subclass named ``matlabdoc`` (based on
Sphinx's ``htmlhelp`` builder): ``embedded = True`` (no sidebar),
``search = False``, ``add_permalinks = False``, ``copysource = False``;
at ``handle_finish`` it walks the resolved root toctree and writes
``helptoc.xml`` (CHM-style escaping). It writes no ``info.xml``, no
search database, no exclusions, no icons; last change 2019. The approach
fits; the code is small enough to rewrite rather than depend on.

5. Proposed shape
-----------------

A ``matlab-help`` builder in ``sphinxcontrib-matlabdomain`` (next to
``matlab-api-check``, :doc:`../user-guide/api-check`), output:

.. code-block:: text

   _build/matlab-help/
     info.xml                 # name, type, help_location = html
     html/
       helptoc.xml            # from the toctree; object entries with anchors
       index.html ...         # content pages only
       helpsearch-v4_en/      # added by the index step (MATLAB or mwdocsearch)

- Builder: HTML builder with ``embedded``, no search page, no general
  index, no stable addresses or redirector, no source copies, page
  titles without the project suffix, a flow-layout theme (default:
  derived from Sphinx ``basic``; any theme allowed).
- ``helptoc.xml``: global toctree from the root document; optionally one
  entry per documented object (anchor targets) with ``HelpIcon.FUNCTION``
  under API sections.
- Index step: ``builddocsearchdb`` through ``matlab -batch`` (documented
  route) or ``mwdocsearch customdocindex`` (no MATLAB start; internal).
  The builder already leaves out what the index must not see, so no
  staging is needed.
- Packaging: the folder with ``info.xml`` goes on the package path
  (``ToolboxMatlabPath`` or the package task); no install hook exists, so
  the index ships prebuilt.

6. Links to other documentation
-------------------------------

- **To MathWorks**: build an ``objects.inv`` from the local catalog
  ``help/docCatalog/referenceapi/<product>.json`` (``refItems[].href``,
  ``refentity[].name/type`` such as ``function``, ``method``, ``class``,
  ``block``, ``refpurpose``; ``helpLocation`` per product). URL:
  ``https://www.mathworks.com/help/<helpLocation>/<href>`` (or
  ``/help/releases/<R>/...`` for a fixed release). Generate it at build
  time from the user's installation; do not ship MathWorks data. In the
  help build the same targets can be ``matlab:doc <name>`` links instead,
  which open the page for the user's release (behind MATLAB's
  confirmation dialog).
- **To another custom site** (two projects documented with this extension
  installed side by side): intersphinx with a relative base
  ``../../<urlpath>/doc/``, where ``<urlpath>`` follows 2.2 from the other
  site's display name. Needs a check that Sphinx resolves a relative
  intersphinx base per document depth.
- **From MathWorks or from** ``doc`` **or F1 to the site**: no hook
  (Section 1).
- **From help text to the site**: help text may hold
  ``<a href="matlab:helpview(...)">`` links; not planned.

7. Limits and risks
-------------------

- The URL rule, the wrapper, ``searchPort`` and the ``mwdocsearch``
  command line are internal and may change in any release; the
  documented surface is ``info.xml``, ``helptoc.xml``, the HTML folder and
  ``builddocsearchdb``.
- Custom search has no snippets, types or anchor hits; MATLAB's own
  search user interface cannot be extended.
- R2024a and older use the help browser inside MATLAB (the system browser
  since R2024b); not probed.
- One ``mwdocsearch`` exit in R2026b during a suggestion request (2.4).
