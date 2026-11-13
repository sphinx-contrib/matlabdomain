"""Test links to the base classes of namespace classes.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_package_links"


def test_package_links(app):
    content = pickle.loads((app.doctreedir / "contents.doctree").read_bytes())

    assert content[5].astext() == (
        "class replab.Action\n\n"
        "Bases: replab.Str\n\n"
        "An action group …\n\n"
        "Method Summary\n\n\n\n\n\n"
        "leftAction(g, p)\n\n"
        "Returns the left action"
    )
