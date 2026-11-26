"""Test autodoc of a project with MATLAB and Python code in separate folders."""

import pickle

import pytest
from sphinx import addnodes


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_python_and_matlab"


def test_python_and_matlab(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    # python code
    assert isinstance(content[3], addnodes.desc)
    assert content[3].astext() == "func.main()\n\nReturn the answer."

    # matlab code
    assert isinstance(content[7], addnodes.desc)
    assert content[7].astext() == "func(x)\n\nReturns x"
