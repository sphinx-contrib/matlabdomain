"""Test autodoc when code base contains both matlab and python
code in the same folder.
"""

import pickle

import pytest
from sphinx import addnodes


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_pymat_common_root"


def test_pymat_common_root(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[4], addnodes.desc)
    assert content[4].astext().startswith("class base.PythonClass.PythonClass")

    assert isinstance(content[8], addnodes.desc)
    assert content[8].astext().startswith("class base.MatlabClass")
