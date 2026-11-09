Roadmap
=======

Possible later work. None of it is available yet.

More file types
---------------

The file-type registry (:doc:`architecture`) is the place for new MATLAB
file types. Simulink models, libraries and subsystem files are supported
(:doc:`../user-guide/simulink`). Planned:

* Simscape components (``.ssc``, text);
* live scripts (``.mlx``): first a check of what they would add next to
  ``.m`` files and apps (``.mlapp``).

One handler owns one extension, as for ``.slx``, ``.mdl`` and exported
Simulink ``.xml`` files.

``scmd apidoc``
---------------

* ``Contents.m`` as the description of its folder, as MATLAB's ``help
  folder`` shows it (before the README introduction of
  :doc:`../user-guide/sidecars`).

Running the generator inside ``sphinx-build`` (as ``sphinx.ext.apidoc``
does) is not planned: the build would write into the source folder, which
races with other builds of the same folder and loops ``sphinx-autobuild``.
The command reads ``conf.py`` instead (:doc:`../user-guide/apidoc`).

Help text
---------

* A mode that uses MATLAB markup instead of parsing help text as
  reStructuredText (:doc:`../user-guide/help-text`). The
  :doc:`specification <matlab-markup-spec>` and the
  :doc:`plan <matlab-markup-plan>` are written; the work has not started.
* A builder that writes the comments of ``arguments`` blocks into the
  inputs, outputs and name-value sections of the help text, so that
  MATLAB's ``help`` shows them and the two stay in step
  (:doc:`../user-guide/api-check`).

MATLAB releases
---------------

Releases before R2024a for :confval:`matlab_version`, each with the naming
and callability rules MATLAB had then.

MATLAB documentation window
---------------------------

A ``matlab-help`` builder that writes the site as MATLAB custom
documentation (``info.xml``, ``helptoc.xml``), so that it shows under
Supplemental Software in MATLAB's documentation, with its own search there.
One search over MathWorks pages and the site's pages is not possible. The
:doc:`specification <matlab-help-spec>` and the
:doc:`plan <matlab-help-plan>` are written; the work has not started.

.. toctree::
   :hidden:

   matlab-markup-spec
   matlab-markup-plan
   matlab-help-spec
   matlab-help-plan
