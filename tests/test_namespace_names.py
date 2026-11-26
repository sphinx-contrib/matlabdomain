"""Test that namespaces show their MATLAB names (without the ``+`` prefix).

:copyright: Copyright by the Isaac Lenton.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest
from sphinx import addnodes


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_namespace_names"


def test_namespace_names(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[4], addnodes.desc)
    assert content[4].astext() == "package.func(x)\n\nReturns x"
    assert content[8].astext() == "package.subpkg.func(x)\n\nReturns x"
    assert "WARNING" not in app.warning.getvalue()
