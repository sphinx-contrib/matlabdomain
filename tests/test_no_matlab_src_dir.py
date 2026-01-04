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
    srcdir = helper.rootdir(__file__) / "roots" / "test_no_matlab_src_dir"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()
    return app


def test_make(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())
    assert len(content) == 1
    assert content[0].astext() == "Description\n\nEmpty."
