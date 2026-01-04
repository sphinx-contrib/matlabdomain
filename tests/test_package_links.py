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


@pytest.fixture
def confdict(matlab_keep_package_prefix):
    return {
        "matlab_keep_package_prefix": matlab_keep_package_prefix,
    }


@pytest.mark.parametrize("matlab_keep_package_prefix", [True, False])
def test_package_links(app, confdict, matlab_keep_package_prefix):
    # TODO: bases are shown without prefix
    content = pickle.loads((app.doctreedir / "contents.doctree").read_bytes())

    expected_content = (
        "class {}replab.Action\n\n"
        "Bases: {}replab.Str\n\n"
        "An action group …\n\n"
        "Method Summary\n\n\n\n\n\n"
        "leftAction(g, p)\n\n"
        "Returns the left action"
    )

    if confdict["matlab_keep_package_prefix"]:
        assert content[5].astext() == expected_content.format("+", "+")
    else:
        assert content[5].astext() == expected_content.format("", "")
