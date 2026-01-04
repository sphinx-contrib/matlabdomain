"""test_autodoc.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import helper
import pytest


@pytest.fixture(scope="module")
def rootdir():
    return helper.rootdir(__file__)


def test_make(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_no_matlab_src_dir"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())
    assert len(content) == 1
    assert content[0].astext() == "Description\n\nEmpty."
