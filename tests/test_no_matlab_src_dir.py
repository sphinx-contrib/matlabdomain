"""Test when no matlab_src_dir is present."""

import pickle

import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_no_matlab_src_dir"


def test_no_matlab_src_dir(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert len(content) == 1
    assert content[0].astext() == "Description\n\nEmpty."
