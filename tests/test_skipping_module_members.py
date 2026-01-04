"""test_autodoc.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import helper
import pytest


@pytest.fixture(scope="module")
def rootdir():
    return helper.rootdir(__file__)


def test_setup(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_skipping_module_members"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())
    content_text = content.astext()
    assert "The first function" in content_text
    assert "The second function" not in content_text
