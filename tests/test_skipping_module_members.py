"""test_autodoc.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import helper
import pytest


@pytest.fixture
def app(make_app):
    srcdir = helper.rootdir(__file__) / "roots" / "test_skipping_module_members"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()
    return app


def test_setup(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())
    content_text = content.astext()
    assert "The first function" in content_text
    assert "The second function" not in content_text
