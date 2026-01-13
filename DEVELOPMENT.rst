Developing sphinxcontrib-matlabdomain
=====================================

Code style
----------

The project uses `pre-commit <https://pre-commit.com/>`_ for setting up git pre-commit hooks.
Development is best done in a Python virtual environment.

Start by running:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -e '.[dev]'
    pre-commit install


Testing
-------

Test can be run directly with pytest:

.. code-block:: bash

    python -m venv .venv
    .venv\Scripts\activate
    pip install -e '.[dev]'
    pytest tests

Or via tox:

.. code-block:: bash

    python -m venv .venv
    .venv\Scripts\activate
    pip install tox

    # will run tests with all available python and a range of sphinx versions
    tox

    # or choose a specific python and sphinx version
    tox run -e py313-sphinxlatest

    # and pass extra pytest options (here for --last-failed and --exitfirst)
    tox run -e py313-sphinxlatest -- --lf -x

Writing tests
"""""""""""""

If you need to add tests,
it may be easier to make use of some of the fixtures in ``tests/conftest.py``
that can build dummy doc and check the generated output.

PR Structure
------------

A new pull request must have a clear scope, conveyed through its name, a
reference to the issue it targets (through the exact mention "Closes #XXXX"),
and a synthetic summary of its goals and main steps.
When working on big contributions, we advise contributors to split them into
several PRs when possible.
This has the benefit of making code changes clearer, making PRs easier to review,
and overall smoothening the whole process.

When relevant, PR names should also include tags if they fall in various categories.
When opening a PR, the authors should include the [WIP] tag in its name, or use
github draft mode.
Other tags can describe the PR content :

- [FIX] for a bugfix,
- [DOC] for a change in documentation or examples,
- [ENH] or [FEAT] for a new feature
- [STY] for code style changes
- [REF] for refactoring
- [MAINT] for maintenance changes.
