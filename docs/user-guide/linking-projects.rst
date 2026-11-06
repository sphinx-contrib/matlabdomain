Linking between projects
========================

Sphinx's ``sphinx.ext.intersphinx`` links the pages of one project to the
objects that another project documents. This page sets up a MATLAB library
(the *producer*) and a project that links to it (the *consumer*), and
explains which links follow the library's objects when its pages change.

The library
-----------

The library needs no setting. Every HTML build writes ``objects.inv`` next
to the pages: one entry per documented object, named by its path reference,
with its MATLAB name, type and address (:doc:`referencing`). Publish the
whole output folder, so that the inventory sits at the site's root, for
example ``https://docs.example.org/team/lib/objects.inv``. The site may be
below a path, as here.

Publish from an empty output folder:

.. code-block:: bash

   rm -rf docs/_build
   sphinx-matlab-apidoc -c docs
   sphinx-build -b html docs docs/_build/html

Sphinx never deletes a page it no longer builds. When
``sphinx-matlab-apidoc`` writes fewer pages than before (``global-2``
disappears), an output folder kept from an earlier build still holds the
old page with its old content, and so does a site copied from it. A CI job
that starts from a fresh checkout has an empty output folder.

The consumer
------------

Load this extension, which provides the ``mat`` roles, and intersphinx,
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
   linked: write one of them instead.

The ``lib:`` prefix and the ``:external+lib:`` role search only that
inventory; ``:external:`` and ``:external+lib:`` skip the local objects.
When two inventories have the same path reference (two versions of one
library), intersphinx links to one of them: name the inventory.

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

References in a consumer follow the object when the consumer is built again
with the new inventory. Its links are only as recent as the inventory it
read and the pages it wrote:

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

A consumer built with an old inventory links to the object's old page,
without a warning. ``sphinx-build -b linkcheck docs docs/_build/linkcheck``
reports such links: ``Anchor 'mat-util/scale.m' not found``.

Stable addresses
~~~~~~~~~~~~~~~~

Every HTML build also writes a small file for each documented object
that sends the browser to the page the object is on now
(:confval:`matlab_stable_urls`):

* ``mat/name/<MATLAB name>.html``, for example ``mat/name/geom.Circle.html``
  or ``mat/name/geom.Circle.area.html``. If several objects have the name
  (two global ``helper`` functions), the file lists them all, with their
  path references and types, like MATLAB's ``which -all``. Files in
  ``private/`` and files MATLAB cannot call have no such address.
* ``mat/ref/<path reference>.html`` for every object, for example
  ``mat/ref/+geom/Circle.m.html``; a folder's is ``mat/ref/<folder>/index.html``.

The "¶" link next to an object points to its address by MATLAB name, or
by path reference if the name is not unique. Copy that link, not the
browser's address bar: these addresses stay the same when the pages split
differently, and change only when the object is renamed, moved or removed
(then the file is removed too). Characters that are not safe in a URL, and
names that differ only by case, are escaped like the output names of
``sphinx-matlab-apidoc``.

The address in the browser's address bar after the redirect is the page's
own, which does not follow the object. If the old page still exists, the
browser opens it at the top, without an error and without the object; if
the page is gone, the site answers "404 Not Found". Links between the
library's own pages follow the object in a full build; an incremental build
writes only the pages whose source changed, so build with ``-a`` after the
API pages were regenerated.

:confval:`matlab_apidoc_separate` gives each file a page named by its path
(``api/util/scale.m.html``), so its page address does not depend on the
split either; only the listing pages split. The stable addresses make this
unnecessary for links, and a page per file makes builds slower.
