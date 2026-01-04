"""test_autodoc.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import helper
import pytest
from sphinx import addnodes


@pytest.fixture
def app(make_app):
    srcdir = helper.rootdir(__file__) / "roots" / "test_pymat"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()
    return app


def test_setup(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[3], addnodes.desc)
    assert content[3].astext() == "func.main()\n\nReturn the answer."

    assert isinstance(content[7], addnodes.desc)
    assert content[7].astext() == "matsrc.func(x)\n\nReturns x"
