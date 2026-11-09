Debugging and profiling
=======================

VS Code
-------

The repository's ``.vscode/launch.json`` has debug configurations
(``debugpy``, with ``justMyCode`` off so you can step into Sphinx and
tree-sitter):

``Sphinx: Debug docs build``
   ``sphinx-build -b html docs docs/_build/html``.
``Python: Debug current test file``
   pytest on the open test file.
``Debug scmd apidoc (CLI)``
   A dry run (``-n``) of the command on the worked example
   (``examples/apidoc/docs``); drop ``-n`` to write the pages.
``Debug matlab-api-check``
   The :term:`builder` on the ``test_api_check`` root, which has known gaps, so it
   exits with status 1.
``sphinxcontrib-matlabdomain: Debug profiling harness build`` and ``sphinxcontrib-matlabdomain: Profile harness (cProfile)``
   The profiling harness (below).

``_build/`` is ignored by Git.

Logging
-------

Run ``sphinx-build`` with ``-vv`` to see the :term:`extension`'s debug messages,
such as the :term:`reST` each auto :term:`directive` generates. ``-T`` prints the
full traceback of an exception. Breakpoints in the documenters see the
generated lines in ``self.directive.result``.

Profiling a build
-----------------

.. code-block:: console

   $ python -m cProfile -o build.prof -m sphinx -E -b html docs docs/_build/html
   $ uvx snakeviz build.prof

``test_slow/profiling`` is a profiling harness: a Sphinx project over the
gauntlet's ``vhlab-toolbox-matlab`` checkout (1,726 files; fetch it with
``test_slow/gauntlet/fetch.py``), with ``profile_build.py`` and the
recorded results of earlier phases. A cold harness build takes about half a
second on Linux.
