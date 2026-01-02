"""test_package_function.
~~~~~~~~~~~~~~~~~~~~~

Test the autodoc extension with the matlab_keep_package_prefix option.

:copyright: Copyright 2019 by the Isaac Lenton.
:license: BSD, see LICENSE for details.
"""

import pickle

import helper
import pytest
from sphinx import addnodes


@pytest.fixture(scope="module")
def rootdir():
    return helper.rootdir(__file__)


def test_with_prefix(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_package_prefix"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[4], addnodes.desc)
    assert content[4].astext() == "+package.func(x)\n\nReturns x"


def test_without_prefix(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_package_prefix"
    confdict = {"matlab_keep_package_prefix": False}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[4], addnodes.desc)
    assert content[4].astext() == "package.func(x)\n\nReturns x"


if __name__ == "__main__":
    pytest.main([__file__])
