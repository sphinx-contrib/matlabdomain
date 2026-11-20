sphinxcontrib-matlabdomain
==========================

New to :term:`Sphinx`? Start with the :doc:`getting-started/sphinx-primer` and
:doc:`reference/glossary`. Terms such as :term:`directive`, :term:`role`,
:term:`domain` and :term:`builder` link to definitions.

**sphinxcontrib-matlabdomain** is a `Sphinx`_ :term:`extension` for `MATLAB`_
code. It adds a ``mat`` :term:`domain` to :term:`Sphinx`, with
:term:`directives <directive>` and :term:`roles <role>` for MATLAB functions,
classes, scripts, apps and folders, and *auto* :term:`directives <directive>`
that read the help text from the ``.m`` and ``.mlapp`` files themselves, much like
``sphinx.ext.autodoc`` does for Python. Simulink models and libraries are
documented too (:doc:`user-guide/simulink`).

.. _agent-skills:

.. admonition:: AI agent skills

   The package ships skills for AI coding agents (GitHub Copilot, Claude,
   OpenAI Codex) that work through the job step by step:

   * ``setting-up-a-project`` sets up the documentation of a MATLAB
     repository that has none, starting with ``scmd quickstart``
     (:doc:`user-guide/setting-up`);
   * ``migrating-from-0x`` moves a project from matlabdomain 0.x to 1.0
     (:doc:`user-guide/migration`).

   ``scmd skills install`` copies them into the project, where the agent
   finds them (:program:`scmd skills install`).

   .. important::

      Learn :term:`Sphinx` and matlabdomain before you hand the work to an agent.
      The :doc:`getting-started/quickstart`, the
      :doc:`getting-started/sphinx-primer` and the user guide take about
      one to two hours. Skip them, and every later change to the site
      needs an agent too, because nobody on the project knows how it
      works. Skipping the learning is a trade-off you can choose, but
      choose it on purpose.

It names :term:`objects <object>` the way MATLAB does: ``+pkg`` folders are
namespaces, ``@Cls`` folders hold a class and its methods, and help text is
found where MATLAB's ``help`` finds it. Three tools come with it:

* ``scmd quickstart`` sets up the documentation of a MATLAB
  project: ``conf.py``, the make files and the :term:`API` pages, with defaults
  read from the project;
* ``scmd apidoc`` writes pages for every file of a project, so a
  large project needs no hand-written :term:`directives <directive>`;
* the ``matlab-api-check`` :term:`builder` checks that functions, classes and
  methods have help text, and that it describes their inputs, outputs and
  name-value arguments, for example in CI.

A ``conf.py`` and a page that document one function:

.. code-block:: python

   extensions = ["sphinxcontrib.matlab"]
   matlab_src_code_project_root = "../src"  # relative to conf.py folder

.. literalinclude:: snippets/quickstart.rst
   :language: rst

:doc:`getting-started/quickstart` shows the result.

It needs Python 3.11 or newer and :term:`Sphinx` 8.0 or newer, and is tested on
Linux, Windows and macOS. Start with :doc:`getting-started/installation`.

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   getting-started/installation
   getting-started/quickstart
   getting-started/sphinx-primer

.. toctree::
   :maxdepth: 2
   :caption: User guide

   user-guide/configuration
   user-guide/setting-up
   user-guide/documenting
   user-guide/referencing
   user-guide/linking-projects
   user-guide/help-text
   user-guide/apidoc
   user-guide/sidecars
   user-guide/simulink
   user-guide/api-check
   user-guide/warnings
   user-guide/builds
   user-guide/projects-and-versions
   user-guide/migration
   user-guide/FAQ

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference/configuration
   reference/glossary
   reference/directives
   reference/cli
   reference/templates
   reference/api-check-report
   reference/warnings

.. toctree::
   :maxdepth: 2
   :caption: Developer guide

   developer-guide/contributing
   developer-guide/testing
   developer-guide/architecture
   developer-guide/debugging
   developer-guide/simulink-file-formats
   developer-guide/roadmap

.. toctree::
   :maxdepth: 1
   :caption: Project

   CHANGES
   blog/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`mat-folderindex`
* :ref:`search`

.. _Sphinx: https://www.sphinx-doc.org/
.. _MATLAB: https://www.mathworks.com/products/matlab.html
