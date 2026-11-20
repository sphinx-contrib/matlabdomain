Frequently asked questions
==========================

Why does Sphinx report that ``docs/docs`` does not exist?
---------------------------------------------------------

Sphinx resolves the source, output and ``-d`` doctree paths relative to
the shell's current working directory. A command that uses ``docs`` as
the source directory must run from the project root, not from inside
``docs``.

For example, run the API checker from the project root:

.. code-block:: console

   $ uv run sphinx-build -b matlab-api-check -d docs/_build/doctrees docs docs/_build/api-check

Or, from the ``docs`` directory, use paths relative to that directory:

.. code-block:: console

   $ uv run sphinx-build -b matlab-api-check -d _build/doctrees . _build/api-check

Use the HTML build's doctree directory for ``-d`` if you want to reuse it.
See :doc:`api-check` for the checker and its findings. A missing source
directory is reported by Sphinx before the extension is loaded.

.. _configuration-error-report:

Why does a wrong setting look like a crash?
-------------------------------------------

A wrong ``matlab_*`` value stops the build with a configuration error
(``ConfigError``) whose message names the setting and what it must be.
Sphinx 8.0 and 8.1 print the message under ``Configuration error:``.
Sphinx 8.2 and later print every error that stops a build as a report
meant for a bug report, their own configuration errors included (an
unknown builder, a ``conf.py`` that raises):

.. code-block:: text

   Configuration error!

   Versions
   ========
   ...

   Traceback
   =========

         File ".../sphinxcontrib/matlab.py", line ..., in ensure_configuration
           ...
       sphinx.errors.ConfigError: matlab_auto_link must be None, 'basic' or 'all', not 'some'.

   The full traceback has been saved in:
   /tmp/sphinx-err-....log

   To report this error to the developers, please open an issue at <https://github.com/sphinx-doc/sphinx/issues/>. Thanks!
   Please also report this if it was a user error, so that a better error message can be provided next time.

The message is the last line of the Traceback section, after
``sphinx.errors.ConfigError:``. Correct the setting in ``conf.py`` or in
the ``-D`` option and build again; there is nothing to report. A file of
the project in the way of a stable address (:confval:`matlab_stable_urls`)
is reported the same way, at the end of the build. The
extension raises the same kind of error as Sphinx's own checks, and
Sphinx decides how it is printed. With ``-T`` or ``-v`` the Traceback
section has the whole traceback; the message is still its last line.

The build ends with exit status 2. ``make html`` prints the same report,
then make's ``Error 2``. sphinx-autobuild prints it, then ``Sphinx exited
with exit code: 2``, keeps serving the pages of the last build and builds
again when a file changes. ``scmd apidoc`` prints the message on one line:
``scmd apidoc: error: <message>``.
