Warnings
========

Every warning of the extension has the type ``mat`` and one of these
subtypes. Turn one off with ``suppress_warnings = ["mat.<subtype>"]``, or
all with ``"mat"``; ``sphinx-matlab-apidoc`` reads the same setting.
:doc:`../user-guide/warnings` explains each one.

.. list-table::
   :header-rows: 1
   :widths: 25 50 25

   * - Warning
     - Raised for
     - Emitted
   * - ``mat.parse_error``
     - a file or folder that cannot be read, an invalid ``.mlapp``, a parser
       failure, a file name that is not valid UTF-8, a page that cannot be
       read
     - every build (reading); parse failures when a page uses the file
   * - ``mat.encoding``
     - a file decoded with the fallback encoding or with replaced bytes; a
       page that is not valid UTF-8
     - every build; pages when they are rendered
   * - ``mat.invalid_matlab``
     - a file whose first line of code and parse disagree, a dotted
       ``function`` name, a ``.m`` file with NUL bytes
     - when a page uses the file (NUL bytes: every build)
   * - ``mat.empty_code_file``
     - an empty file (nothing but blank lines)
     - every build
   * - ``mat.not_callable``
     - a file MATLAB cannot call for :confval:`matlab_version`; the
       message says why (an invalid name, a keyword, a subfolder of a
       class folder, ...)
     - every build
   * - ``mat.outside_root``
     - a link below the project root that points outside it
     - every build
   * - ``mat.ambiguous``
     - a name that matches several objects
     - where the name is used
   * - ``mat.not_found``
     - an auto directive whose argument matches no object
     - where the directive is
   * - ``mat.sidecar``
     - a sidecar doc without a heading, a ``mat:autosidecar`` reference
       that is not an indexed sidecar doc, a project root on another drive
       than the Sphinx source folder
     - where the sidecar doc is rendered; the drive at start-up
   * - ``mat.apidoc``
     - ``sphinx-matlab-apidoc``: an unreadable file, output names that
       differ only by case, a path too long for Windows
     - when it runs
   * - ``mat.stable_url``
     - a stable address file (:confval:`matlab_stable_urls`) that cannot be
       written, for example a path too long for Windows
     - at the end of an HTML build
   * - ``mat.api_check``
     - a ``matlab-api-check`` finding
     - when the builder runs
