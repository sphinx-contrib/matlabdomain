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
    srcdir = helper.rootdir(__file__) / "roots" / "test_pymat_common_root"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()
    return app


def test_setup(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[4], addnodes.desc)
    assert content[4].astext().startswith("class base.PythonClass.PythonClass")

    assert isinstance(content[8], addnodes.desc)
    assert content[8].astext().startswith("class base.MatlabClass")
