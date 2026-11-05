Roadmap
=======

Possible later work. None of it is available yet.

More file types
---------------

The file-type registry (:doc:`architecture`) is the place for new MATLAB
file types. Planned:

* Simulink models and libraries (``.slx``, a zip container; ``.mdl``,
  text; exported ``.xml``) and reference subsystems;
* Simscape components (``.ssc``, text).

One handler owns one extension: an ``.slx`` handler would tell models,
libraries and subsystems apart, and an ``.xml`` handler would reject XML
that is not a Simulink export.

``sphinx-matlab-apidoc``
------------------------

* ``Contents.m`` as the description of its folder, as MATLAB's ``help
  folder`` shows it (before the README introduction of
  :doc:`../user-guide/sidecars`).

Running the generator inside ``sphinx-build`` (as ``sphinx.ext.apidoc``
does) is not planned: the build would write into the source folder, which
races with other builds of the same folder and loops ``sphinx-autobuild``.
The command reads ``conf.py`` instead (:doc:`../user-guide/apidoc`).

Help text
---------

* A mode that shows help as preformatted text instead of parsing it as
  reStructuredText (:doc:`../user-guide/help-text`).
* A builder that writes the comments of ``arguments`` blocks into the
  inputs, outputs and name-value sections of the help text, so that
  MATLAB's ``help`` shows them and the two stay in step
  (:doc:`../user-guide/api-check`).
* Checking which lines MATLAB itself treats as "See also" lines.

MATLAB releases
---------------

Releases before R2024a for :confval:`matlab_version`, each with the naming
and callability rules MATLAB had then.
