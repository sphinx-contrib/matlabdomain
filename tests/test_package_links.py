"""test_package_links.py.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_package_links"


@pytest.mark.parametrize(
    "confdict",
    [{"matlab_keep_package_prefix": True}, {"matlab_keep_package_prefix": False}],
)
def test_package_links(app, confdict):
    # TODO: bases are shown without prefix
    content = pickle.loads((app.doctreedir / "contents.doctree").read_bytes())

    if confdict["matlab_keep_package_prefix"]:
        assert (
            content[5].astext()
            == "class +replab.Action\n\nBases: +replab.Str\n\nAn action group …\n\nMethod Summary\n\n\n\n\n\nleftAction(g, p)\n\nReturns the left action"
        )
    else:
        assert (
            content[5].astext()
            == "class replab.Action\n\nBases: replab.Str\n\nAn action group …\n\nMethod Summary\n\n\n\n\n\nleftAction(g, p)\n\nReturns the left action"
        )
