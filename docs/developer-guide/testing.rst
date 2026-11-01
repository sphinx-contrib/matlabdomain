Testing
=======

Running the tests
-----------------

.. code-block:: console

   $ uv run pytest

``pyproject.toml`` sets verbose pytest options (``-vv -s --showlocals``);
for a quiet run, override them:

.. code-block:: console

   $ uv run pytest -q -o addopts= -rfs

The suite takes about a minute. A few tests are skipped on some systems:
those that need POSIX permissions, non-UTF-8 file names (Linux) or Windows
device names, and the two oracle tests that need the MATLAB reference corpus
(``../reference/matlab_names_reference.json``, outside the repository).

tox runs the suite against each supported Sphinx line, as CI does:

.. code-block:: console

   $ tox run -e py313-sphinxlatest
   $ tox run -e py311-sphinxmin       # Sphinx 8.0, the lowest pins
   $ tox run -e py313-sphinxlatest -- -x --lf

Each tox run also builds ``tests/test_docs`` with Sphinx.

Layout
------

``tests/test_*.py``
   The tests, by area: parsing (``test_mat_tree_sitter_parser.py``,
   ``test_parse_contract.py``, ``test_parser_details.py``), classification
   and naming (``test_mat_classify.py``, ``test_mat_naming.py``), the index
   and incremental builds (``test_build_index.py``, ``test_lazy_index.py``,
   ``test_domain_lifecycle.py``), fault tolerance, directives and options,
   ``sphinx-matlab-apidoc`` (``test_apidoc.py``), ``matlab-api-check``
   (``test_api_check.py``) and this documentation
   (``test_documentation.py``).
``tests/roots/test_<name>/``
   Small Sphinx projects (``conf.py``, pages and MATLAB files) built by the
   tests with the ``make_app`` fixture.
``tests/test_data/``
   MATLAB files for parser tests.
``tests/apidoc_golden/``
   The expected output of ``sphinx-matlab-apidoc`` for the
   ``test_apidoc_basics`` root (default and ``--separate``).
``examples/apidoc/``
   The worked example: its generated pages and api-check reports are
   compared with fresh output, and the project is built with ``-W``.
``docs/``
   The documentation is built with ``-n``, and every configuration value,
   directive, option, role, warning and command-line option must appear in
   its reference pages.

Writing tests
-------------

* Use ``make_app`` (from ``sphinx.testing``, loaded in ``conftest.py``) to
  build a project. Tests that change files write the project into
  ``tmp_path`` or copy a root there first, so roots stay unchanged.
* Check behavior through what users see: the doctree, the HTML, the
  inventory, warnings (``app.warning.getvalue()``), the domain data.
* When a test documents MATLAB behavior (what ``help`` shows, which file
  MATLAB calls), check it in MATLAB and name the release in the test.
* After changing the generator or the example, regenerate the golden output
  with the command the failing test runs, and review the difference before
  committing it. The example's api-check reports: run ``matlab-api-check``
  on ``examples/apidoc/docs`` and copy ``api-check.json``, and
  ``api-check.txt`` with the source paths shortened to ``../src/``.

Coverage
--------

Every reachable line and branch of ``sphinxcontrib`` is covered, Windows and
Linux combined. CI's coverage job combines the data of every test job
except the Sphinx ``dev`` job and fails below 100%:

.. code-block:: console

   $ uv run pytest --cov --cov-report=term-missing

* A line that only one system reaches (POSIX permissions, non-UTF-8 file
  names) counts when the other system's job covers it.
* A defensive guard that only a bug can reach stays, marked
  ``# pragma: no cover`` (or ``no branch``) with the reason on the same or
  the previous line. ``exclude_also`` lists only ``if __name__ ==
  "__main__":`` and ``if TYPE_CHECKING:``.
* Code that defends nothing is deleted, not excluded.

The real-project gauntlet
-------------------------

``test_slow/gauntlet`` runs ``sphinx-matlab-apidoc``, ``sphinx-build`` and
``matlab-api-check`` on 14 open-source MATLAB projects (about 24,000 files)
and checks that nothing crashes, reruns are identical, serial and ``-j``
builds agree, and Windows and Linux give the same output. Run it before
changing the parser, the index or a tree-sitter pin; ``test_slow/README.md``
explains how:

.. code-block:: console

   $ python test_slow/gauntlet/fetch.py
   $ python test_slow/gauntlet/gauntlet.py --jobs
   $ python test_slow/gauntlet/compare.py test_slow/gauntlet/summaries/phase9-linux.json test_slow/gauntlet/runs/latest

The checkouts need about 5 GB. On Windows, Git must create symbolic links
(``core.symlinks``); ``fetch.py`` sets it for the checkouts it clones.

Testing on Linux and Windows
----------------------------

Behavior differs between systems in a few places (file name case, links,
permissions, the default ANSI code page, parallel builds, which Sphinx runs
serially on Windows), so changes in these areas are tested on both:

* CI runs the suite on Linux, Windows and macOS for every push; start it by
  hand with ``gh workflow run python-package.yml --ref <branch>``.
* For runs on a machine of the other system, put a script in ``tmp/`` at the
  repository root that runs each step and prints the expected values next
  to the results; commit it on a side branch, run it there and bring the
  results back.
* To emulate Linux's case-sensitive file system on Windows (no
  administrator rights needed), make a folder case-sensitive with
  ``fsutil file setCaseSensitiveInfo <folder> enable`` and pass it as
  pytest's ``--basetemp``.
