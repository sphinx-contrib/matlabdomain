"""test_autodoc.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_skipping_module_members"


def test_skipping_module_members(app, srcdir):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())
    content_text = content.astext()
    assert "The first function" in content_text
    assert "The second function" not in content_text
