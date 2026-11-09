Sphinx primer for MATLAB users
==============================

Sphinx builds documentation from text files and code. You do not need MATLAB
to build these pages. This guide starts with the operating system's command
line, then shows how Sphinx and this extension document MATLAB code.

For short definitions, use the :doc:`glossary <../reference/glossary>`.
Dotted-underlined terms such as :term:`builder` link to their definitions.
This site also previews linked content in tooltips when JavaScript is available.
You can select a link to read its destination without the preview.

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
Click in the terminal and paste, then press Enter. In Windows Terminal,
``Ctrl+Shift+V`` or the context menu normally pastes. In a separate CMD or
PowerShell window, right-click may paste, depending on its settings. In Git
Bash, use ``Shift+Insert`` or the right-click menu. Paste shortcuts depend on
the terminal application; ``Ctrl+V`` is not universal. Do not paste commands
you do not understand.

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

Install Python 3.11 or newer and `uv <https://docs.astral.sh/uv/>`_ using
their official installation instructions. Open a new terminal if an installer
asks you to, and check that ``uv --version`` runs. If the shell cannot find
``uv``, follow its installer's instructions for adding it to your path.

In the project folder, create a uv project only if it does not already have
``pyproject.toml``:

.. code-block:: console

   uv init

Then add this extension and start the interactive setup:

.. code-block:: console

   uv add sphinxcontrib-matlabdomain
   uv run scmd quickstart

Run each line separately. ``uv`` manages the Python environment and installs
Sphinx as a dependency. Quickstart asks questions and writes ``docs/conf.py``
and source pages. Review its output and follow its next steps. It can also
detect existing project settings; see :doc:`quickstart` before accepting its
defaults for an existing documentation project.

From the project folder, build the HTML site:

.. code-block:: console

   uv run sphinx-build -M html docs docs/_build

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