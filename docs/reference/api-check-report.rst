``matlab-api-check`` reports
============================

The ``matlab-api-check`` builder (:doc:`../user-guide/api-check`) writes two
files to its output folder, before it logs the findings, so ``-W`` cannot
lose them.

``api-check.txt``
-----------------

One line per finding, in the order of the path references::

   <file>:<line>: <severity>: <reference> (<MATLAB name>): <what is missing> [<rule>]

``<file>`` is the absolute path of the source file; ``:<line>`` is left out
for apps and for sidecar findings without a line. Sidecar docs have no
MATLAB name,
so ``(<MATLAB name>)`` is left out for them. Then a summary: the objects
checked per kind, the objects not
checked per reason, and the findings per rule and severity. When
:confval:`matlab_api_check_enabled` is ``False``, the summary says that
nothing was checked.

With :confval:`matlab_api_check_files` or
:confval:`matlab_api_check_files_from`, the report starts with a line for
each entry that selects no file::

   <entry>: error: matches no indexed file or sidecar doc: <reason> [selection]

(``ignored`` instead of ``error`` with
:confval:`matlab_api_check_ignore_unmatched`), and the summary has a line
``Selected: <n> of <total> files by <entries> entries, <unmatched>
matching no file`` (with `` (ignored)`` added likewise; after a line that
says so when the selection is empty); the files not selected are counted
as ``not selected``. Without a selection, the report is as before. The
worked example's report, with the paths shortened:

.. literalinclude:: ../../examples/apidoc/api-check.txt
   :language: text

``api-check.json``
------------------

The same information for tools. It contains no absolute paths, so it is
identical on every system.

``summary``
   ``enabled``
      :confval:`matlab_api_check_enabled`.
   ``rules``
      Rule name to the severity in effect.
   ``checked``
      Objects checked per kind: ``function``, ``class``, ``method``,
      ``property``, ``event``, ``script``, ``application``, ``sidecar``.
   ``not_checked``
      Objects not checked per reason: ``ignored``
      (:confval:`matlab_api_check_ignore_patterns`), ``hidden``
      (``Contents.m`` and the other special files, and ``Hidden`` classes;
      their members are not counted), ``unreadable``,
      ``not_parsed`` (parse failures); with a selection, also
      ``not_selected`` (files and sidecar docs; their members are not
      counted).
   ``selection``
      Only with a selection (:confval:`matlab_api_check_files`,
      :confval:`matlab_api_check_files_from`): ``entries`` (the normalized
      entries, without duplicates), ``selected`` (the number of files and
      sidecar docs selected), ``unmatched`` (a list of ``{"entry": ...,
      "reason": ...}``, one for each entry that selects no file) and
      ``ignore_unmatched`` (:confval:`matlab_api_check_ignore_unmatched`;
      when ``false``, any unmatched entry makes the exit status 1).
   ``findings``
      Rule name to ``{"error": n, "warning": n}``.
   ``errors``, ``warnings``
      The totals.
``findings``
   A list with one object per finding:

   ``reference``
      The path reference (a method or property: ``+pkg/Cls.m.method``).
   ``name``
      The MATLAB name, or ``null`` if MATLAB cannot call the file (and for
      sidecar docs).
   ``kind``
      ``function``, ``class``, ``method``, ``property``, ``event``,
      ``script``, ``application`` or ``sidecar``.
   ``rule``, ``severity``
      The rule and its severity (``error`` or ``warning``).
   ``line``
      The line of the declaration (1 for scripts), or ``null`` (apps); for
      ``sidecar-links``, the line of the link or image when it is known.
   ``message``
      What is missing.

The worked example's report:

.. literalinclude:: ../../examples/apidoc/api-check.json
   :language: json
   :lines: 1-60

(first 60 lines)

Exit status
-----------

1 when a finding has the severity ``error``, else 0. With ``-W``, any
finding fails the build.
