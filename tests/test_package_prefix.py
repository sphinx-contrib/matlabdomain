"""test_package_function.
~~~~~~~~~~~~~~~~~~~~~

Test the autodoc extension with the matlab_keep_package_prefix option.

:copyright: Copyright by the Isaac Lenton.
:license: BSD, see LICENSE for details.
"""

import pickle

import helper
import pytest
from sphinx import addnodes


@pytest.fixture
def app(make_app, matlab_keep_package_prefix):
    srcdir = helper.rootdir(__file__) / "roots" / "test_package_prefix"
    confdict = {"matlab_keep_package_prefix": matlab_keep_package_prefix}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()
    return app


@pytest.mark.parametrize("matlab_keep_package_prefix", [True, False])
def test_prefix(app, matlab_keep_package_prefix):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[4], addnodes.desc)
    if matlab_keep_package_prefix:
        assert content[4].astext() == "+package.func(x)\n\nReturns x"
    else:
        assert content[4].astext() == "package.func(x)\n\nReturns x"
