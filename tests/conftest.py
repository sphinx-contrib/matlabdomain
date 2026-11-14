"""Fixtures common to all tests."""

import os
import shutil
import time
from pathlib import Path

import pytest

# Sphinx's test fixtures (make_app, test_params, ...) for every test file.
pytest_plugins = ["sphinx.testing.fixtures"]

SIMULATE = "--simulate-platforms"


def pytest_addoption(parser):
    parser.addoption(
        SIMULATE,
        action="store_true",
        help="fake the conditions of other systems and Python versions (case "
        "rules, drives, file names, permissions), so that one machine covers "
        "every line; CI's test jobs run without it",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        f"simulates(condition): the test fakes a condition of another system; "
        f"it runs only with {SIMULATE}",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption(SIMULATE):
        return
    for item in items:
        if (marker := item.get_closest_marker("simulates")) is not None:
            reason = f"simulates {marker.args[0]}; runs with {SIMULATE}"
            item.add_marker(pytest.mark.skip(reason=reason))


@pytest.fixture
def condition(request):
    """Return ``condition(needs, real)``, which tells a test how it meets a
    condition that only some systems or Python versions have.

    It returns ``"real"`` if ``real`` is true: the system has the condition
    and the test must not fake it. Otherwise it returns ``"simulated"`` with
    ``--simulate-platforms`` (the test fakes the condition), and without the
    option it skips the test because it ``needs`` the condition.

    A test that only fakes (it never meets the condition) is marked
    ``@pytest.mark.simulates(condition)`` instead.
    """

    def check(needs, real):
        if real:
            return "real"
        if request.config.getoption(SIMULATE):
            return "simulated"
        pytest.skip(f"needs {needs} (or {SIMULATE})")

    return check


@pytest.fixture
def fake_folder(monkeypatch):
    """Return ``fake(folder, names=(), error=None, aliases=None)``, which
    makes ``os.listdir`` of the folder ``folder`` raise ``error``, or list
    ``names`` besides its files; ``os.stat`` and ``os.lstat`` of
    ``folder/name`` answer for ``folder/aliases[name]``. Other paths are
    untouched. For the tests that simulate a file system.
    """
    listdir, stat, lstat = os.listdir, os.stat, os.lstat

    def fake(folder, names=(), error=None, aliases=None):
        folder = os.path.normcase(os.path.abspath(folder))
        aliases = aliases or {}

        def here(path):
            # Not realpath: it calls the faked lstat.
            return isinstance(path, (str, os.PathLike)) and (
                os.path.normcase(os.path.abspath(path)) == folder
            )

        def fake_listdir(path="."):
            if not here(path):
                return listdir(path)
            if error is not None:
                raise error
            return [*listdir(path), *names]

        def answer(original):
            def fake_stat(path, *args, **kwargs):
                if here(os.path.dirname(path) if isinstance(path, str) else None):
                    name = os.path.basename(path)
                    if name in aliases:
                        path = os.path.join(os.path.dirname(path), aliases[name])
                return original(path, *args, **kwargs)

            return fake_stat

        monkeypatch.setattr(os, "listdir", fake_listdir)
        monkeypatch.setattr(os, "stat", answer(stat))
        monkeypatch.setattr(os, "lstat", answer(lstat))

    return fake


def remove_build_tree(path):
    for attempt in range(5):
        try:
            shutil.rmtree(path)
            return
        except OSError as error:
            # 32/33: file in use; 145: directory not empty yet (Windows)
            if getattr(error, "winerror", None) not in (32, 33, 145) or attempt == 4:
                raise
            time.sleep(0.05 * 2**attempt)


@pytest.fixture()
def rootdir() -> Path:
    return Path(__file__).parent


@pytest.fixture()
def dir_test_data(rootdir) -> Path:
    return rootdir / "test_data"


@pytest.fixture
def app(make_app, srcdir: Path, confdict: dict):
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
        remove_build_tree(srcdir / "_build")


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
            "matlab_show_property_default_value": True,
        }

        def test_something(app, confdict):
            ...

    If you need to test several confdict in the same test
    you can parametrize things.

    .. code-block:: python

        @pytest.fixture
        def confdict(matlab_auto_link):
            return {"matlab_auto_link": matlab_auto_link}


        @pytest.mark.parametrize("matlab_auto_link", ["basic", "all"])
        def test_something(app, confdict, matlab_auto_link): ...


    or you can also do

    .. code-block:: python

        @pytest.mark.parametrize(
            "confdict",
            [
                {"matlab_show_property_specs": True, "matlab_auto_link": "basic"},
                {"matlab_show_property_specs": True, "matlab_auto_link": "all"},
            ],
        )
        def test_something(app, confdict): ...
    """
    return {}
