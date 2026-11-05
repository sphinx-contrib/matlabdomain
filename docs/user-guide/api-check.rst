Checking help text: ``matlab-api-check``
========================================

The ``matlab-api-check`` builder checks the help text of a MATLAB project:
that every function, class and public method has a description, that the
help describes its inputs, outputs and name-value arguments, and that it
has an example; and that every public property has a description. It
writes a report, logs each finding, and fails the build when it finds a
problem, so it can guard help text in CI.

Running it
----------

It is a Sphinx builder; the extension adds it. Run it on the Sphinx project
of your docs:

.. code-block:: console

   $ sphinx-build -b matlab-api-check docs docs/_build/api-check

It reads the pages like any builder; give it the ``-d`` folder of the HTML
build (``-d docs/_build/doctrees``) to avoid reading them twice. (If the two
builds use different options, such as ``-n`` for HTML only, Sphinx says the
configuration changed and reads the pages again; that is harmless.) Then it
checks every file the project indexes, whether a page documents it or not,
on every run. It writes no pages.

The worked example of :doc:`apidoc` gives this report (``api-check.txt``,
with the file paths shortened):

.. literalinclude:: ../../examples/apidoc/api-check.txt
   :language: text

The build exits with status 1, because some findings are errors.
``clamp`` passes: its help has ``Inputs:``, ``Outputs:`` and ``Example::``
sections.

.. literalinclude:: ../../examples/apidoc/src/utils/clamp.m
   :language: matlab

``lerp`` does not:

.. literalinclude:: ../../examples/apidoc/src/utils/lerp.m
   :language: matlab

What is checked
---------------

Every indexed object below the project root, minus
:confval:`matlab_api_check_ignore_patterns` (or only the objects of the
files :confval:`matlab_api_check_files` selects, see
`Checking selected files`_):

* functions, classes, scripts and apps (``.mlapp``);
* public methods: methods without ``Access = private``, ``protected`` or an
  access list, and not ``Hidden``, including static methods and
  constructors. ``get.``/``set.`` methods, converter methods with dotted
  names and abstract methods are not checked;
* public properties of classes: without ``Access`` (or, without it,
  ``GetAccess``) ``private``, ``protected`` or an access list, and not
  ``Hidden``; constant and dependent properties included.

Files below ``private/`` and files MATLAB cannot call are checked.
``Contents.m`` and the other special files, files that cannot be read and
files that cannot be parsed are counted as not checked. The function files
of a class folder ``@X/`` whose ``X.m`` is a ``classdef`` are methods; in an
old-style class folder they are functions (old-style classes are not
supported, see :doc:`documenting`).

With :confval:`matlab_src_sidecar_suffixes`, the :doc:`sidecar docs
<sidecars>` are checked too: that each is rendered, and that its relative
links and images exist.

The rules
---------

