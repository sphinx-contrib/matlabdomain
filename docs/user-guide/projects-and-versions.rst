Several projects and versions
=============================

One build documents one project: everything below one
:confval:`matlab_src_code_project_root`. Several projects, or several
versions of one project, are several builds. This page shows how to set
them up, link them, search them together, and what the two common helper
extensions do and do not do.

What was checked, with ``sphinx-matlab-apidoc`` pages, sidecar docs and
``-n -W`` builds:

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Setup
     - Status
     - Notes
   * - One build per project, linked with intersphinx
     - works
     - The recommended way to document several projects.
   * - `sphinx-multiproject`_ 1.0.0, values in its ``config`` option
     - works
     - Same output as one build per project.
   * - sphinx-multiproject 1.0.0, values in ``<project>/conf.py``
     - Sphinx 8 only
     - Its default; fails on Sphinx 9, in the extension.
   * - One search over several projects
     - with a tool
     - Not from Sphinx or either extension; Pagefind works (below).
   * - `sphinx-multiversion`_ 0.2.5 on Sphinx 8.2
     - works
     - When each version's commit holds its API pages (below).
   * - sphinx-multiversion on Sphinx 9
     - fails
     - In the extension (``Config.read()``); not yet fixed there.

These were tried on Windows; Linux and macOS were not tried.

Several projects
----------------

Give each project its own Sphinx source folder with its own ``conf.py``;
settings they share can live in a module the ``conf.py`` files import:

.. code-block:: text

   docs/
     shared_conf.py        # extensions, theme, ...
     alpha/conf.py         # from shared_conf import *; project = "Alpha"
     alpha/index.rst
     beta/conf.py
     beta/index.rst
   alpha/src/              # Alpha's MATLAB code
   beta/src/

.. code-block:: python

   # docs/alpha/conf.py
   import os
   import sys

   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   from shared_conf import *

   project = "Alpha"
   matlab_src_code_project_root = "../../alpha/src"
   matlab_apidoc_output_dir = "api"

Generate the pages and build each project into its own folder:

.. code-block:: console

   $ sphinx-matlab-apidoc -c docs/alpha
   $ sphinx-build -b html docs/alpha docs/_build/alpha/html
   $ sphinx-matlab-apidoc -c docs/beta
   $ sphinx-build -b html docs/beta docs/_build/beta/html

The projects may use the same path references, MATLAB names, page names
and sidecar image names: each build has its own index, environment,
inventory and images. Rebuilding one project does not touch the other.
Do not build two projects into one output or doctree folder: each build
then starts from scratch, and a page only the first project has stays in
the output.

Links between projects
~~~~~~~~~~~~~~~~~~~~~~

Use ``sphinx.ext.intersphinx``. When the projects are published side by
side (``site/alpha/``, ``site/beta/``), Beta's ``conf.py`` can point at
Alpha's built inventory:

.. code-block:: python

   intersphinx_mapping = {
       "alpha": ("../alpha/", "../_build/alpha/html/objects.inv"),
   }

A role finds an object of the project itself first, so a path reference
that both projects have links locally. Name the other project to link
there:

