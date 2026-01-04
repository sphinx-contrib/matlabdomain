"""Fixtures commong to all tests."""

import shutil
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
def app(make_app, srcdir: Path, confdict: dict):  # noqa: F811
    """Run sphinx build on a source directory \
       and yield an initialize SphinxTestApp instance.

    Does some clean up after the test is run.

    srcdir: Path to the source directory

    confdict: configuration dictionary to override that of the conf.py
    """
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    yield app

    if (srcdir / "_build").exists():
        shutil.rmtree(srcdir / "_build")


@pytest.fixture
def srcdir(rootdir):
    """Return default srcdir to pass when running the 'app' fixture.

    If you need a different srcdir you can create a new fixture
    in a test module:
    the fixture defined in the same module as the test
    will take priority over the one defined in conftest.py.

    .. code-block:: python

        @pytest.fixture
        def srcdir(rootdir):
            return rootdir / "roots" / "test_classfolder"


        def test_something(app): ...

    """
    return rootdir / "roots" / "test_autodoc"


@pytest.fixture
def confdict() -> dict:
    """Return default confdict to pass when running the 'app' fixture.

    If you need a different confdict you can create a new fixture
    in a test module:
    the fixture defined in the same module as the test
    will take priority over the one defined in conftest.py.

    .. code-block:: python

        @pytest.fixture
        def confdict():
        return {
            "matlab_keep_package_prefix": True,
        }

        def test_something(app, confdict):
            ...

    If you need to test several confdict in the same test
    you can parametrize things.

    .. code-block:: python

        @pytest.fixture
        def confdict(matlab_keep_package_prefix):
            return {"matlab_keep_package_prefix": matlab_keep_package_prefix}


        @pytest.mark.parametrize("matlab_keep_package_prefix", [True, False])
        def test_something(app, confdict, matlab_keep_package_prefix): ...


    or you can also do

    .. code-block:: python

        @pytest.mark.parametrize(
            "confdict",
            [
                {"matlab_short_links": True, "matlab_auto_link": "basic"},
                {"matlab_short_links": True, "matlab_auto_link": "all"},
            ],
        )
        def test_something(app, confdict): ...
    """
    return {}
