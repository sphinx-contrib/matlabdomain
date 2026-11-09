Glossary
========

This page explains Sphinx terms used in these docs. It covers the terms in
the `Sphinx glossary <https://www.sphinx-doc.org/en/master/glossary.html>`_
in different words and adds a few terms useful to MATLAB users. The Sphinx
glossary is authoritative; consult it when these descriptions differ.

The dotted underline marks a link to a definition. On this HTML site, a
tooltip can preview the definition. Select the link to read the full entry,
including when tooltips are unavailable.

.. glossary::
   :sorted:

   builder
      The part of Sphinx that produces an output or performs a check. The
      HTML builder writes web pages; ``matlab-api-check`` checks MATLAB help.

   configuration directory
      The folder containing ``conf.py``. It is normally the source directory,
      but the ``-c`` build option can select a different folder.

   cross-reference
      A link to a documented item or location, such as a function, page,
      section or glossary entry. A role can create the link by name.

   directive
      A reStructuredText instruction for a block of content. For example,
      ``.. mat:autofunction:: times_two`` requests documentation for a MATLAB
      function. A directive can take options and content below its first line.

   Docutils
      The Python tools that parse reStructuredText. Sphinx uses Docutils and
      adds its own directives, roles and build features.

   doctree
      Sphinx's in-memory tree of nodes for a parsed document. Extensions can
      inspect or change the tree before a builder writes the output.

   document name
      A source document's path relative to the source directory, without its
      filename extension, using forward slashes on every operating system.
      For example, ``getting-started/quickstart`` names a page in this site.

   domain
      A group of directives and roles for related objects. The ``mat`` domain
      describes and links MATLAB objects; ``py`` does the same for Python.

   environment
      Sphinx's stored information about the documents in a project. It helps
      Sphinx resolve links and avoid rereading unchanged source files.

   extension
      A Python package or module that changes or adds Sphinx behavior. This
      package adds the ``mat`` domain; ``sphinx-tippy`` adds link previews.

   master document
   root document
      The top-level source document, usually ``index.rst``. It contains the
      root table of contents that connects the documentation pages.

   MyST
      A Markdown format and parser that can express Sphinx directives and
      roles. It is an alternative to reStructuredText when enabled in Sphinx.

   object
      A documented item, such as a MATLAB function or class. A description
      directive creates an entry that a role can link to.

   RemoveInSphinxXXXWarning
      A warning about a Sphinx feature scheduled for removal in a future
      version. Check the warning message and the named Sphinx version when
      updating Sphinx or an extension.

   reStructuredText
      A plain-text markup format used by Sphinx. Files commonly end in
      ``.rst`` and contain headings, links, directives and roles.

   role
      Inline markup within text. For example, ``:mat:func:`times_two``` links
      to the documentation of the MATLAB function ``times_two``.

   source directory
      The folder containing a Sphinx project's source documents and their
      subfolders. Its location is an argument to ``sphinx-build``.

   toctree
      A directive that connects pages into a table of contents. It controls
      the document hierarchy and, in many themes, the navigation sidebar.