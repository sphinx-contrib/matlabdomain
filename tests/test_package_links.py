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

    expected_content = (
        "class {}replab.Action\n\nBases: {}replab.Str\n\n"
        "An action group …\n\nMethod Summary\n\n\n\n\n\n"
        "leftAction(g, p)\n\nReturns the left action"
    )

    if confdict["matlab_keep_package_prefix"]:
        assert content[5].astext() == expected_content.format("+", "+")
    else:
        assert content[5].astext() == expected_content.format("", "")
