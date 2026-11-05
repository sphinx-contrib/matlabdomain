Quickstart
==========

This page sets up the documentation of a MATLAB project with one command,
then shows what that command does by hand for a single function. If Sphinx
is new to you, its `tutorial
<https://www.sphinx-doc.org/en/master/tutorial/index.html>`_ explains the
basics.

With ``sphinx-matlab-quickstart``
---------------------------------

From the MATLAB project's folder (here ``myproject``, with its code in
``src``), run:

.. code-block:: console

   $ sphinx-matlab-quickstart

It reads the project first: the MATLAB release in its CI files or README,
git submodules, a MATLAB project file, Markdown notes next to the code, the
headings of the help text, and whether the project uses uv. Then it asks one
question per choice, with what it found as the default (press Enter to
keep it):

.. code-block:: text

   > Project name [myproject]:
   > Author names [Ada Lovelace]:
   > MATLAB release the code targets [R2024b]:
   > API pages per namespace or per folder [namespace]:
   ...

It writes the Sphinx source folder ``docs/`` (``conf.py``, ``index.rst``,
the make files, a build guide and the API pages), adds the docs
dependencies to ``pyproject.toml`` in a uv project, and prints a report of
the project with the next steps. Build the site:

.. code-block:: console

   $ cd docs
   $ make html

Open ``docs/_build/html/index.html``. To see what the command would do
first, run it with ``-n``: it writes nothing, prints the report, and saves
your answers for the real run. :doc:`../user-guide/setting-up` explains every
question, what it detects and what it writes.

By hand
-------

The command writes a full ``conf.py``. The one setting every project
needs, and a page that documents one function, look like this.

1. Lay out the project
~~~~~~~~~~~~~~~~~~~~~~

Keep the MATLAB code and the documentation side by side:

.. code-block:: text

   myproject/
       src/
           times_two.m
       docs/

``src/times_two.m``:

.. literalinclude:: ../src/times_two.m
   :language: matlab

2. Create the Sphinx project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

From ``myproject``, run ``sphinx-quickstart`` and accept the defaults (it
asks for a project name and an author):

.. code-block:: console

   $ sphinx-quickstart docs

It writes ``docs/conf.py``, ``docs/index.rst`` and build scripts.

3. Configure the extension
~~~~~~~~~~~~~~~~~~~~~~~~~~

Edit ``docs/conf.py``: ``sphinx-quickstart`` wrote ``extensions = []``;
replace that line with these lines:

.. code-block:: python

   extensions = ["sphinxcontrib.matlab"]

   # The folder all MATLAB code lives below, relative to this folder.
   matlab_src_code_project_root = "../src"

   # Optional: lets you write ``.. autofunction::`` instead of
   # ``.. mat:autofunction::`` and ``:func:`` instead of ``:mat:func:``.
   # RECOMMENDATION: If you have a mixed language project, do not set this and
   # and use ``mat:*`` roles and directives explicitly. This creates explicit
   # separation between MATLAB and other languages in your documentation.
   primary_domain = "mat"

:confval:`matlab_src_code_project_root` is the one setting every project needs:
the extension finds MATLAB files below that folder, and names them by their
path relative to it. :doc:`../user-guide/configuration` covers the other
settings.

4. Document the function
~~~~~~~~~~~~~~~~~~~~~~~~

Add an auto directive to ``docs/index.rst``:

.. literalinclude:: ../snippets/quickstart.rst
   :language: rst

``times_two`` is the function's MATLAB name, the name you would type in
MATLAB. The path below the project root (``times_two.m``) works too.

5. Build
~~~~~~~~

.. code-block:: console

   $ sphinx-build -M html docs docs/_build

Open ``docs/_build/html/index.html``. The function looks like this:

.. include:: ../snippets/quickstart.rst

To make every warning an error (``-W``) and to warn about every link that
does not resolve (``-n``), add them after the folders; with ``-M``, the
builder name must come first:

.. code-block:: console

   $ sphinx-build -M html docs docs/_build -n -W

The help text was read from the comment block after the ``function`` line,
the block MATLAB's ``help times_two`` shows. Its ``:param x:`` lines are
reST field lists; :doc:`../user-guide/help-text` explains how help text is
turned into documentation.

Next steps
----------

* Document a whole project: :doc:`../user-guide/apidoc` writes a page for
  every namespace or folder.
* Write the directives yourself: :doc:`../user-guide/documenting`.
* Link to functions and classes from your text: :doc:`../user-guide/referencing`.
* Check that the help text describes every input and output:
  :doc:`../user-guide/api-check`.
* Set up an existing MATLAB repository with an agent: the repository's
  skill ``skills/setting-up-a-project/SKILL.md`` starts with
  ``sphinx-matlab-quickstart`` and walks through the decisions and the
  warnings step by step.
