Sphinx primer for MATLAB users
==============================

Sphinx builds documentation from text files and code. You do not need MATLAB
to build these pages. This guide starts with the operating system's command
line, then shows how Sphinx and this extension document MATLAB code.

For short definitions, use the :doc:`glossary <../reference/glossary>`.
Terms such as :term:`builder` link to their definitions; hover over a link
to preview it.

The tools and their jobs
------------------------

* :term:`reStructuredText` is a plain-text format for documentation pages.
  :term:`Docutils` reads it. :term:`MyST` adds Markdown support when installed.
* Sphinx reads the pages and uses a :term:`builder` to produce HTML or another
  output. A :term:`toctree` connects the pages in the navigation.
* An :term:`extension` adds behavior to Sphinx. This extension supplies the
  MATLAB :term:`domain`, which contains :term:`directives <directive>` for
  documenting MATLAB objects and :term:`roles <role>` for links to them.
* ``conf.py`` configures the Sphinx project. It is a Python file, not a
  MATLAB script. The generated web pages go in the build output folder.

Open a terminal
---------------

A terminal runs commands in a *shell*. It is separate from the MATLAB
Command Window. Commands such as ``uv run`` and ``cd`` below belong in the
terminal, not in MATLAB. Each terminal has a current folder; commands that
use relative paths start there.

* **Windows:** Open Windows Terminal and select PowerShell or Command Prompt
  (CMD). Git Bash is another option if Git for Windows is installed.
* **macOS:** Open Terminal from Applications > Utilities, or find it with
  Spotlight.
* **Linux:** Open your desktop's Terminal application. Its name varies by
  distribution.

Copy only the command text, not a prompt such as ``$``, ``>``, or
``PS C:\...>``. The prompt shows that the shell is ready for a command.
Click in the terminal and paste, then press Enter. The paste key depends on
the terminal application:

* **Windows Terminal** (PowerShell or CMD): ``Ctrl+V``, or right-click.
* **Git Bash**: ``Shift+Insert``, or right-click and choose Paste.
  ``Ctrl+V`` does not paste there.
* **macOS Terminal**: ``Cmd+V``.
* **Linux terminals**: usually ``Ctrl+Shift+V``, or right-click and choose
  Paste.

Do not paste commands you do not understand.

Choose your project folder
--------------------------

Use the folder that contains your MATLAB project, not the ``docs`` folder.
Replace the example path with your own. Keep the quotes around paths with
spaces. These examples show one command per shell; do not run all of them.

Windows CMD changes both the drive and folder with ``/d``:

.. code-block:: bat

   cd /d "C:\Users\YourName\Documents\myproject"

In Windows PowerShell:

.. code-block:: powershell

   Set-Location "C:\Users\YourName\Documents\myproject"

In Git Bash, the same Windows drive is written as ``/c/``:

.. code-block:: bash

   cd "/c/Users/YourName/Documents/myproject"

On macOS or Linux:

.. code-block:: bash

   cd "$HOME/Documents/myproject"

Run ``cd`` in CMD, ``Get-Location`` in PowerShell, or ``pwd`` in Git Bash,
macOS or Linux to check the current folder. Run ``dir`` in CMD or PowerShell,
or ``ls`` in Git Bash, macOS or Linux, to list its contents. A command that
cannot find a file may have started in the wrong folder.

Install and build
-----------------

Install `Python 3.11 or newer <https://www.python.org/downloads/>`_ and
`uv <https://docs.astral.sh/uv/getting-started/installation/>`_ using their
installation instructions. Open a new terminal if an installer
asks you to, and check that ``uv --version`` runs. If the shell cannot find
``uv``, follow its installer's instructions for adding it to :term:`PATH`.

In the project folder, create a uv project only if it does not already have
``pyproject.toml``:

.. code-block:: console

   uv init --bare --vcs none

This creates Python project metadata without starter code or a new Git
repository. It leaves any existing Git repository in place. Add this extension:

.. code-block:: console

   uv add sphinxcontrib-matlabdomain

``uv`` manages the :term:`Python environment <virtual environment>` and
installs Sphinx as a dependency.

If your project uses Git
~~~~~~~~~~~~~~~~~~~~~~~~

Git records file history in a repository. A commit saves reviewed changes
locally; it does not publish them. Quickstart refuses to change project
metadata that already has uncommitted edits, so record the dependency setup
before running it.

Check the project's Git status:

.. code-block:: console

   git status --short

If the terminal cannot find Git, or Git reports that this is not a repository,
skip this section. Git is not required to build documentation.

Otherwise, open ``pyproject.toml`` and ``uv.lock`` in a text editor and review
the setup changes. If either file also contains earlier work, finish that
work separately first. Select these two files and record the setup:

.. code-block:: console

   git add -- pyproject.toml uv.lock
   git commit -m "Prepare Python documentation tools"

``git add`` selects the files for the commit. It does not select unrelated
files. If Git asks for an author identity, replace the examples below with
your name and email address, then repeat the commit command:

.. code-block:: console

   git config user.name "Your Name"
   git config user.email "you@example.org"

These settings apply only to this repository. Quickstart also checks
``.gitignore`` and ``.gitattributes``; finish any pending edits to those files
before proceeding.

Run quickstart and build
~~~~~~~~~~~~~~~~~~~~~~~~

Start the interactive setup from the project folder:

.. code-block:: console

   uv run scmd quickstart

Run each command separately. Quickstart asks questions and writes ``docs/conf.py``
and source pages. Review its output and follow its next steps. It can also
detect existing project settings; see :doc:`quickstart` before accepting its
defaults for an existing documentation project.

From the project folder, build the HTML site. Quickstart puts Sphinx and the
site's theme in the ``docs`` dependency group, so ask ``uv`` for that group:

.. code-block:: console

   uv run --group docs sphinx-build -M html docs docs/_build

Open ``docs/_build/html/index.html`` in a browser. Edit the sources and run
the build again to update the pages. The :doc:`installation` page covers
other environments, and :doc:`../user-guide/builds` explains build options.

Read a page source
------------------

An ``.rst`` page can contain ordinary prose and Sphinx markup:

.. code-block:: rst

   My function
   ===========

   .. mat:autofunction:: times_two

   See :mat:func:`times_two` for the function.

The heading names the section. The directive reads the function's MATLAB help
text and creates an entry. The role links to that entry. Both use the ``mat``
domain supplied by this extension. The source file must be below the MATLAB
project root configured in ``conf.py``. See
:doc:`../user-guide/documenting` and :doc:`../user-guide/referencing` for
examples and :doc:`../user-guide/help-text` for help-text formatting.
