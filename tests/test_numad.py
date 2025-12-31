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
from sphinx.testing.fixtures import make_app, test_params  # noqa: F811;


@pytest.fixture(scope="module")
def rootdir():
    return helper.rootdir(__file__)


def test_first(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_numad"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_first.doctree").read_bytes())
    assert (
        content.astext()
        == "First Class\n\n\n\nclass target.FirstClass\n\nFirst class with two properties\n\nProperty Summary\n\n\n\n\n\na\n\nThe a property\n\n\n\nb\n\nThe b property\n\n\n\nFirstClass.a\n\nThe a property\n\n\n\nFirstClass.b\n\nThe b property"
    )


def test_second(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_numad"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_second.doctree").read_bytes())
    assert (
        content.astext()
        == "Second Class\n\n\n\nclass target.SecondClass\n\nSecond class with methods and properties\n\nConstructor Summary\n\n\n\n\n\nSecondClass(a)\n\nThe second class constructor\n\nProperty Summary\n\n\n\n\n\na\n\nThe a property\n\n\n\nb\n\nThe b property\n\nMethod Summary\n\n\n\n\n\nfirst_method(b)\n\n"
    )


if __name__ == "__main__":
    pytest.main([__file__])
