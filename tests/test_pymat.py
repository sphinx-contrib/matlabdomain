# -*- coding: utf-8 -*-
"""
    test_autodoc
    ~~~~~~~~~~~~

    Test the autodoc extension.

    :copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import pickle
import sys
import helper

import pytest

from sphinx import addnodes
from sphinx.testing.fixtures import make_app, test_params  # noqa: F811;


@pytest.fixture(scope="module")
def rootdir():
    return helper.rootdir(__file__)


def test_setup(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_pymat"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[3], addnodes.desc)
    assert content[3].astext() == "func.main()\n\nReturns the answer."

    assert isinstance(content[7], addnodes.desc)
    assert content[7].astext() == "matsrc.func(x)\n\nReturns x"


if __name__ == "__main__":
    pytest.main([__file__])