.. code-block:: rst

   :mat:func:`+shared/compute.m`                 (Beta's own)
   :external+alpha:mat:func:`+shared/compute.m`  (Alpha's)

Build the project that others link to first.

sphinx-multiproject
~~~~~~~~~~~~~~~~~~~

`sphinx-multiproject`_ is for Read the Docs, where a repository has one
configuration: one ``conf.py`` serves several projects, and the
``PROJECT`` environment variable picks the one to build. It does not
merge projects: each build still has one source folder (it moves the
source folder, not the configuration folder) and one search index.
Outside Read the Docs, its documentation recommends the layout above.

Its default reads ``<project>/conf.py``. That fails on Sphinx 9 (``'str'
object has no attribute 'parent'``), and on Sphinx 8 the file must not set
``extensions`` and the other values Sphinx reads before extensions load,
so it cannot also build on its own. Pass the values through its
``config`` option instead, taken from the project's ``conf.py``, which
``sphinx-matlab-apidoc -c docs/<project>`` reads:

.. code-block:: python

   # docs/conf.py
   import os
   import runpy

   _here = os.path.dirname(os.path.abspath(__file__))


   def _values(name):
       conf = runpy.run_path(os.path.join(_here, name, "conf.py"))
       return {
           key: value
           for key, value in conf.items()
           if key in ("project", "intersphinx_mapping") or key.startswith("matlab_")
       }


   extensions = [..., "multiproject"]
   multiproject_projects = {
       name: {"use_config_file": False, "config": _values(name)}
       for name in ("alpha", "beta")
   }

.. code-block:: console

   $ PROJECT=alpha sphinx-build -b html docs docs/_build/alpha/html

A relative :confval:`matlab_src_code_project_root` stays relative to the
project's folder (``docs/alpha``), as in the layout above. The
``templates_path`` and ``html_static_path`` of ``docs/conf.py`` are
relative to ``docs``.

Searching several projects
~~~~~~~~~~~~~~~~~~~~~~~~~~

Sphinx's search covers one build. Intersphinx links projects, but does
not merge their searches, and neither extension on this page does. One
search over several projects needs a tool that indexes the published
HTML, such as `Pagefind`_ (checked with 1.6.0; it is not a dependency of
this extension):

#. Build every project from scratch, into fresh output folders. An
   incremental build removes the API pages of MATLAB files that are gone,
   but keeps the HTML of any other page that no longer exists, and the
   search would still find it.
#. Copy the outputs next to each other: ``site/alpha/``, ``site/beta/``.
#. Index them: ``pagefind --site site`` (``python -m pagefind`` from the
   ``pagefind[bin]`` package, or ``npx pagefind``).
#. Add a search page, ``site/search/index.html``, that loads
   ``../pagefind/pagefind-ui.js``.

Mark what to index and which project a page belongs to with a
``layout.html`` in ``templates_path`` (for the alabaster theme; other
themes name their blocks differently):

.. code-block:: html+jinja

   {% extends "!layout.html" %}
   {% block document %}
   <div data-pagefind-body>
   <span hidden data-pagefind-filter="project">{{ project|e }}</span>
   <span hidden data-pagefind-meta="title">{{ project|e }}: {{ title|striptags|e }}</span>
   {{ super() }}
   </div>
   {% endblock %}

Results then show the project in the title and in a filter, and work
under a URL prefix (``https://example.org/docs/alpha/...``) without
settings. Pagefind's results list pages; to link the object in a page,
build sub-results from the ``mat-`` anchors that Pagefind records, in the
search page's ``processResult`` option (Sphinx puts section ids on
``<section>`` elements, which Pagefind does not use for sub-results).

Several versions
----------------

`sphinx-multiversion`_ builds the documentation of each Git branch and
tag into its own folder and adds a version list to the pages. It needs
Sphinx older than 9: version 0.2.5 fails on Sphinx 9 (``Config.read()``).
How it works, and what follows for this extension:

* It copies each revision from Git (``git archive``) into a temporary
  folder and builds it there. Only committed files are in the copy.
* It builds every version with the ``conf.py`` of the checkout you run it
  from; only ``version``, ``release``, ``rst_prolog`` and ``today`` come
  from the revision. The ``matlab_*`` values are therefore the checkout's.
* A relative :confval:`matlab_src_code_project_root` is relative to the
  Sphinx source folder, which is in the revision's copy, so each version
  documents its own code. An absolute path, or one made from
  ``__file__`` in ``conf.py``, points every version at the checkout's
  code: older versions then document the newest code.

API pages for each version
~~~~~~~~~~~~~~~~~~~~~~~~~~

The API pages must be in the commit of each version. Running
``sphinx-matlab-apidoc`` once before ``sphinx-multiversion`` does not
help: uncommitted pages are not copied, so no version gets API pages.
Two ways work:

* Commit the generated pages, and keep them current with
  ``sphinx-matlab-apidoc --check`` in CI. Every tag then has its pages.
* Keep them out of Git, and add them in a throwaway clone before building:

  .. code-block:: console

     $ git clone . ../docs-build && cd ../docs-build
     $ cp docs/conf.py ../conf.py           # the conf.py the builds use
     $ git checkout --detach v1.0
     $ cp ../conf.py docs/conf.py           # generate with that conf.py
     $ sphinx-matlab-apidoc -c docs
     $ git checkout -- docs/conf.py         # keep the revision's version
     $ git add -f docs/api && git commit -m "API pages"
     $ git tag -f v1.0
     ... the same for every version (git branch -f for a branch) ...
     $ git checkout main
     $ PYTHONSAFEPATH=1 sphinx-multiversion docs ../site

  The clone's tags and branches then point at commits with the pages; do
  not push them.

Each version then has its own pages, objects, inventory, sidecar docs and
images: an object that only one version has is in no other version. The
version list links the same page of another version, or its start page
when that version does not have the page.

Notes:

* Set ``PYTHONSAFEPATH=1``. Each version is built with ``python -m
  sphinx`` in the revision's copy, so a ``sphinxcontrib/`` (or ``sphinx/``)
  folder at the top of the repository is imported instead of the
  installed packages.
* Each version's output folder holds its doctrees (``.doctrees``); leave
  them out when publishing.
* On Python 3.12 and newer, give every ``sphinx-build`` option its value
  in the same argument: ``--doctree-dir=build/doctrees``, ``-bdirhtml``.
  With ``-d build/doctrees`` the folder is taken as a page name.
* Every run builds every version from scratch.
* The default ``smv_released_pattern`` (``^tags/.*$``) matches no tag;
  use ``r"^refs/tags/.*$"``.
* To record which matlabdomain built a version, put
  ``importlib.metadata.version("sphinxcontrib-matlabdomain")`` into
  ``html_context`` and show it in a template; the documented revision is
  ``current_version.name``.

.. _sphinx-multiproject: https://github.com/readthedocs/sphinx-multiproject
.. _sphinx-multiversion: https://github.com/sphinx-contrib/multiversion
.. _Pagefind: https://pagefind.app/
