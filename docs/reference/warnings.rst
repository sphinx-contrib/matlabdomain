Warnings
========

Every warning of the extension has the type ``mat`` and one of these
subtypes. Turn one off with ``suppress_warnings = ["mat.<subtype>"]``, or
all with ``"mat"``. :doc:`../user-guide/warnings` explains each one.

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
   * - ``mat.no_code``
     - an empty or comment-only file
     - every build
   * - ``mat.not_callable``
     - a file MATLAB cannot call for :confval:`matlab_version`
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
   * - ``mat.api_check``
     - a ``matlab-api-check`` finding
     - when the builder runs
