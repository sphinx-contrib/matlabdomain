Frequently asked questions
==========================

Why does Sphinx report that ``docs/docs`` does not exist?
---------------------------------------------------------

:term:`Sphinx` resolves the source, output and ``-d`` :term:`doctree` paths
relative to the shell's current working directory. A command that uses
``docs`` as the :term:`source directory` must run from the project root, not
from inside ``docs``.

For example, run the :term:`API` checker from the project root:

.. code-block:: console

   $ uv run sphinx-build -b matlab-api-check -d docs/_build/doctrees docs docs/_build/api-check

Or, from the ``docs`` directory, use paths relative to that directory:

.. code-block:: console

   $ uv run sphinx-build -b matlab-api-check -d _build/doctrees . _build/api-check

Use the HTML build's :term:`doctree` directory for ``-d`` if you want to reuse
it. See :doc:`api-check` for the checker and its findings. A missing :term:`source
directory` is reported by :term:`Sphinx` before the :term:`extension` is loaded.
