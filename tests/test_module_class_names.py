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
import docutils


@pytest.fixture(scope="module")
def rootdir():
    return helper.rootdir(__file__)


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_myclass(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_module_class_names"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "myclass.doctree").read_bytes())
    assert (
        content.astext()
        == "Myclass\n\n\n\nclass Myclass\n\nMyclass\n\nSee Also: YourClass\n\nConstructor Summary\n\n\n\n\n\nMyclass()\n\n\n\nProperty Summary\n\n\n\n\n\nprop\n\nThe property\n\nMethod Summary\n\n\n\n\n\nadd(value)\n\nAdd the value"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_yourclass(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_module_class_names"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "yourclass.doctree").read_bytes())
    assert (
        content.astext()
        == "YourClass\n\n\n\nclass YourClass\n\nYourClass\n\nSee Also: Myclass\n\nConstructor Summary\n\n\n\n\n\nYourClass()\n\n\n\nProperty Summary\n\n\n\n\n\nprop\n\nThe property\n\nMethod Summary\n\n\n\n\n\nadd(value)\n\nAdd the value"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_myclass_auto_link_all(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_module_class_names"
    confdict = {"matlab_auto_link": "all"}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "myclass.doctree").read_bytes())
    assert (
        content.astext()
        == "Myclass\n\n\n\nclass Myclass\n\nMyclass\n\nSee Also: YourClass\n\nConstructor Summary\n\n\n\n\n\nMyclass()\n\n\n\nProperty Summary\n\n\n\n\n\nprop\n\nThe property\n\nMethod Summary\n\n\n\n\n\nadd(value)\n\nAdd the value"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_yourclass_auto_link_all(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_module_class_names"
    confdict = {"matlab_auto_link": "all"}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "yourclass.doctree").read_bytes())
    assert (
        content.astext()
        == "YourClass\n\n\n\nclass YourClass\n\nYourClass\n\nSee Also: Myclass\n\nConstructor Summary\n\n\n\n\n\nYourClass()\n\n\n\nProperty Summary\n\n\n\n\n\nprop\n\nThe property\n\nMethod Summary\n\n\n\n\n\nadd(value)\n\nAdd the value"
    )


if __name__ == "__main__":
    pytest.main([__file__])
