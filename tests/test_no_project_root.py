"""Test a build without ``matlab_src_code_project_root``."""

import pickle

import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_no_project_root"


def test_no_project_root(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert len(content) == 1
    assert content[0].astext() == "Description\n\nEmpty."
