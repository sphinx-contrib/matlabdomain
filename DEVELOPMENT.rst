Developing sphinxcontrib-matlabdomain
=====================================

The project uses `pre-commit https://pre-commit.com/`_ for setting up git
pre-commit hooks. Development is best done in a Python virtual environment.

Start by running:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r dev-requirements.txt
    pre-commit install


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