.. list-table::
   :header-rows: 1

   * - Rule
     - Default
     - Applies to
     - Passes when
   * - ``description``
     - error
     - functions, classes, scripts, apps
     - the first help line (MATLAB's H1 line) is not blank
   * - ``method-description``
     - error
     - methods
     - the same
   * - ``property-description``
     - warning
     - properties
     - the property has a comment: above it, after it on its line, or on
       the lines below it (the help that the documentation shows)
   * - ``inputs``
     - error
     - functions and methods with inputs
     - the help has an inputs section, or every input has a comment in an
       ``arguments`` block
   * - ``outputs``
     - error
     - functions and methods with outputs
     - the help has an outputs section, or every output has a comment in an
       ``arguments (Output)`` block
   * - ``name-value``
     - error
     - functions and methods with name-value arguments
     - the help has a name-value section, or every name-value argument has
       a comment in an ``arguments`` block
   * - ``example``
     - warning
     - functions, classes, scripts
     - the help has an example section
   * - ``method-example``
     - warning
     - methods, except constructors
     - the same
   * - ``sidecar-documented``
     - error
     - sidecar docs
     - a ``mat:autosidecar`` renders the sidecar doc, in a document that a
       toctree
       includes (or an ``:orphan:`` one)
   * - ``sidecar-links``
     - error
     - sidecar docs
     - every relative link (Markdown) and download points to a file, and
       every image exists, relative to the sidecar doc's folder

* Inputs are the named inputs, except ``~``, the object of a method that is
  neither static nor a constructor, and the structure that holds name-value
  arguments. ``varargin`` counts.
* Outputs are the named outputs; ``varargout`` counts. A constructor's
  output (the object) does not.
* Name-value arguments are the ``opts.Name`` entries of ``arguments``
  blocks. Name-value pairs that the code parses itself (``varargin`` with
  ``inputParser``) are not detected.
* ``sidecar-links`` looks at the sidecar docs as they were rendered, so one
  that no ``mat:autosidecar`` renders gets only a ``sidecar-documented``
  finding. Links in reST sidecar docs written as ```text <path>`_`` are not
  checked.

Comments in ``arguments`` blocks count as documentation, although MATLAB's
``help`` does not show them, and neither does the HTML documentation:

.. literalinclude:: ../src/+shapes/totalArea.m
   :language: matlab

Section headers
---------------

A section starts with a help line that begins with one of these labels, in
any letter case:

* **inputs:** ``Input``, ``Inputs``, ``Input(s)``, ``Input Arguments``,
  ``Input Parameters``, ``Arguments``, ``Parameters``, ``Params``,
  ``Required Inputs``, ``Required Arguments``, ``Optional Inputs``,
  ``Optional Arguments``, ``Optional Parameters``;
* **outputs:** ``Output``, ``Outputs``, ``Output(s)``, ``Output
  Arguments``, ``Output Parameters``, ``Returns``, ``Return Values``,
  ``Return Arguments``;
* **name-value:** ``Name-Value Arguments``, ``Name-Value Pairs``,
  ``Name-Value Pair Arguments``, ``Name-Value Parameters``, ``Name-Value
  Options`` (with ``-``, ``/``, a space or nothing between *name* and
  *value*; also with ``Optional`` before them), ``Options``, ``Optional
  Inputs``, ``Optional Arguments``, ``Optional Parameters``.
  ``Input Arguments (Name-Value Arguments)`` counts for inputs and
  name-value arguments;
* **example:** ``Example``, ``Examples``, ``Example(s)``, ``Example 1``
  (any number), ``Usage``, ``Example Usage``, ``Usage Example``, ``Usage
  Examples``; also a reST ``.. rubric:: Example`` (or ``Examples``,
  ``Usage``).

The last word of a label may also be singular or plural (``Parameter``,
``Return``, ``Option``, ``Name-Value Pair``).

The label is followed by one of:

* ``:`` and anything: ``Inputs: x - data``, ``Options::``, ``Input : x``;
* a short qualifier and a ``:`` that ends the line: ``Inputs (all
  optional):``, ``Parameters and their meaning:``;
* nothing: ``INPUTS`` alone on its line, or ``Parameters`` underlined
  with ``---``, ``===`` or ``~~~``.

Two cases are not headers: a lowercase label alone on a line right after a
line of text (a word of wrapped prose), and a label that is the name of one
of the function's arguments with text after its ``:`` (``input: the data``,
the entry of an argument named ``input``). The built-in labels were tuned
on the help of 14 open-source MATLAB projects.

With ``sphinx.ext.napoleon`` in ``extensions``, the headings that
``napoleon_custom_sections`` makes parameter or return sections count
too, so that the check and the rendered help agree:

.. code-block:: python

   napoleon_custom_sections = [
       ("Eingaben", "params_style"),  # an inputs section
       ("Ausgaben", "returns_style"),  # an outputs section
       ("Eingabe", "Eingaben"),  # an alias of the one above: inputs
       "Hinweise",  # a plain section: neither
   ]

The entries are read as Napoleon reads them, in order, the last one for a
heading winning. ``(heading, "params_style")`` is an inputs section and
``(heading, "returns_style")`` an outputs section; ``(heading, other)``
is what an earlier entry made ``other``. A plain heading, and an alias of
one of Napoleon's own sections (``("Ergebnis", "Returns")``) or of an
unknown one, adds nothing: write ``("Ergebnis", "returns_style")``
instead. The headings follow the rules above (any case, the same forms, the
same two exceptions) and are added to the built-in labels, which still
count and keep their meaning: ``("Outputs", "params_style")``, as
``sphinx-matlab-quickstart`` may write it, does not make ``Outputs`` an
inputs section. A ``params_style`` heading is not a name-value section: name-value
arguments need a name-value label or ``arguments``-block comments, as
before. Without Napoleon, ``napoleon_custom_sections`` does nothing.

Configuration
-------------

Four settings in ``conf.py``; changing them does not make Sphinx read the
pages again (:doc:`../reference/configuration`):

* :confval:`matlab_api_check_rules`: the severity of each rule:
  ``"error"``, ``"warning"`` or ``"ignore"``. The defaults are in the table
  above (the newer rules ``property-description``, ``example`` and
  ``method-example`` warn). The dictionary is merged over the defaults:

  .. code-block:: python

     matlab_api_check_rules = {
         "method-description": "warning",
         "name-value": "ignore",
         "example": "error",
     }

