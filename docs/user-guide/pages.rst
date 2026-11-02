Pages next to code
==================

Tutorials, design notes and READMEs often sit next to the MATLAB code they
describe. With :confval:`matlab_src_page_suffixes`, the extension indexes
such ``.md`` and ``.rst`` files with the code, renders them into your
documentation with ``mat:autopage``, links between them and the code,
generates a page for each with ``sphinx-matlab-apidoc`` and checks them
with ``matlab-api-check``. It is off by default.

Turning it on
-------------

List the suffixes in ``conf.py``. Markdown needs `myst-parser
<https://myst-parser.readthedocs.io/>`_ (the ``markdown`` extra,
:doc:`../getting-started/installation`) in ``extensions``; without it,
``".md"`` is a configuration error:

.. code-block:: python

   extensions = ["sphinxcontrib.matlab", "myst_parser"]
   matlab_src_code_project_root = "../src"
   matlab_src_page_suffixes = [".md", ".rst"]

Which files are pages
---------------------

* Files with one of the suffixes below the project root that
  :confval:`matlab_src_include_patterns` and
  :confval:`matlab_src_exclusion_patterns` select, like code. By default
  the exclusion patterns leave out ``README.*``, ``CHANGES.*``,
  ``CHANGELOG.*``, ``LICENSE.*``, ``CONTRIBUTING.*``,
  ``CODE_OF_CONDUCT.*`` and ``SECURITY.*`` at the root, which describe the
  repository rather than the code. Add patterns for anything else, such as
  notes for tools (``"**/CLAUDE.md"``).
* Pages are read as UTF-8 (a byte-order mark is allowed), whatever
  :confval:`matlab_src_encoding` says. Invalid bytes are replaced, with a
  ``mat.encoding`` warning.
* A page has a path reference (``+demo/guide.md``) but no MATLAB name, so
  ``guide.md`` next to ``guide.m`` is fine: names find the code.

The Sphinx source folder and the project root may be arranged three ways:

* **Apart** (``docs/`` and ``src/``): nothing to consider.
* **The source folder inside the root** (root ``repo/``, docs in
  ``repo/docs/``): files in the source folder are documents, never pages.
  Code there is still indexed.
* **The root inside the source folder** (``docs/src/``): Sphinx would read
  the pages as documents too. The extension adds each page to
  ``exclude_patterns`` when the configuration is read, so it does not.
  Adding or removing a page then changes ``exclude_patterns``, and Sphinx
  reads every document again once.

The root cannot be the source folder itself (a configuration error), and on
Windows a root on another drive than the source folder gets a ``mat.page``
warning: relative paths in pages cannot be resolved there.

Rendering a page
----------------

``mat:autopage`` takes the page's path reference and renders the page where
it stands; a document of its own needs nothing else:

.. code-block:: rst

   .. mat:autopage:: +demo/getting-started.md

The page's headings become sections and its first heading is the
document's title. A page without a heading gets its file name as title,
with a ``mat.page`` warning. ``:no-title:`` leaves out the first heading,
so the rest continues the current section; ``sphinx-matlab-apidoc`` uses it
for READMEs (below). This page renders ``+shapes/notes.rst`` from this
documentation's sample project:

.. code-block:: rst

   .. mat:autopage:: +shapes/notes.rst

.. mat:autopage:: +shapes/notes.rst

Use ``mat:autopage`` in reST documents; in a Markdown document, a reST page
would be read as Markdown.

Paths and links
---------------

Relative paths in a page are relative to the page's folder, as on GitHub:

* images (``![plot](img/plot.png)``, ``.. image::``, ``.. figure::``) and
  downloads (``:download:``) are copied into the output;
* ``literalinclude`` and ``include`` read files next to the page.

In Markdown, a relative link goes to:

* another page: the document that renders it, with the page's title when
  the link has no text (``[](notes.rst)``); an anchor (``notes.rst#usage``)
  goes to the section with that id, or with that slug when
  ``myst_heading_anchors`` is set;
* a code file (``[](scale.m)``, ``[the class](@Shape/Shape.m)``): its API
  entry, with its MATLAB name when the link has no text;
* any other file: a download;
* anything else: myst-parser decides, as in any Markdown document.

The domain's roles work in pages: ``:mat:func:`demo.scale``` in reST,
``{mat:func}`demo.scale``` in Markdown. ``:mat:page:`` links to a page by
its path reference, with the page's title as text:
``:mat:page:`+demo/getting-started.md```.

Raw HTML images (``<img src="img/plot.png">``) are rendered only with
myst-parser's ``html_image`` extension (``myst_enable_extensions =
["html_image"]``); other raw HTML is copied as is, and its relative paths
are not resolved.

Pages with ``sphinx-matlab-apidoc``
-----------------------------------

With :confval:`matlab_src_page_suffixes` in ``conf.py``,
``sphinx-matlab-apidoc -c`` (:doc:`apidoc`) writes a page for each page next
to code, named after the file with its suffix after a ``-``
(``getting-started.md`` -> ``getting-started-md.rst``; a name that ends in
``.md.rst`` would lose its ``.md`` in a toctree). The folder's page lists
them in a "Pages" section after the API sections and before "Folders"
(pages in ``@`` folders on the page of the folder above, like their code).
Pages come from ``conf.py`` only: no flag turns them on or off.

A folder's README (``README.md``, ``readme.rst``, any letter case) is not a
page of its own: it is the introduction of the folder's page, without its
first heading. A README in an ``@`` folder, which has no page, is an
ordinary page.

The worked example has a Markdown page with an image in ``src/+demo/`` and
a reST page in ``src/utils/``:

.. literalinclude:: ../../examples/apidoc/src/+demo/getting-started.md
   :language: markdown

The generated namespace page starts with the README and lists the page:

.. literalinclude:: ../../examples/apidoc/docs/api/+demo/index.rst
   :language: rst

and the page's own page holds one directive:

.. literalinclude:: ../../examples/apidoc/docs/api/+demo/getting-started-md.rst
   :language: rst

The templates get the pages as the keys ``pages`` and ``readme``, and a
page's page comes from ``page.rst.jinja`` (:doc:`../reference/templates`).

Checking pages
--------------

``matlab-api-check`` (:doc:`api-check`) checks every page: the rule
``page-documented`` finds pages that no ``mat:autopage`` renders, or only
in documents no toctree includes; ``page-links`` finds relative links and
downloads to missing files and missing images. Exclude pages from the
check with :confval:`matlab_api_check_ignore_patterns`.

Builds
------

A page is a dependency of the document that renders it, as are its images
and included files: editing one reads only the documents that use it again.
A missing image or link target is a dependency too, so its document is
read on every build until the file exists (Sphinx does the same for
missing images). Parallel builds (``-j``) give the same output as serial
ones.
