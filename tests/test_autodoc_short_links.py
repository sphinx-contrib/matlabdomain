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
    confdict = {"matlab_short_links": True}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())
    property_section = content[0][2][1][2][0]  # a bit fragile, I know
    method_section = content[0][2][1][2][1]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        content[0].astext()
        == "target\n\n\n\nclass ClassExample(a)\n\nBases: handle\n\nExample class\n\nClassExample Properties:\n\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample\n\nClassExample Methods:\n\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n\nSee also BaseClass, baseFunction, unknownEntity.\n\nProperty Summary\n\n\n\n\n\na\n\na property\n\n\n\nb\n\na property with default value\n\n\n\nc\n\na property with multiline default value\n\nMethod Summary\n\n\n\n\n\nmymethod(b)\n\nA method in ClassExample\n\nParameters\n\nb – an input to mymethod()"
    )
    assert (
        property_section.rawsource
        == "ClassExample Properties:\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample"
    )
    assert (
        method_section.rawsource
        == "ClassExample Methods:\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_target_show_default_value(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True, "matlab_show_property_default_value": True}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())
    property_section = content[0][2][1][2][0]  # a bit fragile, I know
    method_section = content[0][2][1][2][1]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        content[0].astext()
        == "target\n\n\n\nclass ClassExample(a)\n\nBases: handle\n\nExample class\n\nClassExample Properties:\n\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample\n\nClassExample Methods:\n\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n\nSee also BaseClass, baseFunction, unknownEntity.\n\nProperty Summary\n\n\n\n\n\na\n\na property\n\n\n\nb = 10\n\na property with default value\n\n\n\nc = [10; ... 30]\n\na property with multiline default value\n\nMethod Summary\n\n\n\n\n\nmymethod(b)\n\nA method in ClassExample\n\nParameters\n\nb – an input to mymethod()"
    )
    assert (
        property_section.rawsource
        == "ClassExample Properties:\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample"
    )
    assert (
        method_section.rawsource
        == "ClassExample Methods:\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_target_auto_link_basic(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True, "matlab_auto_link": "basic"}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())
    property_section = content[0][2][1][2][0]  # a bit fragile, I know
    method_section = content[0][2][1][2][1]  # a bit fragile, I know
    see_also_line = content[0][2][1][3]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        property_section.rawsource
        == "ClassExample Properties:\n* :attr:`a <ClassExample.a>` - first property of ClassExample\n* :attr:`b <ClassExample.b>` - second property of ClassExample\n* :attr:`c <ClassExample.c>` - third property of ClassExample"
    )
    assert (
        method_section.rawsource
        == "ClassExample Methods:\n* :meth:`ClassExample() <ClassExample.ClassExample>` - the constructor and a reference to mymethod()\n* :meth:`mymethod() <ClassExample.mymethod>` - a method in ClassExample\n"
    )
    assert (
        see_also_line.rawsource
        == "See also :class:`BaseClass`, :func:`baseFunction`, ``unknownEntity``."
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_target_auto_link_all(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True, "matlab_auto_link": "all"}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())
    property_section = content[0][2][1][2][0]  # a bit fragile, I know
    method_section = content[0][2][1][2][1]  # a bit fragile, I know
    see_also_line = content[0][2][1][3]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        property_section.rawsource
        == "ClassExample Properties:\n* :attr:`a <ClassExample.a>` - first property of :class:`ClassExample`\n* :attr:`b <ClassExample.b>` - second property of :class:`ClassExample`\n* :attr:`c <ClassExample.c>` - third property of :class:`ClassExample`"
    )
    assert (
        method_section.rawsource
        == "ClassExample Methods:\n* :meth:`ClassExample() <ClassExample.ClassExample>` - the constructor and a reference to :meth:`mymethod() <ClassExample.mymethod>`\n* :meth:`mymethod() <ClassExample.mymethod>` - a method in :class:`ClassExample`\n"
    )
    assert (
        see_also_line.rawsource
        == "See also :class:`BaseClass`, :func:`baseFunction`, ``unknownEntity``."
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_classfolder(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_classfolder.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "classfolder\n\n\n\nclass ClassFolder(p)\n\nA class in a folder\n\nProperty Summary\n\n\n\n\n\np\n\na property of a class folder\n\nMethod Summary\n\n\n\n\n\nmethod_inside_classdef(a, b)\n\nMethod inside class definition"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_package(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_package.doctree").read_bytes())
    docstring1 = content[0][2][1][1]  # a bit fragile, I know
    docstring2 = content[0][2][1][2][0][1][1][4][1][0]  # a bit fragile, I know
    docstring3 = content[0][2][1][2][0][2][1][2][1][0]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        content[0].astext()
        == "package\n\n\n\nclass package.ClassBar\n\nBases: handle\n\nThe Bar and Foo handler, with a doFoo() method.\n\nConstructor Summary\n\n\n\n\n\nClassBar()\n\nInitialize the bars and foos\n\nProperty Summary\n\n\n\n\n\nbars\n\nNumber of bars\n\n\n\nfoos\n\nNumber of foos, used by doBar() method\n\nMethod Summary\n\n\n\n\n\ndoBar()\n\nDoing bar, not called by ClassBar()\n\n\n\ndoFoo()\n\nDoing foo\n\n\n\n\n\n\n\npackage.funcFoo(u, t)\n\nFunction that does Foo\n\nx = package.funcFoo(u)\n[x, y] = package.funcFoo(u, t)\n\nTest for auto-linking with baseFunction and BaseClass, etc."
    )
    assert docstring1.rawsource == "The Bar and Foo handler, with a doFoo() method."
    assert docstring2.rawsource == "Number of foos, used by doBar() method"
    assert docstring3.rawsource == "Doing bar, not called by ClassBar()"


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_package_show_default_value(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True, "matlab_show_property_default_value": True}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_package.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "package\n\n\n\nclass package.ClassBar\n\nBases: handle\n\nThe Bar and Foo handler, with a doFoo() method.\n\nConstructor Summary\n\n\n\n\n\nClassBar()\n\nInitialize the bars and foos\n\nProperty Summary\n\n\n\n\n\nbars = 'bars'\n\nNumber of bars\n\n\n\nfoos = 10\n\nNumber of foos, used by doBar() method\n\nMethod Summary\n\n\n\n\n\ndoBar()\n\nDoing bar, not called by ClassBar()\n\n\n\ndoFoo()\n\nDoing foo\n\n\n\n\n\n\n\npackage.funcFoo(u, t)\n\nFunction that does Foo\n\nx = package.funcFoo(u)\n[x, y] = package.funcFoo(u, t)\n\nTest for auto-linking with baseFunction and BaseClass, etc."
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_package_auto_link_all(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True, "matlab_auto_link": "all"}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_package.doctree").read_bytes())
    docstring1 = content[0][2][1][1]  # a bit fragile, I know
    docstring2 = content[0][2][1][2][0][1][1][4][1][0]  # a bit fragile, I know
    docstring3 = content[0][2][1][2][0][2][1][2][1][0]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        content[0].astext()
        == "package\n\n\n\nclass package.ClassBar\n\nBases: handle\n\nThe Bar and Foo handler, with a doFoo() method.\n\nConstructor Summary\n\n\n\n\n\nClassBar()\n\nInitialize the bars and foos\n\nProperty Summary\n\n\n\n\n\nbars\n\nNumber of bars\n\n\n\nfoos\n\nNumber of foos, used by doBar() method\n\nMethod Summary\n\n\n\n\n\ndoBar()\n\nDoing bar, not called by ClassBar()\n\n\n\ndoFoo()\n\nDoing foo\n\n\n\n\n\n\n\npackage.funcFoo(u, t)\n\nFunction that does Foo\n\nx = package.funcFoo(u)\n[x, y] = package.funcFoo(u, t)\n\nTest for auto-linking with baseFunction() and BaseClass, etc."
    )
    assert (
        docstring1.rawsource
        == "The Bar and Foo handler, with a :meth:`doFoo() <package.ClassBar.doFoo>` method."
    )
    assert (
        docstring2.rawsource
        == "Number of foos, used by :meth:`doBar() <package.ClassBar.doBar>` method"
    )
    assert (
        docstring3.rawsource
        == "Doing bar, not called by :meth:`ClassBar() <package.ClassBar.ClassBar>`"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_submodule(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_submodule.doctree").read_bytes())
    bases_line = content[0][2][1][0]
    assert len(content) == 1
    assert (
        content[0].astext()
        == "submodule\n\n\n\nclass ClassMeow\n\nBases: package.ClassBar\n\nClass which inherits from a package\n\nMethod Summary\n\n\n\n\n\nsay()\n\nSay Meow\n\n\n\nfuncMeow(input)\n\nTests a function with comments after docstring"
    )
    assert bases_line.rawsource == "Bases: :class:`package.ClassBar`"


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_submodule_show_default_value(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True, "matlab_show_property_default_value": True}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_submodule.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "submodule\n\n\n\nclass ClassMeow\n\nBases: package.ClassBar\n\nClass which inherits from a package\n\nMethod Summary\n\n\n\n\n\nsay()\n\nSay Meow\n\n\n\nfuncMeow(input)\n\nTests a function with comments after docstring"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_root(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "root\n\n\n\nclass BaseClass(args)\n\nA class in the very root of the directory\n\nBaseClass Methods:\n\nBaseClass - the constructor, whose description extends\n\nto the next line\n\nDoBase - another BaseClass method\n\nSee Also\n\ntarget.ClassExample, baseFunction, ClassExample\n\nConstructor Summary\n\n\n\n\n\nBaseClass(args)\n\nThe constructor\n\nMethod Summary\n\n\n\n\n\nDoBase()\n\nDo the Base thing\n\n\n\nbaseFunction(x)\n\nReturn the base of x\n\nSee Also:\n\ntarget.submodule.ClassMeow\ntarget.package.ClassBar\nClassMeow\npackage.ClassBar"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_root_show_default_value(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True, "matlab_show_property_default_value": True}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "root\n\n\n\nclass BaseClass(args)\n\nA class in the very root of the directory\n\nBaseClass Methods:\n\nBaseClass - the constructor, whose description extends\n\nto the next line\n\nDoBase - another BaseClass method\n\nSee Also\n\ntarget.ClassExample, baseFunction, ClassExample\n\nConstructor Summary\n\n\n\n\n\nBaseClass(args)\n\nThe constructor\n\nMethod Summary\n\n\n\n\n\nDoBase()\n\nDo the Base thing\n\n\n\nbaseFunction(x)\n\nReturn the base of x\n\nSee Also:\n\ntarget.submodule.ClassMeow\ntarget.package.ClassBar\nClassMeow\npackage.ClassBar"
    )


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_root_auto_link_basic(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {"matlab_short_links": True, "matlab_auto_link": "basic"}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    method_section = content[0][2][1][1][0]  # a bit fragile, I know
    see_also_line_1 = content[0][2][1][1][1]  # a bit fragile, I know
    see_also_line_2 = content[0][4][1][1][0]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        method_section.rawsource
        == "BaseClass Methods:\n* :meth:`BaseClass() <BaseClass.BaseClass>` - the constructor, whose description extends\n    to the next line\n* :meth:`DoBase() <BaseClass.DoBase>` - another BaseClass method\n"
    )
    assert (
        see_also_line_1.rawsource
        == "See Also\n:class:`target.ClassExample`, :func:`baseFunction`, :class:`ClassExample`\n\n"
    )
    assert (
        see_also_line_2.rawsource
        == "See Also:\n:class:`target.submodule.ClassMeow`\n:class:`target.package.ClassBar`\n:class:`ClassMeow`\n:class:`package.ClassBar`"
    )


if __name__ == "__main__":
    pytest.main([__file__])
