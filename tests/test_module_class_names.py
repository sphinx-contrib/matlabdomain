# -*- coding: utf-8 -*-
"""
    test_class_subfolder
    ~~~~~~~~~~~~

    Test the autodoc extension.

    :copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import pickle
import sys
import pytest
import helper
from sphinx import addnodes
from sphinx.testing.fixtures import make_app, test_params  # noqa: F811;


@pytest.fixture(scope="module")
def rootdir():
    return helper.rootdir(__file__)


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_index(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_module_class_names"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())
    assert (
        content.astext()
        == "\n\n\n\n\n\nclass Myclass.Myclass\n\nmytest\n\nProperty Summary\n\n\n\n\n\nprop\n\nprop\n\nMethod Summary\n\n\n\n\n\nf()\n\nfunction\n\nOther\n\n"
    )


if __name__ == "__main__":
    pytest.main([__file__])
