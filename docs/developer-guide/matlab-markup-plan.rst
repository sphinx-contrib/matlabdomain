Plan: MATLAB markup in help text
================================

Status: planned, not implemented yet (:doc:`roadmap`).

Spec: :doc:`matlab-markup-spec` (what MATLAB does, target behaviour,
deviations D3-D9, decisions Q1-Q8). Probe kit: MATLAB files run in
R2026b on 2026-11-06; step M0 moves them into the test suite.

Goal: a project sets ``matlab_docstring_format = "matlab"`` (or per file)
and its MATLAB help renders as MATLAB authors mean it: publishing markup
(bold, italic, monospaced, lists, preformatted and code blocks, links,
math, images, includes, titles, raw HTML/LaTeX opt-in) and
help conventions (H1, See also, Example, Note, class member lists,
name highlighting), with no docutils warnings from help text, without
MATLAB at build time.

Out of this plan: Live Code ``%[text]`` format, ``.mlx``, running code,
``Contents.m`` folder help (:doc:`roadmap`), Markdown help text, ``(R)``/``(TM)``
conversion (Q4). Parked: whole scripts as published documents (Q6),
quickstart format detection (Q7).

0. Decisions (maintainer, 2026-11-06)
-------------------------------------

+----------------------------+-----------------------------------------------+
| Topic                      | Decision                                      |
+============================+===============================================+
| Markup families            | publishing markup and help-text conventions;  |
|                            | not the Live Code format                      |
+----------------------------+-----------------------------------------------+
| Oracle                     | R2026b ``publish`` to XML and HTML, plus      |
|                            | ``help`` and ``doc`` output                   |
+----------------------------+-----------------------------------------------+
| Code                       | static only: code blocks are shown, never run |
+----------------------------+-----------------------------------------------+
| Raw ``<html>``/``<latex>`` | opt-in setting, off by default                |
+----------------------------+-----------------------------------------------+
| Selection                  | ``conf.py`` setting plus a per-file override  |
+----------------------------+-----------------------------------------------+
| Probe files                | moved into the test suite (M0)                |
+----------------------------+-----------------------------------------------+

Maintainer, 2026-11-07 (spec Section 3): Q1 drop the H1 name; Q2 name
as ``literal``; Q3 ``note`` admonition; Q4 no ``(R)``/``(TM)`` conversion; Q5
exact publish indentation (3-space help bodies become code blocks);
Q6 and Q7 parked; Q8 reST mode unchanged. No open questions. Decided
items go into the design documentation (:doc:`architecture`) when the
step that uses them starts.

1. Design summary
-----------------

- Settings: ``matlab_docstring_format`` (``"rst"`` default, ``"matlab"``),
  ``matlab_docstring_format_overrides`` (``{glob: format}``),
  ``:docstring-format:`` on auto directives, ``matlab_markup_raw`` (False).
- Parser keeps raw help lines next to today's docstring string (cache
  ``data_version`` +1).
- Documenter emits ``.. mat:helptext:: <reference>`` for MATLAB-format
  docstrings; the directive runs the markup parser and returns docutils
  nodes. Napoleon and ``autodoc-process-docstring`` hooks see only the
  placeholder line.
- New module ``sphinxcontrib/mat_markup.py`` (pure: raw lines in, nodes
  out; a small context object for name lookup and file access), directive
  in ``matlab.py``, documenter switch in ``mat_documenters.py``. No new
  runtime dependency.

2. Steps
--------

Each step ends with tests (100% line and branch coverage stays), the
Windows gate, and a commit on the ``matlab-markup`` branch.

