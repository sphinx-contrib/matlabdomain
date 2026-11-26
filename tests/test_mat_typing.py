"""``override`` comes from ``typing``, or from ``typing_extensions`` before
Python 3.12. One Python runs one of the two imports; with
``--simulate-platforms`` the other one runs too.
"""

import importlib
import sys
import types
import typing

import pytest

from sphinxcontrib import mat_typing


def marker(method):
    return method


@pytest.mark.parametrize(
    ("version", "module"), [((3, 11), "typing_extensions"), ((3, 12), "typing")]
)
def test_override_comes_from_the_module_of_the_python_version(
    monkeypatch, condition, version, module
):
    real = (sys.version_info >= (3, 12)) == (version >= (3, 12))
    needs = f"Python {'>= 3.12' if version >= (3, 12) else '< 3.12'}"
    if condition(needs, real) == "real":
        assert mat_typing.override is importlib.import_module(module).override
        return
    if module == "typing":
        monkeypatch.setattr(typing, "override", marker, raising=False)
    else:
        stand_in = types.ModuleType(module)
        monkeypatch.setattr(stand_in, "override", marker, raising=False)
        monkeypatch.setitem(sys.modules, module, stand_in)
    monkeypatch.setattr(sys, "version_info", (*version, 0, "final", 0))
    try:
        assert importlib.reload(mat_typing).override is marker
    finally:
        monkeypatch.undo()
        importlib.reload(mat_typing)
    assert mat_typing.override is not marker
