Linking between projects
========================

Sphinx's ``sphinx.ext.intersphinx`` links the pages of one project to the
:term:`objects <object>` that another project documents. This page sets up a MATLAB library
(the *producer*) and a project that links to it (the *consumer*), and
explains which links follow the library's objects when its pages change.

The library
-----------

The library needs no setting. Every HTML build writes the :term:`inventory`,
``objects.inv``, next
to the pages: one entry per documented object, named by its path reference,
with its MATLAB name, type and stable address (``mat/ref/util/scale.m.html``,
:ref:`stable-addresses`). Publish the
whole output folder, so that the inventory sits at the site's root, for
example ``https://docs.example.org/team/lib/objects.inv``. The site may be
below a path, as here.

Publish from an empty output folder:

.. code-block:: bash

   rm -rf docs/_build
   uv run scmd apidoc --conf-dir docs
   uv run sphinx-build -b html docs docs/_build/html

Sphinx never deletes a page it no longer builds. This :term:`extension` removes
the HTML page, and its copy in ``_sources``, of every page below
:confval:`matlab_apidoc_output_dir` whose source ``scmd apidoc``
removed (``global-2`` when it writes fewer pages). Other removed pages
stay in an output folder kept from an earlier build, and in a site copied
from it; a CI job that starts from a fresh checkout has an empty output
folder.

The consumer
------------

Load this extension, which provides the ``mat`` :term:`roles <role>`, and intersphinx,
and name the library's site:

.. code-block:: python

   extensions = ["sphinxcontrib.matlab", "sphinx.ext.intersphinx"]
   intersphinx_mapping = {
       "lib": ("https://docs.example.org/team/lib/", None),
   }

``None`` reads ``objects.inv`` from the site. A second value gives another
place to read it from, such as the output of a local build of the library,
``("https://docs.example.org/team/lib/",
"../../lib/docs/_build/html/objects.inv")``; the links still point to the
site. :confval:`matlab_src_code_project_root` is needed only if the
consumer documents MATLAB files of its own.

References
----------

References to the library are written like local ones:

.. code-block:: rst

   :mat:class:`geom.Circle`              a MATLAB name
   :mat:func:`util/scale.m`              a path reference
   :mat:meth:`geom.Circle.area`          a member
   :mat:folder:`geom`                    a namespace, if documented
   :mat:func:`Scale it <util/scale.m>`   with link text
   :mat:func:`lib:util/scale.m`          in the inventory "lib" only
   :external+lib:mat:func:`scale`        in "lib" only, never a local object

A target is looked up:

1. among the consumer's own objects (:doc:`referencing`): a local object
   with the same MATLAB name or path reference wins;
2. in the inventories, by path reference;
3. in the inventories, by MATLAB name, if exactly one object of the role's
   type has it, ignoring ``private/`` files. If several have it (two
   global ``helper`` functions in different folders), a ``mat.ambiguous``
   warning lists their path references (with the inventory,
   ``lib:examples/helper.m``, when several are loaded), and the text is not
   linked: write one of them instead. With
   :confval:`matlab_link_shadowed_files_to_chooser_pages`, the text links to the page of
   the other site that lists them, without the warning, if that site was
   built with this release or later.

The ``lib:`` prefix and the ``:external+lib:`` role search only that
inventory; ``:external:`` and ``:external+lib:`` skip the local objects.
When several inventories have the same path reference (two versions of one
library), a ``mat.ambiguous`` warning lists them (``one:util/scale.m``,
``two:util/scale.m``) and the text is not linked: write one of them.

Unlike local references:

* The role must match the object's type: ``:mat:func:`` does not find a
  class in an inventory; ``:mat:obj:`` finds any type.
* Files in ``private/`` are found by path reference only.
* Lookups relative to the current folder or class, and the ``.name``
  suffix search, find local objects only.
* Folders are in the inventory only where the library documents them:
  with :confval:`matlab_apidoc_group` ``"folder"``, or with
  ``mat:autofolder`` or ``mat:folder`` on a hand-written page.
* Without link text, a link shows the object's MATLAB name, without
  ``()``; ``~`` does not shorten it.