M0: fixtures and the oracle
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Copy the probe sources into ``tests/roots/test_markup/src/`` (publish
  probes, help probes, the generated delimiter matrix) and a MATLAB
  script ``tests/markup/make_oracle.m`` (from the probe kit's ``runProbes.m``) that
  writes the publish XML into ``tests/markup/oracle/``. Commit the XML
  (small text; not the equation PNGs).
- A test helper turns the XML into a compact tree (``p``, ``b``, ``i``, ``tt``,
  ``a@href``, ``ul/ol/li``, ``pre``, ``code``, ``eq``, ``eqblock``, ``img@src``,
  ``html``, ``latex``, ``title``) and the parser's docutils output into the
  same tree, so tests compare MATLAB and matlabdomain directly.
- Expected-deviation list: the oracle cases where the spec deviates
  (D3-D9) are listed with the expected matlabdomain tree, so a change in
  MATLAB or in the parser shows up as a diff.
- Optional cross-release check: rerun ``make_oracle.m`` on R2024a and
  R2026a; record differences in the spec (one line if
  none).

Done when: the oracle XML and the tree helper are committed; the script
reruns cleanly on R2026b; every construct of spec Section 1 has an
oracle case.

M1: raw help lines in the parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``help_text`` and ``process_text_into_docstring`` return (or store) the raw
  lines too; every caller in ``mat_tree_sitter_parser.py`` (about 25
  sites: script, function, class, property, method, event, enumeration,
  name-value argument help) carries them to the object
  (``MatObject.help_lines``, tuple of str).
- Raw = leading whitespace removed, marker (``%``, ``%%``, ``%%%``) and the
  rest kept; ``%{ %}`` blocks as today (``help_text`` stops at ``{``).
- ``data_version`` +1. No output change: the reST path still uses
  ``docstring``.

Done when: unit tests show raw lines for every docstring kind (fixtures
of ``tests/roots/``); full test suite and docs build unchanged (byte
compare of a docs build before/after).

M2: the markup parser (publishing rules)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``mat_markup.parse(lines, ctx) -> list[nodes.Node]``:

  - line classification (spec 1.2), exact publish indentation (spec
    1.3, Q5), paragraphs; a body line ``%text``/``%<tab>text`` turns the
    rest into one code block; the H1 is exempt (D3);
  - blocks (spec 1.3, 2.3): paragraph, pre, code, lists, display math,
    titles → rubric, image/include/raw paragraphs recognised (rendered
    in M5; placeholder nodes here);
  - inline (spec 1.5-1.7, 2.4): anchors (D5), angle links (D6), bare
    URLs, inline math (D7), nested ``*``/``_``/``|``, empty pairs, link scheme
    allowlist; ``(R)``/``(TM)`` left as typed (D9).

- Pure function: no Sphinx app needed; ``ctx`` supplies the object name,
  member names and a resolver callback (returns a target or None).
- Tests: the M0 oracle (publish files give MATLAB's tree), the deviation
  list, the delimiter matrix, property-based tests
  (Hypothesis is not a dependency: a seeded random generator of marker
  strings instead) for "never raises, text round-trips"
  (``node.astext()`` keeps every non-marker character).

Done when: all oracle cases pass or are listed deviations; random input
never raises; parser timing on the gauntlet's 21,446 help texts recorded
(target: under 1 ms median per help text).

M3: settings, directive, documenters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Config values (spec 2.1) with validation (ConfigError on unknown
  formats, bad globs); ``:docstring-format:`` option on every auto
  directive (``mat:autofunction``, ``autoclass``, ``automethod``,
  ``autoattribute``, ``autoproperty``, ``autoscript``, ``autoenumeration``,
  ``autoevent``, ``automodule``/namespace, ``autoapp``, ...: whatever
  ``mat_documenters.py`` registers).
- Format chosen per object: directive option, then the last matching
  override glob for the object's file, then ``matlab_docstring_format``.
- ``add_content``: MATLAB format → one placeholder line, no
  ``matlab_auto_link`` pass; ``autodoc-process-docstring`` still fires.
- ``mat:helptext`` directive: looks the object up by reference, runs the
  parser, returns nodes; ``pending_xref`` resolution through the domain.
- Builders: HTML, singlehtml, LaTeX (and a PDF compile in CI if
  available), text, man; nested inline in ``literal`` checked in each.
- Napoleon on: a MATLAB-format docstring with ``Example:``/``Note:``/
  ``Returns:`` lines is not touched by napoleon (test).

Done when: a ``test_markup`` docs root builds ``-W`` with
``matlab_docstring_format = "matlab"``, with an override glob back to reST
for one file, and with the directive option; HTML snapshot tests for
each construct; reST-mode output byte-identical to before.

M4: help-convention layer
~~~~~~~~~~~~~~~~~~~~~~~~~

- Runs before the publish blocks; conventions found at any indentation
  (spec 2.5).
- H1 without the leading name (Q1), name highlighting as ``literal`` (Q2),
  Example sections, Note as ``note`` admonition (Q3), See also (``seealso``
  node, case-insensitive fallback lookup), class member lists (class
  docstrings: properties, methods, events, enumerations, functions),
  ``matlab_auto_link = "all"`` in text. reST mode untouched (Q8).
- Tests against ``out/help/*.txt`` (hotlinked ``help``) for which names
  MATLAB links and how it shows them; differences listed (See also
  ending at ``%%``).

Done when: ``helpFun``, ``helpClass``, ``helpEnum`` fixtures render with the
same links MATLAB makes (``help`` output), plus the spec's deviations.

M5: files and raw blocks
~~~~~~~~~~~~~~~~~~~~~~~~

- Images (``<<path>>``): resolution (D8), confinement to the project root,
  remote URLs, Sphinx image copy (check paths outside the Sphinx
  source directory are copied; else copy them ourselves into the build's
  ``_images`` through ``env.images``).
- Includes: resolution, confinement, encoding detection, size limit,
  ``.m`` highlighted, ``note_dependency`` (incremental build test: editing
  the included file rebuilds the page).
- Raw ``<html>``/``<latex>``: ``matlab_markup_raw`` on → ``raw`` nodes for the
  matching builder only (MATLAB drops HTML from LaTeX output and the
  reverse); off → dropped with a ``mat.markup`` warning.
- Security tests: ``..`` escape, absolute paths outside, symlink and
  junction out of the root (Windows can create both), ``javascript:``
  links, ``<html><script>`` with the setting off.

Done when: each case has a test; ``-W`` build of the fixture root clean
with the setting off and on.

M6: apidoc, docs, gauntlet
~~~~~~~~~~~~~~~~~~~~~~~~~~

- apidoc: pass ``:docstring-format:`` through when a generated page needs
  it (only if apidoc writes per-object options today; else nothing).
- quickstart: nothing (format detection parked, Q7).
- api-check: nothing new (markup errors are not API errors).
- Docs: ``docs/user-guide/help-text.rst`` gets a "MATLAB markup" section
  (settings, the construct table, deviations from publish with reasons,
  that 3-space help indentation means code blocks, security notes);
  ``docs/developer-guide/roadmap.rst`` (its help-text item); CHANGES
  entry; a demo page in the docs' own example project.
- Gauntlet: build mtex, fieldtrip, chebfun, eeglab, Psychtoolbox-3,
  vhlab-toolbox-matlab with ``"matlab"``; record docutils warning counts
  against reST mode (baseline 14,341) and new ``mat.markup`` warnings;
  count pages whose help body is mostly code blocks (Q5); spot-check 20
  pages per project against ``publish``/``help``.

Done when: docs build ``-W``; a gauntlet table (warnings before/after
per project, no new errors) is recorded with the change.

3. Parked
---------

- Q6: ``mat:autoscript`` option ``:publish:`` rendering every ``%%`` section
  of a script (titles, text through the markup parser, code as
  ``literal_block``, no output); oracle: the M0 publish XML (cells with
  ``mcode``).
- Q7: quickstart counts publish markers and reST roles in a project's
  help (the probe kit's ``survey_help.py`` logic) and proposes ``"matlab"``, ``"rst"``
  or an override glob.

4. Risks
--------

- **publish is P-code.** Rules come from probes only; a later release
  may differ. Mitigation: the oracle in M0, rerun per MATLAB release
  (add to the release routine with the Simulink formats page).
- **False positives in old help.** ``$Id$``, ``<describe ...>``, ``||f-r|``:
  deviations D6 and D7 handle the frequent ones (``f(R)`` is safe: no
  trademark conversion, D9); the gauntlet run in M6 finds the rest. The
  format is opt-in, per file.
- **Help-style indentation** (7,922 of 21,446 help texts) renders as
  code blocks under exact publish rules (Q5). Expected, documented;
  such projects stay on reST or reindent to 1 space. M6 counts them.
- **Hooks.** ``autodoc-process-docstring`` handlers see only the
  placeholder in MATLAB format; documented. If users need the raw text,
  add a separate event later (``mat-process-helptext``), not now.
- **Localized help words.** MATLAB matches ``See also``/``Note`` through its
  message catalog (translated in Japanese/Korean/Chinese installs);
  English only here.
- **Math.** MATLAB renders with its own LaTeX subset; MathJax and LaTeX
  accept more or differ slightly (text-mode commands). Content passes
  as typed.
