# -*- coding: utf-8 -*-
"""
    test_autodoc
    ~~~~~~~~~~~~

    Test the autodoc extension.

    :copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import pickle
import os
import sys

import pytest

from sphinx import addnodes
from sphinx.testing.fixtures import make_app, test_params  # noqa: F811;
from sphinx.testing.path import path


@pytest.fixture(scope="module")
def rootdir():
    return path(os.path.dirname(__file__)).abspath()


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_target(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "target\n\n\n\nclass target.ClassExample(a)\n\nBases: handle\n\nExample class\n\nParameters\n\na – first property of ClassExample\n\nb – second property of ClassExample\n\nc – third property of ClassExample\n\nProperty Summary\n\n\n\n\n\na\n\na property\n\n\n\nb\n\na property with default value\n\n\n\nc\n\na property with multiline default value\n\nMethod Summary\n\n\n\n\n\nmymethod(b)\n\nA method in ClassExample\n\nParameters\n\nb – an input to mymethod()"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_target_show_default_value(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    app = make_app(
        srcdir=srcdir, confoverrides={"matlab_show_property_default_value": True}
    )
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "target\n\n\n\nclass target.ClassExample(a)\n\nBases: handle\n\nExample class\n\nParameters\n\na – first property of ClassExample\n\nb – second property of ClassExample\n\nc – third property of ClassExample\n\nProperty Summary\n\n\n\n\n\na\n\na property\n\n\n\nb = 10\n\na property with default value\n\n\n\nc = [10; ... 30]\n\na property with multiline default value\n\nMethod Summary\n\n\n\n\n\nmymethod(b)\n\nA method in ClassExample\n\nParameters\n\nb – an input to mymethod()"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_classfolder(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_classfolder.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "classfolder\n\n\n\nclass target.@ClassFolder.ClassFolder(p)\n\nA class in a folder\n\nProperty Summary\n\n\n\n\n\np\n\na property of a class folder\n\nMethod Summary\n\n\n\n\n\nmethod_inside_classdef(a, b)\n\nMethod inside class definition"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_package(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_package.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "package\n\n\n\nclass target.package.ClassBar\n\nBases: handle\n\nThe Bar and Foo handler\n\nConstructor Summary\n\n\n\n\n\nClassBar()\n\nInitialize the bars and foos\n\nProperty Summary\n\n\n\n\n\nbars\n\nNumber of bars\n\n\n\nfoos\n\nNumber of foos\n\nMethod Summary\n\n\n\n\n\ndoBar()\n\nDoing bar\n\n\n\ndoFoo()\n\nDoing foo\n\n\n\n\n\n\n\ntarget.package.funcFoo(u, t)\n\nFunction that does Foo"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_package_show_default_value(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    app = make_app(
        srcdir=srcdir, confoverrides={"matlab_show_property_default_value": True}
    )
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_package.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "package\n\n\n\nclass target.package.ClassBar\n\nBases: handle\n\nThe Bar and Foo handler\n\nConstructor Summary\n\n\n\n\n\nClassBar()\n\nInitialize the bars and foos\n\nProperty Summary\n\n\n\n\n\nbars = 'bars'\n\nNumber of bars\n\n\n\nfoos = 10\n\nNumber of foos\n\nMethod Summary\n\n\n\n\n\ndoBar()\n\nDoing bar\n\n\n\ndoFoo()\n\nDoing foo\n\n\n\n\n\n\n\ntarget.package.funcFoo(u, t)\n\nFunction that does Foo"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_submodule(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_submodule.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "submodule\n\n\n\nclass target.submodule.ClassMeow\n\nBases: package.ClassBar\n\nClass which inherits from a package\n\nMethod Summary\n\n\n\n\n\nsay()\n\nSay Meow\n\n\n\ntarget.submodule.funcMeow(input)\n\nTests a function with comments after docstring"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_submodule_show_default_value(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    app = make_app(
        srcdir=srcdir, confoverrides={"matlab_show_property_default_value": True}
    )
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_submodule.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "submodule\n\n\n\nclass target.submodule.ClassMeow\n\nBases: package.ClassBar\n\nClass which inherits from a package\n\nMethod Summary\n\n\n\n\n\nsay()\n\nSay Meow\n\n\n\ntarget.submodule.funcMeow(input)\n\nTests a function with comments after docstring"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_root(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "root\n\n\n\nclass BaseClass(args)\n\nA class in the very root of the directory\n\nConstructor Summary\n\n\n\n\n\nBaseClass(args)\n\nThe constructor\n\nMethod Summary\n\n\n\n\n\nDoBase()\n\nDo the Base thing\n\n\n\nbaseFunction(x)\n\nReturn the base of x"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_root_show_default_value(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    app = make_app(
        srcdir=srcdir, confoverrides={"matlab_show_property_default_value": True}
    )
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "root\n\n\n\nclass BaseClass(args)\n\nA class in the very root of the directory\n\nConstructor Summary\n\n\n\n\n\nBaseClass(args)\n\nThe constructor\n\nMethod Summary\n\n\n\n\n\nDoBase()\n\nDo the Base thing\n\n\n\nbaseFunction(x)\n\nReturn the base of x"
    )


if __name__ == "__main__":
    pytest.main([__file__])