.. _library-changes:

When the library changes
------------------------

An object's path reference, inventory name and anchor
(``#mat-util/scale.m``) change only when its file moves or is renamed. Its
*page* can change without that: :confval:`matlab_apidoc_page_size` splits a
long namespace or folder into pages (``global.html``, ``global-2.html``),
and adding or removing a file moves the entries after it to another page.

References in a consumer link to the object's stable address in the
library, which opens the page the object is on now. They keep working when
the library's pages split differently, even if the consumer was built with
an older inventory. A new, renamed or moved file needs a newer inventory,
and a consumer's links are only as recent as the inventory it read and the
pages it wrote:

* intersphinx keeps an inventory read from a site for
  ``intersphinx_cache_limit`` days (5 by default). Recent Sphinx versions
  keep a copy in the doctree folder, so even ``-E`` reuses it. Set
  ``intersphinx_cache_limit = 0`` to read it on every build, or delete the
  doctree folder. An inventory read from a file is read on every build.
* Sphinx writes only the pages whose source changed, so a page that links to
  the library keeps its old links until it is written again. Build with
  ``-a`` (or into an empty folder) after the inventory changed.

.. code-block:: bash

   sphinx-build -a -D intersphinx_cache_limit=0 -b html docs docs/_build/html

A consumer built with an inventory from before a file was renamed or
removed links to an address that no longer exists, without a warning.
``sphinx-build -b linkcheck docs docs/_build/linkcheck`` reports such
links. With :confval:`matlab_stable_urls` ``False`` the inventory holds the
page addresses (``api/global.html#mat-util/scale.m``), and a consumer built
with an old inventory links to the object's old page.

.. _stable-addresses:

Stable addresses
~~~~~~~~~~~~~~~~

Every HTML build also (not EPUB, ``json`` or ``pickle``, which write no
``.html`` pages) writes a small file for each documented object
that sends the browser to the page the object is on now
(:confval:`matlab_stable_urls`):

* ``mat/name/<MATLAB name>.html``, for example ``mat/name/geom.Circle.html``
  or ``mat/name/geom.Circle.area.html``. If several objects have the name
  (two global ``helper`` functions), it is a page in the site's theme that
  lists them all, with their path references and types, like MATLAB's
  ``which -all``. Files in
  ``private/`` and files MATLAB cannot call have no such address.
* ``mat/ref/<path reference>.html`` for every object, for example
  ``mat/ref/+geom/Circle.m.html``; a folder's is ``mat/ref/<folder>/index.html``.

The "¶" link next to an object points to its address by MATLAB name, or
by path reference if the name is not unique; ``objects.inv`` gives the
address by path reference, and has an entry for each MATLAB name of
several objects (once per object type) that points to the page listing
them. Copy that link, not the
browser's address bar: these addresses stay the same when the pages split
differently, and change only when the object is renamed, moved or removed
(then the file is removed too). Characters that are not safe in a URL, and
names that differ only by case, are escaped like the output names of
``scmd apidoc``.

The address in the browser's address bar after the redirect is the page's
own, which does not follow the object. A small script on every page
helps when such an address is opened later: if the page no longer has the
object (``#mat-util/scale.m``), it opens the object's stable address. If
the page is gone, the build's ``404.html`` does the same, on hosts that
show it for missing pages, such as GitHub Pages (the build does not
replace a ``404.html`` of the project's own, for example from
``sphinx-notfound-page``, whose page still runs the script). Both read
``mat/refs.js``, a list of all the stable addresses, only when needed.

An incremental build in which objects were added, removed or moved to
other pages also writes again every page that links to a MATLAB object,
so the links between the library's own pages follow the objects. A build
that writes no page renders the pages that list several objects again only
when what they list changed or one of them is missing; ``mat/choosers.json``
records what the pages on disk list.

:confval:`matlab_apidoc_separate` gives each file a page named by its path
(``api/util/scale.m.html``), so its page address does not depend on the
split either; only the listing pages split. The stable addresses make this
unnecessary for links, and a page per file makes builds slower.
