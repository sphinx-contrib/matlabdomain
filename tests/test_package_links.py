"""test_package_links.py.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import helper
import pytest


@pytest.fixture
def app(make_app, matlab_keep_package_prefix):
    srcdir = helper.rootdir(__file__) / "roots" / "test_package_links"
    confdict = {"matlab_keep_package_prefix": matlab_keep_package_prefix}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()
    return app


@pytest.mark.parametrize("matlab_keep_package_prefix", [True, False])
def test_with_prefix(app, matlab_keep_package_prefix):
    # TODO: bases are shown without prefix
    content = pickle.loads((app.doctreedir / "contents.doctree").read_bytes())

    if matlab_keep_package_prefix is True:
        assert (
            content[5].astext()
            == "class +replab.Action\n\nBases: +replab.Str\n\nAn action group …\n\nMethod Summary\n\n\n\n\n\nleftAction(g, p)\n\nReturns the left action"
        )
    else:
        assert (
            content[5].astext()
            == "class replab.Action\n\nBases: replab.Str\n\nAn action group …\n\nMethod Summary\n\n\n\n\n\nleftAction(g, p)\n\nReturns the left action"
        )
