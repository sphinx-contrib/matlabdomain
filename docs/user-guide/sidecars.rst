Sidecar docs
============

Tutorials, design notes and READMEs often sit next to the MATLAB code they
describe. With :confval:`matlab_src_sidecar_suffixes`, the :term:`extension` indexes
such ``.md`` and ``.rst`` files (sidecar docs) with the code, renders them
into your documentation with ``mat:autosidecar``, links between them and the
code, generates a page for each with ``scmd apidoc`` and checks
them with ``matlab-api-check``. It is off by default.

Turning it on
-------------

List the suffixes in ``conf.py``. Markdown needs `myst-parser
<https://myst-parser.readthedocs.io/>`_ (the ``markdown`` extra,
:doc:`../getting-started/installation`) in ``extensions``; without it,
``".md"`` is a configuration error:

.. code-block:: python

   extensions = ["sphinxcontrib.matlab", "myst_parser"]
   matlab_src_code_project_root = "../src"
   matlab_src_sidecar_suffixes = [".md", ".rst"]

Which files are sidecar docs
----------------------------

* Files with one of the suffixes below the project root that
  :confval:`matlab_src_include_patterns` and
  :confval:`matlab_src_exclude_patterns` select, like code. By default
  the exclusion patterns leave out ``README.*``, ``CHANGES.*``,
  ``CHANGELOG.*``, ``LICENSE.*``, ``CONTRIBUTING.*``,
  ``CODE_OF_CONDUCT.*`` and ``SECURITY.*`` at the root, which describe the
  repository rather than the code. Add patterns for anything else, such as
  notes for tools (``"**/CLAUDE.md"``).
* Sidecar docs are read as UTF-8 (a byte-order mark is allowed), whatever
  :confval:`matlab_src_encoding` says. Invalid bytes are replaced, with a
  ``mat.encoding`` warning.
* A sidecar doc has a path reference (``+demo/guide.md``) but no MATLAB
  name, so ``guide.md`` next to ``guide.m`` is fine: names find the code.

The Sphinx :term:`source folder <source directory>` and the project root may be
arranged three ways:

* **Apart** (``docs/`` and ``src/``): nothing to consider.
* **The source folder inside the root** (root ``repo/``, docs in
  ``repo/docs/``): files in the source folder are documents, never sidecar
  docs. Code there is still indexed.
* **The root inside the source folder** (``docs/src/``): Sphinx would read
  the sidecar docs as documents too. The extension adds each one to
  ``exclude_patterns`` when the configuration is read, so it does not.
  Adding or removing a sidecar doc then changes ``exclude_patterns``, and
  Sphinx reads every document again once.

The root cannot be the source folder itself (a configuration error), and on
Windows a root on another drive than the source folder gets a
``mat.sidecar`` warning: relative paths in sidecar docs cannot be resolved
there.

Rendering a sidecar doc
-----------------------

``mat:autosidecar`` takes the sidecar doc's path reference and renders it
where the :term:`directive` stands; a document of its own needs nothing else:

.. code-block:: rst

   .. mat:autosidecar:: +demo/getting-started.md

The sidecar doc's headings become sections and its first heading is the
document's title. One without a heading gets its file name as title,
with a ``mat.sidecar`` warning. ``:no-title:`` leaves out the first heading,
so the rest continues the current section; ``scmd apidoc`` uses it
for READMEs (below). This page renders ``+shapes/notes.rst`` from this
documentation's sample project:

.. code-block:: rst

   .. mat:autosidecar:: +shapes/notes.rst

.. mat:autosidecar:: +shapes/notes.rst

In :term:`reST` documents, ``mat:autosidecar`` supports both sidecar formats.
Markdown sidecars also work directly in :term:`MyST` documents. For a reST sidecar
in a MyST document, use an ``eval-rst`` block; otherwise MyST reads the
sidecar's contents as Markdown:

.. code-block:: markdown

   ```{eval-rst}
   .. mat:autosidecar:: +demo/notes.rst
   ```