* :confval:`matlab_api_check_ignore_patterns`: objects not to check. Globs
  with the rules of :confval:`matlab_src_exclusion_patterns`, matched
  against the path references of files, of methods and properties
  (``+pkg/Cls.m.helper``) and of sidecar docs. Use them for generated code,
  examples and tests:

  .. code-block:: python

     matlab_api_check_ignore_patterns = [
         "**/generated/**",
         "examples/**",
         "+pkg/Legacy.m.*",
     ]

* :confval:`matlab_api_check_enabled` (default ``True``): ``False`` checks
  nothing; the reports say so. Useful to switch the check off in one
  configuration without removing the CI step.

* :confval:`matlab_api_check_files` (default ``None``, every file): the
  files to check; see `Checking selected files`_.

An unknown rule or severity is a configuration error.

Checking selected files
-----------------------

:confval:`matlab_api_check_files` checks only some files, such as the
files a pull request changes. The project is indexed and the pages are
read as before, so names resolve, links work and the documentation does
not change; only the check is narrower, and files that are not selected
are not parsed for it. Give it on the command line, separated by commas:

.. code-block:: console

   $ sphinx-build -b matlab-api-check -D matlab_api_check_files=+shapes/Circle.m,utils/ docs docs/_build/api-check

or in ``conf.py``, as a list:

.. code-block:: python

   matlab_api_check_files = ["+shapes/Circle.m", "utils/", "+pkg/**/*.m"]

* Entries are paths or glob patterns relative to
  :confval:`matlab_src_code_project_root`, with ``/`` and the rules of
  :confval:`matlab_src_include_patterns` (case-sensitive, ``**`` crosses
  folders). An entry that ends in ``/`` selects every file below that
  folder.
* They select files and sidecar docs; a selected ``classdef`` file is
  checked with its methods and properties. A class folder's method files
  are files of their own: ``@Shape/area.m`` checks that method only,
  ``@Shape/Shape.m`` the class and the methods written in it, and
  ``@Shape/`` all of them.
* :confval:`matlab_api_check_ignore_patterns` still apply, and selected
  ``Contents.m`` files are still not checked; the report counts them.
* ``[]`` (or an empty ``-D matlab_api_check_files=``) selects nothing:
  the reports say so, and the build passes. ``None``, the default,
  checks every file.
* An entry that selects no indexed file or sidecar doc (a typo, a deleted
  or excluded file, a path relative to another folder) is logged as an
  ``ERROR`` with the reason, listed in both reports, and makes the build
  exit with status 1, whatever the rule severities, so the check of a
  file that was asked for cannot pass silently.

Both reports count the files selected and the files not selected (``not
selected``) and list the entries that select nothing; ``api-check.json``
also lists every entry. See :doc:`../reference/api-check-report`.

In CI, pass the files a change touches. They must be relative to the
project root, exist and be indexed, so filter the list first. With Git,
for a project root ``src`` (``--relative`` leaves out other files and
strips ``src/``; ``--diff-filter=d`` leaves out deleted files):

.. code-block:: bash

   files=$(git diff --name-only --diff-filter=d --relative=src origin/main... \
       -- '*.m' '*.mlapp' ':!src/tests')
   sphinx-build -b matlab-api-check -D "matlab_api_check_files=$files" \
       docs docs/_build/api-check

Line breaks separate entries like commas. Leave out the folders that
:confval:`matlab_src_exclusion_patterns` excludes (``:!src/tests`` above),
and add the sidecar suffixes if you check sidecar docs. A file name with a
comma needs a list in ``conf.py``.

Findings and reports
--------------------

Each finding is logged at the line of the declaration (scripts at line 1,
apps without a line), as an ``ERROR`` for severity ``error`` and a
``WARNING`` for ``warning``, with the type ``mat.api_check``::

   path/to/file.m:12: ERROR: [sphinxcontrib-matlabdomain] +pkg/f.m (pkg.f): has no inputs section ... [inputs] [mat.api_check]

The output folder gets two reports, written before anything is logged:

* ``api-check.txt``: one line per finding, then a summary (above);
* ``api-check.json``: the same for tools, without absolute paths, so it is
  identical on every system (:doc:`../reference/api-check-report`).

Sphinx's last line counts the findings among its warnings ("build finished
with problems, 1 warning"). A run without errors ends with "The MATLAB API
check passed; see .../api-check.txt".

In CI
-----

The exit status is 1 when a finding has severity ``error`` or an entry of
:confval:`matlab_api_check_files` selects no file, and 0 otherwise. With
``-W``, any finding fails the build, like any warning. A CI step:

.. code-block:: console

   $ sphinx-build -b matlab-api-check -d docs/_build/doctrees docs docs/_build/api-check

To adopt the check on an existing project, start with the rules that pass,
set the others to ``"warning"``, and tighten them as the help improves.
Keep ``api-check.json`` as a build artifact to follow the counts.
