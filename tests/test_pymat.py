"""test_autodoc.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest
from sphinx import addnodes


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_pymat"


def test_pymat(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[3], addnodes.desc)
    assert content[3].astext() == "func.main()\n\nReturn the answer."

    assert isinstance(content[7], addnodes.desc)
    assert content[7].astext() == "matsrc.func(x)\n\nReturns x"
