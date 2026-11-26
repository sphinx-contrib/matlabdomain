"""Test autodoc of a project with MATLAB and Python code in one folder."""

import pickle

import pytest
from sphinx import addnodes


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_python_and_matlab_one_folder"


def test_python_and_matlab_one_folder(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[4], addnodes.desc)
    assert content[4].astext().startswith("class base.PythonClass.PythonClass")

    assert isinstance(content[8], addnodes.desc)
    assert content[8].astext().startswith("class MatlabClass")
