"""Test autodoc when code base contains both matlab and python code."""

import pickle

import pytest
from sphinx import addnodes


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_pymat"


def test_pymat(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    # python code
    assert isinstance(content[3], addnodes.desc)
    assert content[3].astext() == "func.main()\n\nReturn the answer."

    # matlab code
    assert isinstance(content[7], addnodes.desc)
    assert content[7].astext() == "matsrc.func(x)\n\nReturns x"
