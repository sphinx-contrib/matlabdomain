"""Test that an ``autodoc-skip-member`` handler can skip a member of a folder."""

import pickle

import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_skip_member"


def test_skip_member(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())
    content_text = content.astext()
    assert "The first function" in content_text
    assert "The second function" not in content_text
