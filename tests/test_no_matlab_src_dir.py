# -*- coding: utf-8 -*-
"""
    test_autodoc
    ~~~~~~~~~~~~

    Test the autodoc extension.

    :copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import pickle
import os
import sys
import helper

import pytest

from sphinx import addnodes
from sphinx.testing.fixtures import make_app, test_params  # noqa: F811;


@pytest.fixture(scope="module")
def rootdir():
    return helper.rootdir(__file__)


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_make(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_no_matlab_src_dir"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())
    assert len(content) == 1
    assert content[0].astext() == "Description\n\nEmpty."


if __name__ == "__main__":
    pytest.main([__file__])