Paths and links
---------------

Relative paths in a sidecar doc are relative to its folder, as on GitHub:

* images (``![plot](img/plot.png)``, ``.. image::``, ``.. figure::``) and
  downloads (``:download:``) are copied into the output;
* ``literalinclude`` and ``include`` read files next to the sidecar doc.

A relative link written in Markdown (``[notes](notes.rst)``) or as a reST
hyperlink (```notes <notes.rst>`_``) goes to:

* another sidecar doc: the document that renders it, with its title when
  the link has no text (``[](notes.rst)``); an anchor (``notes.rst#usage``)
  goes to the section with that id, or with that slug when
  ``myst_heading_anchors`` is set;
* a code file (``[](scale.m)``, ``[the class](@Shape/Shape.m)``): its API
  entry, with its MATLAB name when the link has no text;
* any other file: a download;
* anything else: the document's parser decides.

The domain's roles work in sidecar docs: ``:mat:func:`demo.scale``` in reST,
``{mat:func}`demo.scale``` in Markdown. ``:mat:sidecar:`` links to a sidecar
doc by its path reference, with its title as text:
``:mat:sidecar:`+demo/getting-started.md```.

Raw HTML images (``<img src="img/plot.png">``) are rendered only with
myst-parser's ``html_image`` extension (``myst_enable_extensions =
["html_image"]``); other raw HTML is copied as is, and its relative paths
are not resolved.

Sidecar docs with ``scmd apidoc``
---------------------------------

With :confval:`matlab_src_sidecar_suffixes` in ``conf.py``,
``scmd apidoc`` (:doc:`apidoc`) documents the sidecar docs too.

In namespace grouping (the default), each sidecar doc is rendered on the
page of its namespace (or Global), in a "Sidecar docs" section after the
API sections, sorted by file name, each with its own title. A sidecar doc
in an ``@`` folder goes with its class, one in ``private/`` with the folder
above it. READMEs are sidecar docs like the others. The worked example has
a Markdown sidecar doc with an image and a README in ``src/+demo/``, and a
reST one in ``src/utils/``:

.. literalinclude:: ../../examples/apidoc/src/+demo/getting-started.md
   :language: markdown

The generated page of the namespace renders both of ``+demo/``:

.. literalinclude:: ../../examples/apidoc/docs/api/demo.rst
   :language: rst

In folder grouping, each sidecar doc gets a page of its own, named after
the file with its suffix after a ``-`` (``getting-started.md`` ->
``getting-started-md.rst``; a name that ends in ``.md.rst`` would lose its
``.md`` in a toctree), with one ``mat:autosidecar`` directive. The folder's
page lists them in a "Sidecar docs" section after the API sections
(sidecar docs in ``@`` folders on the page of the folder above, like their
code). A folder's README (``README.md``, ``readme.rst``, any letter case)
does not get a page of its own: it is the introduction of the folder's
page, without its first heading. A README in an ``@`` folder, which has no
page, is an ordinary sidecar doc.

The templates get the sidecar docs as the key ``sidecars`` (and, in folder
grouping, ``readme``); a sidecar doc's page comes from
``sidecar.rst.jinja`` (:doc:`../reference/templates`).

Checking sidecar docs
---------------------

``matlab-api-check`` (:doc:`api-check`) checks every sidecar doc: the rule
``sidecar-documented`` finds sidecar docs that no ``mat:autosidecar``
renders, or only in documents no toctree includes; ``sidecar-links`` finds
relative links and downloads to missing files and missing images. Exclude
sidecar docs from the check with :confval:`matlab_api_check_ignore_patterns`.

Builds
------

A sidecar doc is a dependency of the document that renders it, as are its
images and included files: editing one reads only the documents that use it
again.
A missing image or link target is a dependency too, so its document is
read on every build until the file exists (Sphinx does the same for
missing images). Parallel builds (``-j``) give the same output as serial
ones.
