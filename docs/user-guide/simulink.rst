Simulink files
==============

The :term:`extension` reads Simulink models, libraries and subsystem files
(``.slx``, ``.mdl`` and ``.xml`` exported by ``save_system``) without
MATLAB, from every release since R2006a, and documents them next to the
code: description, mask, ports, metadata and a documentation file of your
own. :doc:`../developer-guide/simulink-file-formats` describes the formats.

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
table of the ports. :doc:`../reference/directives` lists the options.

Names
-----

A Simulink file is named the way Simulink runs it. Simulink loads models
only from the global namespace, and not directly from a ``private/`` or
``@`` class folder, so a file there has no MATLAB name (a
``mat.not_callable`` warning) and is documented by its path reference
(``+pkg/plant.slx``). Exported ``.xml`` files have no MATLAB name either.

A block follows its file with its path in the library:
``lib.slx/Group/Gain`` or, by MATLAB name, ``lib/Group/Gain``. A ``/`` in a
block name is doubled (``lib.slx/A//B``); a line break in a block name is a
space in a :term:`role`'s target (``lib/Two Lines``).

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
