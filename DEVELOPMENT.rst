Developing sphinxcontrib-matlabdomain
=====================================

The project uses `pre-commit https://pre-commit.com/`_ for setting up git
pre-commit hooks. Development is best done in a Python virtual environment.

Start by running:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r dev-requirements.txt
    pre-commit install
