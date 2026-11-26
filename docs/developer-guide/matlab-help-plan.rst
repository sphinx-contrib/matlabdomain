Plan: a Sphinx site in the MATLAB help system
=============================================

Status: investigation done (2026-11-07); not scheduled (:doc:`roadmap`).

Spec: :doc:`matlab-help-spec` (mechanics, probe results, limits).

Goal: a ``sphinxcontrib-matlabdomain`` project can produce a build that
MATLAB shows under Supplemental Software, with search on the MATLAB side
and links out to MathWorks pages.

Out of scope (not possible for a third-party site; spec Section 1): one
merged list of MathWorks and custom results, ``doc`` or F1 on a function
opening the site's page, MathWorks pages linking to the site, MATLAB
Online.

Recommendation: low priority. The embedding is cheap and useful for
teams that ship a MATLAB package; one search over both is not reachable,
so the value is "the project's docs in the MATLAB documentation window,
searched separately". Start with H1-H4 and the packaging guide (H7);
H5-H6 when a user project asks for them.

0. Decisions to take first
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 8 32 60

   * - Id
     - Question
     - Proposal
   * - D1
     - Builder or post-processing command?
     - Builder ``matlab-help`` (one ``sphinx-build -b matlab-help``, like
       ``matlab-api-check``).
   * - D2
     - Theme
     - Own minimal flow-layout theme derived from ``basic``, used unless
       ``matlab_help_theme`` names another. Furo and PyData scroll inside
       the iframe (spec Section 3).
   * - D3
     - Index step
     - Documented route first: a MATLAB script or command run by the user
       or CI (``builddocsearchdb``). ``mwdocsearch customdocindex`` as
       opt-in (internal command line).
   * - D4
     - Object entries in ``helptoc.xml``
     - Yes for API pages (anchor targets, ``HelpIcon.FUNCTION``), behind
       an option; toctree only by default.
   * - D5
     - MathWorks links
     - Inventory from the local catalog (spec Section 6), generated, never
       shipped; ``https`` links in web builds, ``matlab:doc`` optional in
       help builds.
   * - D6
     - Oldest release
     - Match the extension's oldest supported MATLAB release
       (:confval:`matlab_version`); v3 index only if that is before
       R2022a.

1. Tasks
--------

.. list-table::
   :header-rows: 1
   :widths: 6 54 40

   * - Id
     - Task
     - Completion check
   * - H1
     - ``matlab-help`` builder: subclass of the HTML builder; writes
       ``info.xml`` (``matlab_help_name`` default ``project``,
       ``matlab_help_type`` default ``package``) and the site into
       ``html/``; ``embedded``, no ``search.html``, no ``genindex``, no
       stable addresses or ``mat/refs.js``, no ``_sources``, titles
       without suffix.
     - Build of ``docs/``: ``info.xml`` validates against ``info.xsd``;
       the folder on the path shows the site under Supplemental Software
       in R2026b; no ``mat/name``, ``mat/ref``, ``genindex`` or
       ``search`` pages.
   * - H2
     - ``helptoc.xml`` from the resolved root toctree (nested, escaped,
       ``/`` separators, case-exact targets); option for object entries
       (D4) and icons per top-level section.
     - Contents tree matches the toctree; anchor entries scroll to the
       object (check in R2026b).
   * - H3
     - Minimal theme (D2): body scroll, no sidebar, no header or footer
       text, MATLAB-like typography.
     - Pages show without inner scrollbars; the ``customdocindex -o json``
       body of a page holds only its own text.
   * - H4
     - Page hygiene: no JavaScript navigation in pages; links in content
       are plain ``<a href>``; check extensions that add pages
       (``sphinx-notfound-page``, ``viewcode``) and drop or exclude them.
     - No nested wrapper when clicking any link or hit; the index lists
       only content pages.
   * - H5
     - Index step (D3): a command or a MATLAB function shipped with the
       package that runs ``builddocsearchdb`` on the build; opt-in
       ``mwdocsearch`` route; CI example (MATLAB GitHub Action).
     - ``helpsearch-v4_en/`` present; a query on the local results page
       (``selectedsource=3p``) returns the expected pages in R2024a,
       R2026a and R2026b.
   * - H6
     - Links out (D5): inventory generator from
       ``help/docCatalog/referenceapi/*.json`` into ``objects.inv`` (domain
       ``mat``, roles for function, class, method, block); relative
       intersphinx between two custom sites.
     - A ``:mat:func:`plot``` in a test project links to the MathWorks
       ``plot`` page; site A links into site B when both are installed.
   * - H7
     - User guide page: packaging a site with a MATLAB package
       (``info.xml`` folder on the package path, prebuilt index per
       release family, what search can and cannot do, MATLAB Online).
       Quickstart option later.
     - The guide page builds; a sample ``.mltbx`` installs and shows the
       docs.
   * - H8
     - Release and mode matrix: R2024a (help browser inside MATLAB),
       R2024b and later (system browser), web and installed documentation,
       Windows and Linux.
     - Table in the spec filled; known gaps listed in the guide.
   * - H9
     - Tests: builder output (files present or absent, ``helptoc.xml``
       shape, ``info.xml`` order) without MATLAB; MATLAB-dependent checks
       in ``test_slow/``, starting from the probe scripts (2).
     - The fast ``pytest`` suite passes; the slow suite runs where MATLAB
       exists.

2. Open checks
--------------

Probe before the task that needs them:

- Anchor targets in ``helptoc.xml`` and the 300 ms fragment scroll (H2).
- Sphinx relative intersphinx bases across document depths (H6).
- ``doc "<display name>"`` opening the landing page, end to end (H7
  text).
- The R2026b ``mwdocsearch`` exit on a suggestion request: reproduce; if
  real, report it to MathWorks and note it in the guide (H8).
- Whether the HTML folder must be on the path in any release (spec 2.1).
- Effect of one large page versus one page per object on relevance (H4;
  ties to the page layout of ``scmd apidoc``).

3. Probes
---------

The probe scripts are not in the repository yet; H9 moves them into
``test_slow/``. They cover:

- the indexer: synthetic pages, ``customdocindex -o json``, searches
  (what the indexer reads);
- releases: an R2026b index searched by the R2024a, R2026a and R2026b
  ``mwdocsearch``;
- exclusion by staging: index a filtered copy and swap it in;
- the MathWorks reference catalog: size and shape.

MATLAB side (run in a session): ``addpath(<folder with info.xml>)``,
``builddocsearchdb(<html>)``,
``matlab.internal.doc.project.getCustomToolboxes()``,
``matlab.internal.doc.search.getSearchPort()``; results page:
``http://127.0.0.1:<port>/static/help/customdoc/searchresults.html?qdoc=<term>&searchPort=<port>&selectedsource=3p``.
