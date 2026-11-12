Simulink files
==============

The :term:`extension` reads Simulink models, libraries and subsystem files
(``.slx`` and ``.mdl``) without MATLAB, from every release since R2006a,
and documents them next to the code: description, mask, ports, metadata
and a documentation file of your own. :doc:`../developer-guide/simulink-file-formats` describes the formats.

What is documented
------------------

* **Models** (``mat:autosimulink_model``).
* **Libraries** (``mat:autosimulink_library``).
* **Subsystem files**, the targets of Subsystem Reference blocks
  (``mat:autosimulink_subsystem_reference``).
* **Library blocks** (``mat:autosimulink_library_block``): the masked
  blocks at the top of a library, and those below subsystems without a
  mask. A linked block (a copy of another library's block) and a
  sublibrary block (an empty subsystem whose ``OpenFcn`` opens a library)
  are links, not :term:`objects <object>` of their own. Blocks inside
  models and subsystem files are not documented: the file is the object.

Each page shows the description saved in the file or block (the mask
description if it has none), then the documentation file, the mask type,
description and Help, the metadata of :confval:`matlab_simulink_metadata`,
the mask parameters (hidden ones with ``:hidden-mask-parameters:``) and a
table of the ports: inputs, outputs and physical connections by port
number, then the enable, trigger and action ports.
:doc:`../reference/directives` lists the options.

Names
-----

A Simulink file is named the way Simulink runs it. A file in a namespace
folder (``+pkg/``), directly in ``private/`` or in an ``@`` class folder has
no MATLAB name (a ``mat.not_callable`` warning) and is documented by its
path reference (``+pkg/plant.slx``).

.. _simulink-namespaces:

Simulink files in namespace folders
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keep Simulink files in the global namespace. Simulink's support for
``.slx`` and ``.mdl`` files in ``+pkg/`` folders is partial and changes
between releases (observed in R2024a, R2024b, R2026a and R2026b, the same
for ``.slx`` and ``.mdl``):

* **Works in every release:** ``load_system``, ``sim`` and ``save_system``
  with the full path; ``sim(pkg.plant)`` written as an expression without
  quotes (MATLAB resolves ``pkg.plant`` like a function call and passes the
  model handle), also for ``pkg.inner.plant``.
* **Works from R2026a:** ``load_system("pkg.plant")``. The model is loaded
  under its short name ``plant``, so it can clash with a global model of
  the same name.
* **Never works:** ``sim("pkg.plant")``; a namespace name in a Model block,
  Subsystem Reference block or library link; finding the file by its short
  name, even after ``cd`` into ``+pkg``; ``load_system("pkg.inner.plant")``.
* **Only when the target is loaded first:** a Model or Subsystem Reference
  block that gives the short name ``plant``. Library links into ``+pkg/``
  work that way in R2024a and R2024b and fail in R2026a and R2026b.

Because a namespaced Simulink file cannot be used by name in a model, the
extension gives it no MATLAB name: reference it by path
(``:mat:simulink_model:`+pkg/plant.slx```).

A block follows its file with its path in the library:
``lib.slx/Group/Gain`` or, by MATLAB name, ``lib/Group/Gain``. A ``/`` in a
block name is doubled (``lib.slx/A//B``); a line break in a block name is
written as a space (``lib/Two Lines``) in a :term:`role`'s target, an auto
directive's argument, ``:members:`` and ``:exclude-members:``; the block's entry in ``objects.inv`` has that form,
so another project links to it with the same text. A name in
``:members:`` that is no documented block gets ``mat.not_found``.

``plant.slx`` and ``plant.m`` share a MATLAB name, like two ``plant.m`` in
different folders: give the path reference, or see
:confval:`matlab_link_shadowed_files_to_chooser_pages`.

Documenting
-----------

.. code-block:: rst

   .. mat:autosimulink_model:: plant
      :references:

   .. mat:autosimulink_library:: controlLib
      :members:

``:members:`` of a library documents its blocks in the library's order and
adds a list, *Links to other blocks*, of its linked and sublibrary blocks,
each a link. A block or library outside the project (a MathWorks library
such as ``simulink/Sources/Sine Wave``) stays text without a warning.
``:references:`` lists what a model or subsystem file uses (model
references, subsystem references, library links). ``scmd apidoc``
writes these :term:`directives <directive>` for you (:doc:`apidoc`), with a section for each
kind and one for the blocks of the libraries.

"See also" entries and :confval:`matlab_auto_link` link names of models,
libraries and subsystem files in MATLAB help text.

Documentation files
-------------------

Dialog boxes are no place for long text. Write it in a file next to the
Simulink file, with the same name: ``plant.md`` or ``plant.rst`` next to
``plant.slx`` (:confval:`matlab_simulink_doc_suffixes`; Markdown needs
``myst_parser`` in ``extensions``). The auto directives put its text after
the description; the description stays the short summary.

* The first heading is the title and is dropped; deeper headings become
  rubrics.
* A model or subsystem file gets the whole text.
* A library's file has a section for each block, headed by the block's path
  in the library; the text before the first such section is the library's:

  .. code-block:: md

     # Control library

     Blocks for the plant's controllers.

     ## PID

     A PID controller with anti-windup.

     ## Filters/Low Pass

     A first-order low-pass filter.

  A heading that names no masked block, and masked blocks without a
  section, get ``mat.simulink`` warnings. A block with a section counts as
  documented for ``:members:``.
* Relative links, images and includes work as in :doc:`sidecars`, but a
  documentation file is not a sidecar doc: it has no page of its own.

Example
-------

The sample project of this documentation has a library,
``simulink/shapeBlocks.slx``, with a documentation file
``simulink/shapeBlocks.rst``, and a model, ``simulink/shapeAreas.slx``,
that uses one of its blocks:

.. code-block:: rst

   .. mat:autosimulink_library:: shapeBlocks
      :members:

   .. mat:autosimulink_model:: shapeAreas
      :references:

gives:

.. mat:autosimulink_library:: shapeBlocks
   :members:

.. mat:autosimulink_model:: shapeAreas
   :references:

The Help button
---------------

A model, subsystem file or library block can open its page from its Help
button. ``scmd quickstart`` adds
``+sphinxcontrib/+matlabdomain/simulinkDocumentationLinker.m`` to a project
with Simulink files, and asks for the address of the published site. The
Help of an object calls it with the object's path reference:

.. code-block:: matlab

   web(sphinxcontrib.matlabdomain.simulinkDocumentationLinker("src/controlLib.slx/PID"))

It opens the local build after ``make html``, the server of ``make
livehtml`` while it runs (:confval:`matlab_simulink_autobuild_server`), or else the
published site; ``help sphinxcontrib.matlabdomain.simulinkDocumentationLinker``
describes the choice. The documentation shows such a Help as a link to the
page.

The settings file ``simulinkDocumentationLinker.json`` next to it names the
folder of the local build, the server and the published site. ``scmd
quickstart`` writes it once; a build never changes it, because a build
writes only to its output folder and its doctree folder. When the output
folder, the server or ``html_baseurl`` of a build differs from the file,
the build logs one ``info`` line (not a warning, so ``-W`` builds and CI
builds with another output folder are not affected) that names the values:
edit ``local``, ``server`` or ``published`` by hand and commit the file.
Each HTML build writes ``mat/simulinkDocumentationLinker.json`` in its
output folder, which tells the function whether the last build was local or
for a server.

``sphinxcontrib.matlabdomain.setSimulinkHelp`` writes these Help lines for
every documented object of a file. It ships with this package; add its
folder to the MATLAB path first:

.. code-block:: console

   $ python -c "from sphinxcontrib.mat_simulink import MATLAB_TOOLS; print(MATLAB_TOOLS)"

.. code-block:: matlab

   addpath("<the folder printed above>")
   sphinxcontrib.matlabdomain.setSimulinkHelp("src/controlLib.slx", "src")

It leaves a Help with other text alone unless ``Overwrite=true``, and
returns a table of what it did.
