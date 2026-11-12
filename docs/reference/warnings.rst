Warnings
========

Every warning of the :term:`extension` has the type ``mat`` and one of these
subtypes. Turn one off with ``suppress_warnings = ["mat.<subtype>"]``, or
all with ``"mat"``; ``scmd apidoc`` reads the same setting.
:doc:`../user-guide/warnings` explains each one.

.. list-table::
   :header-rows: 1
   :widths: 25 50 25

   * - Warning
     - Raised for
     - Emitted
   * - ``mat.parse_error``
     - a file or folder that cannot be read, an invalid ``.mlapp``, a
       ``.slx`` or ``.mdl`` file that is not a readable Simulink file (a Git
       LFS pointer, too large), a parser failure, a file name that is not
       valid UTF-8, two names in one folder that differ only by Unicode
       form, a page that cannot be read
     - every build (reading); parse failures when a page uses the file
   * - ``mat.folder_name``
     - an error, not a warning (``suppress_warnings`` does not hide it): a
       folder named like a supported file (``.m``, ``.mlapp``, ``.slx``,
       ``.mdl``, ``.md``, ``.rst``, any case); it is not documented
     - every build
   * - ``mat.encoding``
     - a file decoded with the fallback encoding or with replaced bytes; a
       page that is not valid UTF-8
     - every build; pages when they are rendered
   * - ``mat.invalid_matlab``
     - a file whose first line of code and parse disagree, a dotted
       ``function`` name, a ``classdef`` named unlike its file, a ``.m``
       file with NUL bytes
     - when a page uses the file (NUL bytes: every build)
   * - ``mat.empty_code_file``
     - an empty file (nothing but blank lines)
     - every build
   * - ``mat.not_callable``
     - a file MATLAB cannot call for :confval:`matlab_version`; the
       message says why (an invalid name, a keyword, a subfolder of a
       class folder, a Simulink file directly in ``private/`` or a class
       folder, or in a namespace folder, ...)
     - every build
   * - ``mat.outside_root``
     - a link below the project root that points outside it
     - every build
   * - ``mat.link_cycle``
     - a link that points to the folder it is in or a folder above it (a
       cycle); it is not followed
     - every build
   * - ``mat.ambiguous``
     - a name that matches several :term:`objects <object>`
     - where the name is used
   * - ``mat.not_found``
     - an auto :term:`directive` whose argument matches no object; a name
       in ``:members:`` that is not a member
     - where the directive is
   * - ``mat.directive``
     - a directive argument of the wrong kind: a class folder given to
       ``mat:folder``, arguments or a return annotation given to
       ``mat:autofolder``
     - where the directive is
   * - ``mat.duplicate``
     - an object described twice, or two objects that would get the same
       anchor
     - where the second description is (the line of the auto directive
       for generated content)
   * - ``mat.sidecar``
     - a sidecar doc without a heading, a ``mat:autosidecar`` reference
       that is not an indexed sidecar doc, a project root on another drive
       than the Sphinx :term:`source folder <source directory>`
     - where the sidecar doc is rendered; the drive at start-up
   * - ``mat.apidoc``
     - ``scmd apidoc``: an unreadable file, output names that differ only
       by case, a path too long for Windows
     - when it runs
   * - ``mat.stable_url``
     - a stable address file (:confval:`matlab_stable_urls`) that cannot be
       written, for example a path too long for Windows
     - at the end of an HTML build
   * - ``mat.simulink``
     - an unknown name in :confval:`matlab_simulink_metadata` or a
       ``:metadata:`` option; a Simulink documentation file that is not
       used, a heading in one of a library that names no masked block, or
       masked blocks without a section
       (:confval:`matlab_simulink_doc_suffixes`)
     - where the directive is, or in the documentation file
   * - ``mat.api_check``
     - a ``matlab-api-check`` finding
     - when the builder runs
