"""test_autodoc.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import helper
import pytest
from sphinx import addnodes


@pytest.fixture(scope="module")
def rootdir():
    return helper.rootdir(__file__)


def test_setup(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_pymat_common_root"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[4], addnodes.desc)
    assert content[4].astext().startswith("class base.PythonClass.PythonClass")

    assert isinstance(content[8], addnodes.desc)
    assert content[8].astext().startswith("class base.MatlabClass")


if __name__ == "__main__":
    pytest.main([__file__])
