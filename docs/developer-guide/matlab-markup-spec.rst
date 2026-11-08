Specification: MATLAB markup in help text (docstrings)
======================================================

Status: planned, not implemented yet (:doc:`roadmap`).

Scope: a second help-text format for ``sphinxcontrib-matlabdomain``, next to
reST: MATLAB's **publishing markup** (Editor PUBLISH tab) plus MATLAB's
**help-text conventions** (H1 line, See also, class member lists, links),
rendered by Sphinx without MATLAB. Plan: :doc:`matlab-markup-plan`.
Motivation: help text that is not reST gave 14,341 docutils warnings in
14 gauntlet projects (:doc:`testing`).

Not in scope: the plain-text Live Code format (``%[text]``, R2025a+; MATLAB
reads it in ``matlab.internal.help.LiveCodeHelpParser``), ``.mlx``, running
code (publish's ``evalCode``, ``snapnow``, figures, command-window output),
publish options (image sizes, output formats, stylesheets).

Evidence (2026-11-06, MATLAB R2026b 26.2.0.3386108):

- Probe kit (plan step M0 moves it into the test suite): ``publish/pubAll.m`` (every construct of the
  MathWorks "Publishing Markup" page), ``publish/pubEdge.m`` and
  ``publish/pubMore.m`` (thresholds, lists, links, includes, titles),
  ``makeDelims.m`` (writes ``publish/pubDelims.m``: every ASCII punctuation
  character before an opening and after a closing marker),
  ``publish/pubIndented.m`` (help-style indentation under publish),
  ``publish/pubFunction.m`` (markup in function help), ``helpprobe/``
  (function, class, enumeration, script, ``Contents.m``). ``runProbes.m``
  publishes to XML, HTML and LaTeX with ``evalCode=false`` and captures
  ``help`` and ``doc`` (``matlab.internal.help.helpwin.help2json``) output.
  ``summarize.py`` turns the XML into ``out/<file>.cells.txt`` (one block per
  cell): the oracle quoted below.
- MATLAB's own help code, readable ``.m`` in R2026b
  ``toolbox/matlab/helptools/+matlab/+internal/+help/``: ``getMFileHelpText``,
  ``sanitizeHelpComments``, ``HelpSections``, ``highlightHelp``,
  ``@helpProcess/hotlinkHelp``, ``fixsymbols``, ``ParsedSeeAlso``,
  ``private/seeAlsoPattern``. ``publish`` itself is P-code.
- Survey of the gauntlet help text (``survey_help.py`` in the probe kit;
  file-level help of 21,446 files in 14
  projects; regexes approximate the rules below).

Only R2026b was probed. Publishing markup is old and stable; other
releases are not checked (plan M0 keeps the probe kit runnable on any
release).

1. What MATLAB does
-------------------

1.1 Where markup applies
~~~~~~~~~~~~~~~~~~~~~~~~

- ``publish`` interprets markup only in the comment block **directly after
  a section break** (``%%``). Comments after code in the same section are
  code (``pubAll`` cells 27-28). A function's help text is code too:
  ``publish(pubFunction.m)`` lists the help block as code; only a ``%%``
  section inside the body gets markup (``pubFunction.cells.txt``).
- ``help`` and ``doc`` **never** interpret publishing markup: ``*bold*``,
  ``|mono|``, ``$x^2$``, ``* bullet`` show as typed (``out/help/*.txt``,
  ``*.doc.html``). ``doc`` HTML-escapes the help text (``fixsymbols``) and keeps
  only ``<a href>`` anchors.
- So markup in help text is this extension's choice, not MATLAB
  behaviour. It is readable as plain text in ``help``, which is why it fits.

1.2 Lines
~~~~~~~~~

+-------------------------------------+-------------------------------------+
| Line                                | publish                             |
+=====================================+=====================================+
| ``%% Title``, ``%%``                | section break; title optional,      |
|                                     | trimmed (``%%   Title`` →           |
|                                     | ``Title``)                          |
+-------------------------------------+-------------------------------------+
| ``%%% Title``                       | title without a new code cell (same |
|                                     | heading in the output)              |
+-------------------------------------+-------------------------------------+
| ``%%Title``, ``%%<tab>Title``       | not a break: an ordinary comment    |
|                                     | (cell 19 of ``pubEdge``, cell 13 of |
|                                     | ``pubMore``)                        |
+-------------------------------------+-------------------------------------+
| ``% text``                          | markup text line                    |
+-------------------------------------+-------------------------------------+
| ``%`` or ``%`` + spaces only        | blank: ends a paragraph (``%`` too) |
+-------------------------------------+-------------------------------------+
| ``%text`` (no space),               | ends the markup block; it and the   |
| ``%<tab>text``                      | rest of the section are code        |
|                                     | (``pubAll`` cells 12, 33)           |
+-------------------------------------+-------------------------------------+
| ``%{ ... %}``                       | code                                |
+-------------------------------------+-------------------------------------+

A paragraph's lines are joined with one space.

1.3 Blocks: chosen by the first line of a paragraph
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Spaces after ``%`` on the paragraph's first line (``pubEdge`` cell 4,
``pubAll`` cells 9-12):

========= ================================= ==================================
Spaces    Block                             Leading spaces removed per line
========= ================================= ==================================
1         paragraph                         all (lines are joined)
2         preformatted (``<pre>``)          2
3         sample code (MATLAB highlighting) up to 3 (shallower lines lose all)
4 or more preformatted                      2 (``%    four`` → ``four``)
========= ================================= ==================================

- Later lines of the paragraph follow the first line's block, whatever
  their indentation: a 4-space line under a 1-space line joins the
  paragraph; a 2-space line under a code line stays code (``pubEdge`` cells
  5, 7; ``pubIndented`` cell 2).
- A blank comment line ends the block: one code or pre block with a blank
  line inside becomes two blocks.
- No markup inside pre and code (``pubMore`` cell 15).
- Help-style indentation (``%   text``, 3 spaces) is **sample code** under
  publish (``pubIndented`` cell 1). 7,922 of 21,446 gauntlet help texts use
  it. Decided (Q5): matlabdomain follows publish exactly, so their bodies
  render as code blocks; only help conventions (2.5) are found at any
  indentation.

1.4 Lists
~~~~~~~~~

- ``% * item`` bulleted, ``% # item`` numbered. Marker, then one space.
- A list must start a paragraph (blank line before it, or the first line
  after the title). ``Text then list:`` followed by ``% * a`` joins one
  paragraph (``pubAll`` cell 6).
- A line without a marker continues the item (indented or not).
- One level only: ``%   * inner`` continues the item as text; a ``#``
  line inside a bulleted list continues the item (no mixed lists).
- Numbered items separated by blank lines are separate lists, each
  starting at 1 (``pubMore`` cell 6).
- Not lists: ``%  *`` (2 spaces: pre), ``% *x``, ``% #x``, ``% - x``, ``% + x``,
  ``% 1. x`` (text).
- Inline markup works in items.

1.5 Inline formatting
~~~~~~~~~~~~~~~~~~~~~

``*bold*`` → ``<b>``, ``_italic_`` → ``<i>``, ``|mono|`` → ``<tt>``.

- Opening marker: at the start of the paragraph, after whitespace, after
  ``(``, or after another marker (``*``, ``_``, ``|``); followed by a non-space.
  Any other preceding character (``"``, ``'``, ``[``, ``{``, ``-``, ``/``, letters,
  digits, ``é``) leaves it literal (``pubDelims``, ``tinyProbe``).
- Closing marker: after a non-space, and **not followed by an ASCII
  letter or digit** (any punctuation, ``_``, ``é``, space or end is fine).
  ``*a*b*`` → ``<b>a*b</b>``; ``*m*x ... d*`` closes at ``d*``.
- Scope: one paragraph (or list item, or title); may span joined lines.
- Nesting: any order (``*_x_*``, ``_*x*_``, ``|*x*|``); markup, links and
  trademarks work inside ``|mono|``.
- Math inside emphasis stays literal (``*$x$*`` → ``<b>$x$</b>``).
- No escapes: ``\*`` is two characters; ``\*x\*`` can still match.
- Empty pairs vanish: ``**``, ``__``, ``||`` are deleted.
- ``snake_case``, ``2*3*4``, ``a*b*c``, ``x|y|z`` stay literal by the rules above.

Trademarks: ``(R)`` → ®, ``(TM)`` → ™ directly after a non-space
(``MATLAB(R).`` works; ``MATLAB (R)``, ``(R) alone``, ``x(R)y``, ``(r)``, ``(tm)``
do not). In the gauntlet, 97 help matches, about 5 real (``MATLAB(R)``,
``Nervus(TM)``); the rest are calls (``f(R)``, ``rotate(R)``, ``CYLINDER(R)``).
matlabdomain does not convert them (D9, Q4): authors write ® and ™.

1.6 Links
~~~~~~~~~

- ``<target text>`` → link with that text; ``<target>`` → the target as text.
  Text may hold spaces and markup; the link may span joined lines
  (``pubEdge`` cell 10).
- **Any** ``<word ...>`` is a link: ``<b>`` → ``href="b"``, ``<a href="x">`` →
  ``href="a"`` with text ``href="x"``, ``<not a link>`` → ``href="not"``. Only
  ``<`` followed by a space stays text (``a < b > c``).
- Targets: any scheme (``https:``, ``ftp:``, ``mailto:``, ``file:``,
  ``matlab:...``), relative (``otherPage.html``), bare email (no ``mailto:``
  added).
- Bare URLs in text are links: ``http://``, ``https://``, ``ftp://``,
  ``mailto:``; not ``www.``; a trailing ``.`` is not part of the URL.
- ``matlab:`` links run code in MATLAB's viewer only.

1.7 Math
~~~~~~~~

- Inline: ``$...$``; the opener is followed by a non-space, the closer
  preceded by one. ``$5 and $6 ... end $y$`` is **one** formula from ``$5``
  to ``$y$``; ``$x$y$z$`` is one formula. Content is LaTeX math mode, as
  typed (``_``, ``*``, ``|`` inside are not markup).
- Display: a paragraph that is exactly ``$$...$$`` (may span lines). ``$$``
  with other text in the paragraph becomes inline (``$$a$$`` → ``$a$``;
  two ``$$`` lines in one paragraph → two inline formulas).
- Output: PNG images (HTML), ``$...$`` (LaTeX). Invalid LaTeX gives an
  error box (``$10, cost $20$``).
- Survey: 159 help texts with inline ``$...$``; 28 only RCS keywords
  (``$Id$``, fieldtrip), which publish would turn into math. See D7.

1.8 Images
~~~~~~~~~~

- ``<<path>>`` alone in its paragraph → image. Anything else in the
  paragraph (text before or after, even on the next line) breaks it into
  a junk link (``pubEdge`` cells 11-12).
- Path: relative to the **output** folder, or a URL.

1.9 Include
~~~~~~~~~~~

- ``<include>file</include>`` alone in its paragraph → the file's content:
  ``.m`` as highlighted code, others as preformatted text (escaped).
- Inline it is a junk link.
- Resolution (probe, contradicts the docs page, which says "relative to
  the published file"): the current folder, then the MATLAB path. Not
  relative to the file (``sub/inc2.txt`` next to the file fails), no ``..``.
- A missing file gives an error box.

1.10 Raw HTML and LaTeX
~~~~~~~~~~~~~~~~~~~~~~~

- A paragraph that starts with ``<html>`` and ends with ``</html>`` passes
  its content raw to HTML output and is dropped from LaTeX output.
  ``<latex>...</latex>`` likewise for LaTeX only. A blank line inside, or
  text before the tag in the paragraph, breaks it into junk links
  (``pubEdge`` cells 16-17).
- Inline HTML is not supported (it becomes links, Section 1.6).

1.11 Titles
~~~~~~~~~~~

- Inline markup (formatting, math, links) works in section titles.
- First section with a title and only text: document title (``h1``);
  others ``h2``; a contents list of titles.

1.12 Help-text conventions (``help``, ``doc``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

From the R2026b help code and ``out/help/``:

- **Help block**: the first contiguous ``%`` lines at the top of the file,
  else the block right after the ``function``/``classdef`` line (an
  ``arguments`` block may come first). Ends at the first non-``%`` line.
  ``%%`` lines are part of it (``sanitizeHelpComments`` replaces
  ``^\s*%%?`` by one space). matlabdomain's ``help_text`` already follows
  this.
- **H1 line**: the first line, ``NAME  summary`` by convention. ``lookfor``
  and the Files panel use it.
- **Name highlighting**: whole-word occurrences of the topic's name, in
  upper case or its own case, become the name in its own case, bold in
  ``help`` (``<strong>``), ``<span class="helptopic">`` in ``doc``
  (``HELPFUN`` → **helpFun**; not ``helpFunX``, not inside links).
- **Syntax paragraphs**: a paragraph whose first line is
  ``[out =] NAME(args)`` or ``NAME ARG`` (``HelpSections.functionPattern``).
  Used for hotlinking order only; shown as typed.
- **Example**: a paragraph whose first line starts with ``example``
  (any case, ``Examples``, ``Example 2``); later paragraphs belong to it
  until another kind starts.
- **Note**: a paragraph starting ``Note`` (optional ``:``).
- **See also**: a paragraph starting ``See also`` (optional ``:``), possibly
  the last line of the last paragraph. Names are hotlinked when MATLAB
  finds them (``PLUS`` → ``plus``, ``helpClass.doThis`` →
  ``helpClass/doThis``, ``DOTHAT`` → ``doThat`` in a method); unknown names
  stay as written (``NOTAFUNCTION``). The paragraph runs to the next blank
  line: in ``helpFun``, the ``%%`` line after See also was linked word by
  word. In ``doc``, See also moves to a footer.
- **Class member lists** (class help only): a paragraph headed
  ``<ClassName> Properties:`` / ``Methods:`` / ``Events:`` / ``Enumerations:`` /
  ``Functions:`` (optional namespace prefix); each ``name - text`` line links
  ``name`` to the member.
- **``Contents.m``** (folder help): ``name - text`` lines link ``name``. Folder
  help is a separate roadmap item (:doc:`roadmap`), not this spec.
- **Links**: ``<a href="...">text</a>`` anchors (usually ``matlab:`` commands:
  ``web(...)``, ``help x``, ``doc x``); bare ``\w{2,}://\S*`` URLs become
  ``matlab:web`` links. ``doc`` turns ``matlab:help`` into ``matlab:helpwin``.
- **Member help**: properties, events, enumeration members: comment
  lines above the definition win over a trailing comment; first line
  convention ``name - summary``.

Survey (file-level help, 21,446 files): See also 5,777; Example 1,591;
Note 859; bare URLs 1,125; ``%% Title`` 811 (mtex 571); ``|mono|`` 644;
``*bold*`` 560; angle links 133; ``<a href>`` 17; class member lists 201;
reST roles 299 and :literal:`\``x`\`` 405 (matpower, matnwb: these projects
stay reST).

2. Target behaviour in matlabdomain
-----------------------------------

2.1 Selecting the format
~~~~~~~~~~~~~~~~~~~~~~~~

- ``matlab_docstring_format``: ``"rst"`` (default, today's behaviour) or
  ``"matlab"``.
- ``matlab_docstring_format_overrides``: ``{glob: format}``; globs match the
  file's path reference (relative to ``matlab_src_code_project_root``,
  case-sensitive, Sphinx ``Matcher`` rules, like
  ``matlab_src_include_patterns``); the last matching glob wins.
- Auto directives get ``:docstring-format: rst|matlab``, which wins over
  both.
- One format per object; class and member docstrings follow their file.
- Unknown values: a config error at build start.

2.2 Pipeline
~~~~~~~~~~~~

1. **Raw help lines.** The parser keeps, for every docstring it extracts
   (``help_text``, ``process_text_into_docstring`` and their callers), the
   raw comment lines: leading whitespace removed, the ``%``/``%%``/``%%%``
   marker and everything after it kept. Today's ``docstring`` string is
   unchanged. Stored on the objects (index cache ``data_version`` +1).
2. **Placeholder.** For a ``"matlab"`` docstring the documenter emits one
   line, ``.. mat:helptext::`` with the object's reference as argument,
   instead of the docstring lines. ``autodoc-process-docstring`` still
   fires (with that line), so napoleon and user hooks see no MATLAB
   text and cannot mangle it. ``matlab_auto_link`` is not applied to it
   (the parser links instead, 2.4).
3. **Directive.** ``mat:helptext`` fetches the raw lines from the index and
   runs the **markup parser**, which returns docutils nodes directly (no
   reST round trip: reST cannot nest ``**_x_**``, and escaping arbitrary
   help text is fragile).
4. **Parser stages:** help-convention layer (2.5) on the paragraph list,
   then publishing blocks (2.3), then inline markup (2.4).

2.3 Blocks (publish rules plus deviations)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mapping:

+------------------------------------+---------------------------------------+
| MATLAB                             | docutils / Sphinx node                |
+====================================+=======================================+
| ``%% Title``, ``%%% Title``        | ``rubric`` (inline markup kept);      |
|                                    | sections are not allowed inside       |
|                                    | directive content                     |
+------------------------------------+---------------------------------------+
| ``%%`` without title               | paragraph break                       |
+------------------------------------+---------------------------------------+
| paragraph                          | ``paragraph``                         |
+------------------------------------+---------------------------------------+
| ``*`` list                         | ``bullet_list`` / ``list_item`` /     |
|                                    | ``paragraph``                         |
+------------------------------------+---------------------------------------+
| ``#`` list                         | ``enumerated_list`` (``arabic``,      |
|                                    | start 1)                              |
+------------------------------------+---------------------------------------+
| preformatted                       | ``literal_block`` (no highlighting:   |
|                                    | ``language="none"``)                  |
+------------------------------------+---------------------------------------+
| sample code                        | ``literal_block``                     |
|                                    | ``language="matlab"``                 |
+------------------------------------+---------------------------------------+
| ``$$...$$`` paragraph              | ``math_block``                        |
+------------------------------------+---------------------------------------+
| ``<<img>>`` paragraph              | ``image`` (2.6)                       |
+------------------------------------+---------------------------------------+
| ``<include>`` paragraph            | ``literal_block``, ``matlab`` for     |
|                                    | ``.m``, else ``none`` (2.6)           |
+------------------------------------+---------------------------------------+
| ``<html>`` / ``<latex>`` paragraph | ``raw`` ``format="html"`` /           |
|                                    | ``"latex"`` if ``matlab_markup_raw``  |
|                                    | is true; else dropped with a warning  |
|                                    | (2.7)                                 |
+------------------------------------+---------------------------------------+

Indentation follows publish exactly (Q5): spaces after ``%`` on a
paragraph's first line, 1 → text, 2 → preformatted, 3 → code, 4 or more
→ preformatted, with publish's stripping (1.3). A ``%text`` or
``%<tab>text`` body line ends the markup, as in publish: it and the rest of
the help block become one code block (``%`` kept).

Deviations from publish (all needed because help text is not a publish
section):

- **D1** withdrawn (was relative indentation; Q5).
- **D2** withdrawn (was no-space and tab lines as text; follows Q5).
- **D3 H1 is its own paragraph** (it never joins the next line, and a
  ``%NAME ...`` H1 without a space does not end the markup).
- **D4 Everything is markup.** The whole help block is read as one
  publish text section; there is no "code after the comment".

2.4 Inline markup
~~~~~~~~~~~~~~~~~

Order inside a paragraph, list item or title (each step leaves already
made nodes alone):

1. ``<a href="URL">text</a>`` anchors (help convention, D5).
2. ``<target text>`` / ``<target>`` links, only when ``target`` has a URL
   scheme (``\w+:``), starts with ``/``, ``./``, ``../`` or ``#``, or contains a ``.``
   or ``/`` (D6); otherwise the angle text stays literal (no junk links
   from ``<b>`` or ``<describe ...>``).
3. Bare URLs (``http``, ``https``, ``ftp``, ``ftps``, ``mailto:``), trailing
   ``.``, ``,``, ``;``, ``:``, ``)`` excluded.
4. Inline math ``$...$`` (publish pairing). Exception D7: RCS keywords
   (``$Id$``, ``$Revision$``, ``$Date$``, ``$Author$``, ``$Log$``, ``$Header$``,
   ``$Source$``, ``$RCSfile$``, ``$Name$``, ``$Locker$``, ``$State$``, ``$Rev$``, with
   or without ``: value``) stay text.
5. ``*`` / ``_`` / ``|`` with the opener/closer rules of 1.5, nested;
   ``|...|`` → ``literal`` (children kept), ``*`` → ``strong``, ``_`` → ``emphasis``;
   empty pairs deleted.
6. Name highlighting and member/See-also linking (2.5).

``(R)`` and ``(TM)`` stay as typed (D9, Q4).

Link targets:

+-------------------------------------+-------------------------------------+
| Target                              | Node                                |
+=====================================+=====================================+
| ``http(s)``, ``ftp(s)``,            | ``reference`` ``refuri``            |
| ``mailto:``                         |                                     |
+-------------------------------------+-------------------------------------+
| relative path, ``#anchor``          | ``reference`` ``refuri`` as written |
+-------------------------------------+-------------------------------------+
| ``matlab:help X``,                  | ``pending_xref`` (domain ``mat``,   |
| ``matlab:doc X``,                   | ``obj``, target ``X``, lookup as    |
| ``matlab:helpwin X``,               | ``_find_link``); unresolved: the    |
| ``matlab:doc('X')``                 | text, no link                       |
+-------------------------------------+-------------------------------------+
| ``matlab:web URL``,                 | ``reference`` to ``URL`` (if its    |
| ``matlab:web('URL')``               | scheme is allowed)                  |
+-------------------------------------+-------------------------------------+
| any other ``matlab:`` command       | the text, no link; info log once    |
|                                     | per docstring                       |
+-------------------------------------+-------------------------------------+
| other schemes (``javascript:``,     | the text, no link; warning          |
| ``data:``, ``vbscript:``, ``file:`` |                                     |
| ...)                                |                                     |
+-------------------------------------+-------------------------------------+

2.5 Help-convention layer
~~~~~~~~~~~~~~~~~~~~~~~~~

Runs before the publish blocks. Conventions are recognised at any
indentation (as MATLAB's ``help`` does); their paragraphs are not publish
blocks.

- **H1**: the first line. Leading ``NAME``, ``NAME -``, ``NAME:`` (the object's
  name, any case) is dropped: the signature already shows it (Q1).
- **Name highlighting**: like ``highlightHelp`` (whole word, upper or own
  case, not inside links or code): the name in its own case as a
  ``literal`` node (Q2).
- **Example**: a paragraph whose first line starts with ``example`` (any
  case) → ``rubric`` with that line; the paragraph's other lines and the
  following paragraphs indented deeper than the title line → one code
  block each (``matlab``, common indentation removed); a paragraph at the
  title's indentation or less ends the example. Needed: help writes
  ``Example:`` then indented code without a blank line, which publish
  would join into one paragraph (or, at 4+ spaces, make preformatted).
- **Note**: a ``Note`` / ``Note:`` paragraph → ``note`` admonition (Q3); its
  text goes through inline markup.
- **See also**: → ``seealso`` node (Sphinx ``addnodes.seealso``). Names are
  split on commas and whitespace, a trailing ``.`` dropped, each resolved
  like today's ``auto_link_see_also`` (``_find_link``, folder-relative), then
  (new) case-insensitively like MATLAB (``PLUS`` → ``plus``); found → ``pending_xref``
  showing the found name; ambiguous → today's warning; not found → text.
  Ends at the next blank line or ``%%`` line (unlike MATLAB, 1.12).
- **Class member lists** (class docstrings): rubric with the heading,
  then a definition list ``name`` → text; ``name`` resolved among the
  class's members (``:mat:attr:``, ``:mat:meth:``, events, enumeration
  members); unknown names stay text.
- **``matlab_auto_link = "all"``**: known MATLAB names in paragraph text
  (not in literals, code or links) are linked, as today in reST mode.
- Syntax paragraphs: no special node.

2.6 Files: images and includes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Paths resolve relative to the documented file's folder, then the
  project root ``matlab_src_code_project_root`` (D8: MATLAB uses the
  output folder for images and the current folder/path for includes;
  neither exists in a Sphinx build).
- The resolved path must stay inside the project root (no ``..`` escape,
  symlinks resolved); else a warning and nothing is rendered.
- Images: ``image`` node; Sphinx copies the file into ``_images/``. Remote
  ``http(s)`` images are allowed as remote URIs.
- Includes: read with the file's encoding detection (``mat_classify``);
  size limit 1 MiB; ``env.note_dependency`` so a change rebuilds the page.

2.7 Warnings
~~~~~~~~~~~~

Type ``mat``, subtype ``markup``: raw block dropped, path outside the source
root, missing image/include, disallowed link scheme. Suppressible with
``suppress_warnings = ["mat.markup"]``. Markup that does not match (an
unclosed ``*``) is text, as in MATLAB: no warning.

2.8 Security
~~~~~~~~~~~~

- No code runs (no ``evalCode``, no ``matlab:`` command, no ``snapnow``).
- Raw HTML/LaTeX off by default (``matlab_markup_raw = False``); it is
  author-controlled source, but turning it on is an explicit choice for
  sites that render third-party code.
- Link scheme allowlist (2.4); ``javascript:`` and friends never become
  links.
- Paths confined to the project root (2.6).
- Text is never passed to reST or HTML unescaped: the parser builds
  ``Text`` nodes.

2.9 Builders
~~~~~~~~~~~~

HTML (MathJax for math), LaTeX/PDF (math native; ``raw latex`` only there),
text, man, singlehtml. Nested inline nodes inside ``literal`` (``|*x*|``)
must render in each; not yet checked (plan M3).

3. Decisions
------------

Maintainer, 2026-11-07:

+----+-----------------------------------+-------------------------------------+
| Id | Topic                             | Decision                            |
+====+===================================+=====================================+
| Q1 | H1 name                           | drop the leading name (the          |
|    |                                   | signature shows it;                 |
|    |                                   | ``LiveCodeHelpParser.splitPurpose`` |
|    |                                   | drops it too)                       |
+----+-----------------------------------+-------------------------------------+
| Q2 | Name highlighting                 | the name in its own case as a       |
|    |                                   | ``literal`` node                    |
+----+-----------------------------------+-------------------------------------+
| Q3 | ``Note:`` paragraphs              | ``note`` admonition                 |
+----+-----------------------------------+-------------------------------------+
| Q4 | ``(R)``, ``(TM)``                 | not converted (D9): 92 of 97        |
|    |                                   | gauntlet matches are calls such as  |
|    |                                   | ``f(R)``; authors write ® and ™     |
+----+-----------------------------------+-------------------------------------+
| Q5 | Indentation                       | exact publish rules (1.3): 3-space  |
|    |                                   | help bodies render as code blocks;  |
|    |                                   | help conventions (2.5) still found  |
|    |                                   | at any indentation                  |
+----+-----------------------------------+-------------------------------------+
| Q6 | Whole scripts as published        | parked                              |
|    | documents (``:publish:`` on       |                                     |
|    | ``mat:autoscript``)               |                                     |
+----+-----------------------------------+-------------------------------------+
| Q7 | quickstart proposes the format    | parked                              |
|    | from a survey                     |                                     |
+----+-----------------------------------+-------------------------------------+
| Q8 | Help conventions in reST mode     | no; reST mode stays as is           |
+----+-----------------------------------+-------------------------------------+

D9 (from Q4): ``(R)`` and ``(TM)`` stay as typed.
