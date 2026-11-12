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
device names.

tox runs the suite against each supported Sphinx line, as CI does:

.. code-block:: console

   $ uv run tox -e py313-sphinxlatest
   $ uv run tox -e py311-sphinxmin       # Sphinx 8.0, the lowest pins
   $ uv run tox -e py313-sphinxlatest -- -x --lf
   $ uv run tox -e lint                 # Ruff, format check, basic Pyright

Each tox run also builds ``tests/test_docs`` with Sphinx.

The suite fails on a deprecation warning that Python attributes to this
package's own modules (``filterwarnings`` in ``pyproject.toml``); warnings
from other packages, such as ``myst_parser``, do not. This is the signal that
a Sphinx, docutils or Python release now deprecates something the package
uses, for example the autodoc ``Documenter`` classes. Read the warning, then
move the code off the deprecated interface; only if that cannot happen yet,
add a temporary ``ignore`` entry for that exact message, with a comment.
The ``lint`` :term:`environment <virtual environment>` instead checks maintained Python without modifying it.
Repository configuration and its documented inventory are checked by
``test_documentation.py``; see :ref:`repository-configuration`.

Layout
------

``tests/test_*.py``
   The tests, by area: parsing (``test_mat_tree_sitter_parser.py``,
   ``test_parse_contract.py``, ``test_parser_details.py``), classification
   and naming (``test_mat_classify.py``, ``test_mat_naming.py``), the index
   and incremental builds (``test_build_index.py``, ``test_lazy_index.py``,
   ``test_domain_lifecycle.py``), fault tolerance, :term:`directives <directive>` and options,
   ``scmd apidoc`` (``test_apidoc.py``), links from another
   project through its :term:`inventory` and page splitting
   (``test_intersphinx.py``), stable addresses (``test_stable_urls.py``, ``test_chooser_cache.py``),
   ``matlab-api-check``
   (``test_api_check.py``), ``scmd quickstart``
   (``test_quickstart.py``) and this documentation
   (``test_documentation.py``).
``tests/roots/test_<name>/``
   Small Sphinx projects (``conf.py``, pages and MATLAB files) built by the
   tests with the ``make_app`` fixture.
``tests/test_data/``
   MATLAB files for parser tests.
``tests/apidoc_golden/``
   The expected output of ``scmd apidoc`` for the
   ``test_apidoc_basics`` root: namespace grouping (``default``,
   ``separate``) and folder grouping (``folder``, ``folder-separate``).
``tests/quickstart_golden/``
   The expected output of ``scmd quickstart``: the Sphinx
   :term:`source folder <source directory>` and the printed lines for the
   ``test_quickstart`` root as a uv
   project in git (``uv``), for ``test_apidoc_basics`` outside git
   (``plain``), and a dry run (``dry-run.txt``). The copyright year is
   ``<YEAR>``, run times ``<T>``.
``examples/apidoc/``
   The worked example: its generated pages and api-check reports are
   compared with fresh output, and the project is built with ``-W``.
``docs/``
   The documentation is built with ``-n``, and every configuration value,
   directive, option, :term:`role`, warning and command-line option must appear in
   its reference pages.

Writing tests
-------------

* Use ``make_app`` (from ``sphinx.testing``, loaded in ``conftest.py``) to
  build a project. Tests that change files write the project into
  ``tmp_path`` or copy a root there first, so roots stay unchanged.
* Check behavior through what users see: the :term:`doctree`, the HTML, the
  inventory, warnings (``app.warning.getvalue()``), the :term:`domain` data.
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

``test_slow/gauntlet`` runs ``scmd apidoc``, ``sphinx-build`` and
``matlab-api-check`` on 14 open-source MATLAB projects (about 24,000 files)
and checks that nothing crashes, reruns are identical, serial and ``-j``
builds agree, and Windows and Linux give the same output. Run it before
changing the parser, the index or a tree-sitter pin; ``test_slow/README.md``
explains how:

.. code-block:: console

   $ uv run python test_slow/gauntlet/gauntlet.py --fetch --jobs
   $ uv run python test_slow/gauntlet/compare.py test_slow/gauntlet/summaries/linux.json test_slow/gauntlet/runs/latest

It needs Git, network access the first time and about 4 GB of disk, and
takes about 20 minutes on Linux.

With ``--quickstart`` it runs ``scmd quickstart -q`` on a
temporary ``git worktree`` of each project instead, then a ``-n`` build of
what the command wrote; the checkouts stay unchanged.

The checkouts need about 5 GB. On Windows, Git must create symbolic links:
matpower, for one, has 807 of them, and without them Git writes small text
files in their place, so the pages and warnings differ from Linux.
``fetch.py`` sets ``core.symlinks`` for the checkouts it clones, but
Windows lets a process create links only if one of these holds:

* **Developer Mode** is on (Settings, System, For developers). Then
  ordinary users can create links; no administrator rights are needed once
  it is on. This is the usual choice.
* The user has the *Create symbolic links* right
  (``SeCreateSymbolicLinkPrivilege``; Local Security Policy, User Rights
  Assignment). An administrator grants it once; sign out and in again.
* The process runs as administrator.

To check, create a link in a scratch folder, as a normal user:
``New-Item -ItemType SymbolicLink -Path link -Target somefile`` in
PowerShell, or ``mklink link somefile`` in ``cmd``. Git for Windows' installer
option "Enable symbolic links" sets ``core.symlinks`` for every repository.
A checkout made without links can be repaired:

.. code-block:: console

   $ git config core.symlinks true
   $ git checkout -- .

``git checkout -- .`` discards uncommitted changes in that checkout.
Junctions (``mklink /J``) need no rights, but Git does not create them.

Testing on Linux and Windows
----------------------------

Behavior differs between systems in a few places (file name case, links,
permissions, the default ANSI code page, parallel builds, which Sphinx runs
serially on Windows), so changes in these areas are tested on both:

* CI covers Linux, Windows and macOS.
* For runs on a machine of the other system, put a script in ``tmp/`` at the
  repository root that runs each step and prints the expected values next
  to the results; commit it on a side branch, run it there and bring the
  results back.
* To emulate Linux's case-sensitive file system on Windows (no
  administrator rights needed), make a folder case-sensitive with
  ``fsutil file setCaseSensitiveInfo <folder> enable`` and pass it as
  pytest's ``--basetemp``.
