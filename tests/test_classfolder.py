# -*- coding: utf-8 -*-
"""
    test_autodoc
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
def test_first(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_classfolder"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_first.doctree").read_bytes())
    assert (
        content[0].astext()
        == "First\n\n\n\nclass First\n\nThe first class\n\nConstructor Summary\n\n\n\n\n\nFirst(a)\n\nConstructor for First\n\nProperty Summary\n\n\n\n\n\na\n\nThe property\n\nMethod Summary\n\n\n\n\n\nmethod_in_folder(varargin)\n\nA method defined in the folder\n\n\n\nmethod_inside_classdef(b)\n\nMethod inside class definition"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_second(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_classfolder"
    app = make_app(srcdir=srcdir)
    app.builder.build_all

    content = pickle.loads((app.doctreedir / "index_second.doctree").read_bytes())
    assert (
        content[0].astext()
        == "Second\n\n\n\nclass Second\n\nThe second class\n\nConstructor Summary\n\n\n\n\n\nSecond(b)\n\nConstructor for Second\n\nProperty Summary\n\n\n\n\n\nb\n\na property of a class folder\n\nMethod Summary\n\n\n\n\n\nmethod_in_folder(varargin)\n\nA method defined in the folder\n\n\n\nmethod_inside_classdef(c)\n\nMethod inside class definition"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_third(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_classfolder"
    app = make_app(srcdir=srcdir)
    app.builder.build_all

    content = pickle.loads((app.doctreedir / "index_third.doctree").read_bytes())
    assert (
        content[0].astext()
        == "Third\n\n\n\nclass Third\n\nThe third class\n\nConstructor Summary\n\n\n\n\n\nThird(c)\n\nConstructor for Third\n\nProperty Summary\n\n\n\n\n\nc\n\na property of a class folder\n\nMethod Summary\n\n\n\n\n\nmethod_in_folder(varargin)\n\nA method defined in the folder\n\n\n\nmethod_inside_classdef(d)\n\nMethod inside class definition"
    )
