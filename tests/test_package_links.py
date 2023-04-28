# -*- coding: utf-8 -*-
"""
    test_package_links.py
    ~~~~~~~~~~~~

    Test the autodoc extension.

    :copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import pickle
import os
import sys

import pytest

from sphinx import addnodes
from sphinx import version_info
from sphinx.testing.fixtures import test_params, make_app
from sphinx.testing.path import path


@pytest.fixture(scope="module")
def rootdir():
    return path(os.path.dirname(__file__)).abspath()


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_with_prefix(make_app, rootdir):
    # TODO: bases are shown without prefix
    srcdir = rootdir / "roots" / "test_package_links"
    confdict = {"matlab_keep_package_prefix": True}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "contents.doctree").read_bytes())

    assert (
        content[5].astext()
        == "class +replab.Action\n\nBases: +replab.Str\n\nAn action group"
        " …\n\nMethod Summary\n\n\n\n\n\nleftAction(self, g, p)\n\nReturns the left action"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_without_prefix(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_package_links"
    confdict = {"matlab_keep_package_prefix": False}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "contents.doctree").read_bytes())

    assert (
        content[5].astext()
        == "class replab.Action\n\nBases: replab.Str\n\nAn action group …\n\nMethod Summary\n\n\n\n\n\nleftAction(self, g, p)\n\nReturns the left action"
    )


if __name__ == "__main__":
    pytest.main([__file__])
