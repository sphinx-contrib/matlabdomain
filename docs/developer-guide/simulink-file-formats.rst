Simulink file formats
=====================

What Simulink saves in ``.slx`` and ``.mdl`` files, release by release, as
far as this project reads them. MathWorks does not
publish these formats; everything here was observed in files and checked
against what the Simulink API reports for the same files. The reader is
``sphinxcontrib.mat_simulink``. This page grows with every MATLAB release
(see `Keeping this page current`_).

Layouts
-------

Four layouts carry the same content:

.. list-table::
   :header-rows: 1
   :widths: 25 45 30

   * - Layout
     - How to recognise it
     - Releases
   * - Classic ``.mdl``
     - text that starts with ``Model {``, ``Library {`` or ``Subsystem {``
     - R2006a to R2021a
   * - Text ``.mdl`` (OPC package)
     - first line ``# MathWorks OPC Text Package``
     - R2021b and later
   * - ``.slx``, XML diagram
     - a zip file with ``simulink/blockdiagram.xml``
     - R2012a to R2026a
   * - ``.slx``, JSON diagram
     - a zip file with ``simulink/blockDiagram.json``; the systems stay XML
     - R2026b

Simulink's XML export (``save_system`` with ``ExportToXML``) is not read:
no ``.xml`` file is opened.

An ``.slx`` file is an Open Packaging Conventions (OPC) zip package, like
an App Designer ``.mlapp`` file. The text ``.mdl`` from R2021b holds the same
parts as an ``.slx``, one after another: each starts with a line
``__MWOPC_PART_BEGIN__ /<part name>``, and binary parts end that line with
`` BASE64``. Its first lines (``Model { Version ... Description ... }``) are
a header: the word is ``Model`` for every kind of file, and the description
there is a save note, not the model's description.

A file stored with Git LFS but not fetched is a small text pointer
(``version https://git-lfs.github.com/spec/v1``); the reader reports it
instead of reading it as a model.

What changes per release
------------------------

The first release with each change. Files of all three kinds change the
same way unless noted.

.. list-table::
   :header-rows: 1
   :widths: 12 88

   * - Release
     - Change
   * - R2006a
     - Classic ``.mdl``: nested ``Name { ... }`` sections with one
       ``Key value`` per line; strings in double quotes with C escapes
       (``\n``, ``\t``, ``\"``, ``\\``), continued on following lines as more
       quoted strings; ``SavedCharacterEncoding`` (``windows-1252`` in
       exported files); ``Description`` in the root section;
       ``BlockParameterDefaults``; masks as
       ``Object { $ClassName "Simulink.Mask" ... }``; binary values in a
       ``MatData`` section. The layout stays the same up to R2021a; only
       ``Version`` changes.
   * - R2012a
     - First ``.slx``. ``metadata/coreProperties.xml`` holds the kind
       (``cp:category``: ``model``, ``library``, ``subsystem``; also seen
       capitalized) and the description (``dc:description``). Every system is
       inside ``simulink/blockdiagram.xml``. Masks are
       ``<Object ClassName="Simulink.Mask">`` elements. Block defaults are a
       ``BlockParameterDefaults`` element of ``blockdiagram.xml``. Binary
       values are variables ``DataTag<n>`` of one MAT file,
       ``simulink/bdmxdata.mat``.
   * - R2014b
     - ``simulink/graphicalInterface.xml``.
   * - R2015a
     - ``simulink/configSet0.xml`` and ``configSetInfo.xml``.
   * - R2015b
     - One part per binary value: ``simulink/bdmxdata/<name>.mxarray``,
       referenced as ``Ref="bdmxdata:<name>"``.
   * - R2016b
     - The system mask (the mask of the model or subsystem file itself) in
       ``simulink/modelMask.xml``; up to R2017a it holds a
       ``<ModelMask>`` with a ``Simulink.Mask`` object.
   * - R2017a
     - Bus element ports (``PortName``, ``Element``).
   * - R2017b
     - Masks as ``<Mask>`` elements (also in ``modelMask.xml``); block
       defaults move to ``simulink/bddefaults.xml``.
   * - R2019b
     - Subsystem files (``cp:category`` ``subsystem``; classic root
       ``Subsystem {``) and Subsystem Reference blocks
       (``ReferencedSubsystem``).
   * - R2020a
     - Systems move to their own parts: ``simulink/systems/system_root.xml``
       and ``system_<SID path>.xml``, referenced by
       ``<System Ref="system_..."/>``.
   * - R2021b
     - ``.mdl`` becomes the text OPC package.
   * - R2022b
     - Subsystem Reference blocks save the names of their port blocks
       (``<PortProperties>``).
   * - R2024b
     - ``graphicalInterface.json`` instead of the XML part.
   * - R2026b
     - ``blockDiagram.json``, ``bddefaults.json`` (mask defaults only, no
       block defaults) and ``configSet0.json``.

Compression: ``.slx`` parts are deflated or stored. Files saved by R2024a
and R2026b store the model text uncompressed by default; files exported to
older releases deflate it whatever ``SLXCompressionType`` says. The reader
reads both.

Where each fact is
------------------

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Fact
     - Where it is saved
   * - Kind
     - ``cp:category`` in ``coreProperties.xml`` (``.slx``, text ``.mdl``);
       the root section (classic ``.mdl``). The
       ``blockdiagram.xml`` root element (``<Model>``, ``<Library>``,
       ``<Subsystem>``) is a fallback; ``blockDiagram.json`` does not say.
   * - Description
     - ``dc:description`` in ``coreProperties.xml``; ``Description`` of the
       root section (classic).
   * - Release
     - ``matlabRelease`` in ``metadata/mwcoreProperties.xml``; ``Version`` in
       classic files (``8.6`` is R2015b; from R2023b the version is the
       release, ``23.2``).
   * - Creator, dates, model version
     - ``dc:creator``, ``cp:lastModifiedBy``, ``dcterms:created``,
       ``dcterms:modified``, ``cp:revision``; classic ``Creator``,
       ``LastModifiedBy``, ``Created``, ``LastModifiedDate``,
       ``ModelVersionFormat``.
   * - Blocks
     - ``<Block BlockType=... Name=... SID=...>`` with ``<P Name=...>``
       parameters; classic ``Block { BlockType ... Name ... }``. A name may
       hold a newline (``&#xA;`` in XML, ``\n`` in classic files) or a
       ``/``, which is saved as it is; in a Simulink path it is written
       ``//``.
   * - Parameter values
     - Only values that differ from the default are saved. The defaults are
       ``BlockParameterDefaults`` (in ``blockdiagram.xml``, then
       ``bddefaults.xml``, or the classic section), or Simulink's own when
       the file has none (R2026b).
   * - Masks
     - ``<Mask>`` (``Type``, ``Description``, ``Help``, ``Initialization``,
       ``MaskParameter`` with ``Name``, ``Type``, ``Prompt``, ``Value``,
       ``TypeOptions``); before R2017b and in classic files a
       ``Simulink.Mask`` object with the same properties and an array of
       ``Simulink.MaskParameter`` objects. Very old classic files keep
       masks as block parameters (``MaskType``, ``MaskPromptString``
       separated by ``|``, ``MaskVariables``, ``MaskValueString``).
   * - Help
     - The mask's ``Help``. A model or subsystem file has no help
       parameter of its own (R2026b ``ObjectParameters``): its help is the
       ``Help`` of its system mask (``modelMask.xml``), so a file without a
       system mask has none. When its first line is a URL (``https:``,
       ``file:``, ...) or a ``web`` or ``eval`` call, Simulink opens or runs
       it; other text is shown (R2026b Mask Editor documentation).
   * - Ports
     - ``Inport``, ``Outport`` and ``PMIOPort`` blocks of a system: ``Port``,
       ``OutDataTypeStr``, ``PortDimensions``, ``Unit``, ``Description``. A
       bus element port keeps ``PortName`` and ``Element`` in a
       ``<List ListType="InterfaceData">``. Compiled data types are not
       saved.
   * - References
     - ``ModelReference`` blocks (``ModelNameDialog``), ``SubSystem``
       blocks with ``ReferencedSubsystem``, and library links:
       ``BlockType="Reference"`` with ``SourceBlock``.
   * - DocBlock text
     - ``UserData`` of the DocBlock: ``.mxarray`` parts and classic
       ``MatData`` records hold the same bytes (8 bytes
       ``00 01 49 4D 00 00 00 00``, then MAT-file level 5 elements; in
       ``MatData`` uuencoded). A ``string`` value is saved as an opaque
       object.

Exports drop what the target release cannot hold: a bus element port
becomes a plain ``Inport`` before R2017a, the system mask is lost before
R2016b and in every classic ``.mdl``, and a Subsystem Reference before
R2019b.

How this was verified
---------------------

``tests/simulink/make_fixtures.m`` builds a small model, referenced model,
library and subsystem file in R2026b and exports them to one release per
change point above, as ``.slx`` and ``.mdl``; it also builds them natively
in R2024a as ``.slx``. It then loads every file in R2026b and
writes what the Simulink API reports (kind, description, release, system
mask, ports, references, library blocks) to ``tests/simulink/oracle.json``.
``tests/test_mat_simulink.py`` requires the reader to agree with it for
every fixture.

Exports show what R2026b writes for an old release. Files saved natively by
R2024a match the R2024a exports in every fact the reader uses. The reader
also reads the 2,328 ``.slx`` and ``.mdl`` files that ship with MATLAB R2026b
(about 1.5 ms per file to tell the kind, 6 ms to read) and the model files
of the test projects without an error.

Keeping this page current
-------------------------

For each new MATLAB release (the steps and commands are in
``test_slow/simulink/README.md``):

1. run ``make_fixtures("sources", ...)``, ``make_fixtures("export", ...)``
   and ``make_fixtures("oracle", ...)`` in the new release, after adding the
   previous release to ``fixtureReleases`` when it changed the format;
2. compare the parts and the oracle with the previous release's
   (``test_slow/simulink/survey.py``);
3. add a row to `What changes per release`_ and, if the reader needs a
   change, a test;
4. read the ``.slx`` and ``.mdl`` files that ship with the new release
   (``test_slow/simulink/corpus.py``);
5. rerun ``test_slow/simulink/naming_probe.m``, which checks how Simulink
   loads files by name, and add any change to ``MATLAB_VERSION_RULES``.
