from pathlib import Path

import pytest

# needed for sphinx testing
# import once in the pytest config
# so it does not need to be imported in every test file
from sphinx.testing.fixtures import make_app, test_params  # noqa: F401


@pytest.fixture()
def rootdir() -> Path:
    return Path(__file__).parent


@pytest.fixture()
def dir_test_data(rootdir) -> Path:
    return rootdir / "test_data"


@pytest.fixture
def confdict() -> dict:
    return {}


@pytest.fixture
def app(make_app, srcdir, confdict):  # noqa: F811
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()
    return app
