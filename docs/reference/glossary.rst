Glossary
========

This page explains Sphinx terms used in these docs. It covers the terms in
the `Sphinx glossary <https://www.sphinx-doc.org/en/master/glossary.html>`_
in different words and adds a few terms useful to MATLAB users. The Sphinx
glossary is authoritative; consult it when these descriptions differ.

Terms used on other pages link here. Hover over such a link, or move the
keyboard focus to it, to preview the definition; Escape closes the preview.

.. glossary::
   :sorted:

   API
      The functions, classes and other public interfaces a project provides.
      API reference pages describe how to call them and what they return.

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
      package adds the ``mat`` domain; ``sphinxcontrib-mermaid`` adds diagrams.

   inventory
      The ``objects.inv`` file that lists a site's documented targets and
      their addresses. Other Sphinx projects use it to create links to them.

   markup
      Text notation for structure and formatting, such as heading underlines
      and link syntax. A parser turns the notation into document elements.

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

   PATH
      The operating system's list of folders to search for executable
      commands. This is separate from MATLAB's search path.

   RemovedInSphinxXXWarning
   RemoveInSphinxXXXWarning
      A warning about a Sphinx feature scheduled for removal in a future
      version, such as ``RemovedInSphinx10Warning``. Check the warning
      message and the named Sphinx version when updating Sphinx or an
      extension. The Sphinx glossary spells it ``RemoveInSphinxXXXWarning``.

   reStructuredText
   reST
      A plain-text markup format used by Sphinx. Files commonly end in
      ``.rst`` and contain headings, links, directives and roles.

   role
      Inline markup within text. For example, ``:mat:func:`times_two``` links
      to the documentation of the MATLAB function ``times_two``.

   signature
      An object's call or declaration syntax, such as a function name with
      its arguments. Sphinx displays it above the object's description.

   source directory
      The folder containing a Sphinx project's source documents and their
      subfolders. Its location is an argument to ``sphinx-build``.

   theme
      The appearance and navigation layout of the generated HTML site.
      This documentation uses the Furo theme.

   toctree
      A directive that connects pages into a table of contents. It controls
      the document hierarchy and, in many themes, the navigation sidebar.

   virtual environment
      A separate Python interpreter and set of installed packages for a
      project. uv normally keeps it in the project's ``.venv`` folder.
