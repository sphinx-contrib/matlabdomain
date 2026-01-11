"""test_autodoc.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest


def test_target(app):
    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())
    property_section = content[0][2][1][2][0]  # a bit fragile, I know
    method_section = content[0][2][1][2][1]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        content[0].astext()
        == "target\n\n\n\nclass target.ClassExample\n\nBases: handle\n\nExample class\n\nClassExample Properties:\n\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample\n\nClassExample Methods:\n\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n\nSee also BaseClass, baseFunction, b, unknownEntity, mymethod,\npackage.ClassBar.bars, package.ClassBar.doFoo.\n\nConstructor Summary\n\n\n\n\n\nClassExample(a)\n\nLinks to fully qualified names package.ClassBar.foos,\npackage.ClassBar.doBar, and ClassExample.mymethod.\n\nProperty Summary\n\n\n\n\n\na\n\na property\n\n\n\nb\n\na property with default value\n\n\n\nc\n\na property with multiline default value\n\nMethod Summary\n\n\n\n\n\nmymethod(b)\n\nA method in ClassExample\n\nParameters\n\nb – an input to mymethod()"
    )
    assert (
        property_section.rawsource
        == "ClassExample Properties:\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample"
    )
    assert (
        method_section.rawsource
        == "ClassExample Methods:\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n"
    )


@pytest.mark.parametrize("confdict", [{"matlab_show_property_default_value": True}])
def test_target_show_default_value(app, confdict):
    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())
    property_section = content[0][2][1][2][0]  # a bit fragile, I know
    method_section = content[0][2][1][2][1]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        content[0].astext()
        == "target\n\n\n\nclass target.ClassExample\n\nBases: handle\n\nExample class\n\nClassExample Properties:\n\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample\n\nClassExample Methods:\n\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n\nSee also BaseClass, baseFunction, b, unknownEntity, mymethod,\npackage.ClassBar.bars, package.ClassBar.doFoo.\n\nConstructor Summary\n\n\n\n\n\nClassExample(a)\n\nLinks to fully qualified names package.ClassBar.foos,\npackage.ClassBar.doBar, and ClassExample.mymethod.\n\nProperty Summary\n\n\n\n\n\na = 42\n\na property\n\n\n\nb = 10\n\na property with default value\n\n\n\nc = [10; ... 30]\n\na property with multiline default value\n\nMethod Summary\n\n\n\n\n\nmymethod(b)\n\nA method in ClassExample\n\nParameters\n\nb – an input to mymethod()"
    )
    assert (
        property_section.rawsource
        == "ClassExample Properties:\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample"
    )
    assert (
        method_section.rawsource
        == "ClassExample Methods:\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n"
    )


@pytest.mark.parametrize("confdict", [{"matlab_auto_link": "basic"}])
def test_target_auto_link_basic(app, confdict):
    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())
    property_section = content[0][2][1][2][0]  # a bit fragile, I know
    method_section = content[0][2][1][2][1]  # a bit fragile, I know
    see_also_line = content[0][2][1][3]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        property_section.rawsource
        == "ClassExample Properties:\n* :attr:`a <target.ClassExample.a>` - first property of ClassExample\n* :attr:`b <target.ClassExample.b>` - second property of ClassExample\n* :attr:`c <target.ClassExample.c>` - third property of ClassExample"
    )
    assert (
        method_section.rawsource
        == "ClassExample Methods:\n* :meth:`ClassExample() <target.ClassExample.ClassExample>` - the constructor and a reference to mymethod()\n* :meth:`mymethod() <target.ClassExample.mymethod>` - a method in ClassExample\n"
    )
    assert (
        see_also_line.rawsource
        == "See also :class:`BaseClass`, :func:`baseFunction`, :attr:`b <target.ClassExample.b>`, ``unknownEntity``, :meth:`mymethod() <target.ClassExample.mymethod>`,\n:attr:`package.ClassBar.bars`, :meth:`package.ClassBar.doFoo`."
    )


@pytest.mark.parametrize("confdict", [{"matlab_auto_link": "all"}])
def test_target_auto_link_all(app, confdict):
    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())
    property_section = content[0][2][1][2][0]  # a bit fragile, I know
    method_section = content[0][2][1][2][1]  # a bit fragile, I know
    see_also_line = content[0][2][1][3]  # a bit fragile, I know
    constructor_desc = content[0][2][1][4][0][0][1][2][1][0]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        property_section.rawsource
        == "ClassExample Properties:\n* :attr:`a <target.ClassExample.a>` - first property of :class:`ClassExample`\n* :attr:`b <target.ClassExample.b>` - second property of :class:`ClassExample`\n* :attr:`c <target.ClassExample.c>` - third property of :class:`ClassExample`"
    )
    assert (
        method_section.rawsource
        == "ClassExample Methods:\n* :meth:`ClassExample() <target.ClassExample.ClassExample>` - the constructor and a reference to :meth:`mymethod() <target.ClassExample.mymethod>`\n* :meth:`mymethod() <target.ClassExample.mymethod>` - a method in :class:`ClassExample`\n"
    )
    assert (
        see_also_line.rawsource
        == "See also :class:`BaseClass`, :func:`baseFunction`, :attr:`b <target.ClassExample.b>`, ``unknownEntity``, :meth:`mymethod() <target.ClassExample.mymethod>`,\n:attr:`package.ClassBar.bars`, :meth:`package.ClassBar.doFoo`."
    )
    assert (
        constructor_desc.rawsource
        == "Links to fully qualified names :attr:`package.ClassBar.foos`,\n:meth:`package.ClassBar.doBar`, and :meth:`ClassExample.mymethod`."
    )


def test_classfolder(app):
    content = pickle.loads((app.doctreedir / "index_classfolder.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "classfolder\n\n\n\nclass target.@ClassFolder.ClassFolder\n\nA class in a folder\n\nProperty Summary\n\n\n\n\n\np\n\na property of a class folder\n\nMethod Summary\n\n\n\n\n\na_static_func(args)\n\nA static method in @ClassFolder\n\n\n\nclassMethod(varargin)\n\nCLASSMETHOD A function within a package\n\nParameters\n\nobj – An instance of this class.\n\nvarargin – Variable input arguments.\n\nReturns\n\nvarargout\n\n\n\nmethod_inside_classdef(a, b)\n\nMethod inside class definition"
    )


def test_package(app):
    content = pickle.loads((app.doctreedir / "index_package.doctree").read_bytes())
    docstring1 = content[0][2][1][1]  # a bit fragile, I know
    docstring2 = content[0][2][1][2][0][1][1][4][1][0]  # a bit fragile, I know
    docstring3 = content[0][2][1][2][0][2][1][2][1][0]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        content[0].astext()
        == "package\n\n\n\nclass target.package.ClassBar\n\nBases: handle\n\nThe Bar and Foo handler, with doFoo() and doBar() methods.\n\nConstructor Summary\n\n\n\n\n\nClassBar()\n\nInitialize the bars and foos\n\nProperty Summary\n\n\n\n\n\nbars\n\nNumber of bars\n\n\n\nfoos\n\nNumber of foos, used by doBar() method\n\nMethod Summary\n\n\n\n\n\ndoBar()\n\nImplement doBar stage, not called by ClassBar()\n\n\n\ndoFoo()\n\ndoFoo - Doing foo, without passing in @ClassExample\n\n\n\n\n\n\n\ntarget.package.funcFoo(u, t)\n\nFunction that does Foo\n\nx = package.funcFoo(u)\n\n[x, y] = package.funcFoo(u, t)\n\nTest for auto-linking with baseFunction and BaseClass, etc."
    )
    assert (
        docstring1.rawsource
        == "The Bar and Foo handler, with doFoo() and doBar() methods."
    )
    assert docstring2.rawsource == "Number of foos, used by doBar() method"
    assert docstring3.rawsource == "Implement **doBar** stage, not called by ClassBar()"


@pytest.mark.parametrize("confdict", [{"matlab_show_property_default_value": True}])
def test_package_show_default_value(app, confdict):
    content = pickle.loads((app.doctreedir / "index_package.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "package\n\n\n\nclass target.package.ClassBar\n\nBases: handle\n\nThe Bar and Foo handler, with doFoo() and doBar() methods.\n\nConstructor Summary\n\n\n\n\n\nClassBar()\n\nInitialize the bars and foos\n\nProperty Summary\n\n\n\n\n\nbars = 'bars'\n\nNumber of bars\n\n\n\nfoos = 10\n\nNumber of foos, used by doBar() method\n\nMethod Summary\n\n\n\n\n\ndoBar()\n\nImplement doBar stage, not called by ClassBar()\n\n\n\ndoFoo()\n\ndoFoo - Doing foo, without passing in @ClassExample\n\n\n\n\n\n\n\ntarget.package.funcFoo(u, t)\n\nFunction that does Foo\n\nx = package.funcFoo(u)\n\n[x, y] = package.funcFoo(u, t)\n\nTest for auto-linking with baseFunction and BaseClass, etc."
    )


@pytest.mark.parametrize("confdict", [{"matlab_auto_link": "all"}])
def test_package_auto_link_all(app, confdict):
    content = pickle.loads((app.doctreedir / "index_package.doctree").read_bytes())
    docstring1 = content[0][2][1][1]  # a bit fragile, I know
    docstring2 = content[0][2][1][2][0][1][1][4][1][0]  # a bit fragile, I know
    docstring3 = content[0][2][1][2][0][2][1][4][1][0][0]  # a bit fragile, I know
    docstring4 = content[0][2][1][2][0][2][1][4][1][0][2]  # a bit fragile, I know
    docstring5 = content[0][2][1][2][0][2][1][2][1][0]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        content[0].astext()
        == "package\n\n\n\nclass target.package.ClassBar\n\nBases: handle\n\nThe Bar and Foo handler, with doFoo() and doBar() methods.\n\nConstructor Summary\n\n\n\n\n\nClassBar()\n\nInitialize the bars and foos\n\nProperty Summary\n\n\n\n\n\nbars\n\nNumber of bars\n\n\n\nfoos\n\nNumber of foos, used by doBar() method\n\nMethod Summary\n\n\n\n\n\ndoBar()\n\nImplement doBar stage, not called by ClassBar()\n\n\n\ndoFoo()\n\ndoFoo() - Doing foo, without passing in @ClassExample\n\n\n\n\n\n\n\ntarget.package.funcFoo(u, t)\n\nFunction that does Foo\n\nx = package.funcFoo(u)\n\n[x, y] = package.funcFoo(u, t)\n\nTest for auto-linking with baseFunction() and BaseClass, etc."
    )
    assert (
        docstring1.rawsource
        == "The Bar and Foo handler, with :meth:`doFoo() <target.package.ClassBar.doFoo>` and doBar() methods."
    )
    assert (
        docstring2.rawsource
        == "Number of :attr:`foos <target.package.ClassBar.foos>`, used by :meth:`doBar() <target.package.ClassBar.doBar>` method"
    )
    assert docstring3.rawsource == ":meth:`doFoo() <target.package.ClassBar.doFoo>`"
    assert docstring4.rawsource == "``@ClassExample``"
    assert (
        docstring5.rawsource
        == "Implement **doBar** stage, not called by :meth:`ClassBar() <target.package.ClassBar.ClassBar>`"
    )


def test_submodule(app):
    content = pickle.loads((app.doctreedir / "index_submodule.doctree").read_bytes())
    bases_line = content[0][2][1][0]
    assert len(content) == 1
    assert (
        content[0].astext()
        == "submodule\n\n\n\nclass target.submodule.ClassMeow\n\nBases: target.package.ClassBar\n\nClass which inherits from a package\n\nMethod Summary\n\n\n\n\n\nsay()\n\nSay Meow\n\n\n\ntarget.submodule.funcMeow(input)\n\nTests a function with comments after docstring"
    )
    assert bases_line.rawsource == "Bases: :class:`target.package.ClassBar`"


@pytest.mark.parametrize("confdict", [{"matlab_show_property_default_value": True}])
def test_submodule_show_default_value(app, confdict):
    content = pickle.loads((app.doctreedir / "index_submodule.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "submodule\n\n\n\nclass target.submodule.ClassMeow\n\nBases: target.package.ClassBar\n\nClass which inherits from a package\n\nMethod Summary\n\n\n\n\n\nsay()\n\nSay Meow\n\n\n\ntarget.submodule.funcMeow(input)\n\nTests a function with comments after docstring"
    )


def test_root(app):
    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "root\n\n\n\nclass BaseClass\n\nA class in the very root of the directory\n\nBaseClass Methods:\n\nBaseClass - the constructor, whose description extends\n\nto the next line\n\nDoBase - another BaseClass method\n\nSee Also\n\ntarget.ClassExample, baseFunction, ClassExample\n\nConstructor Summary\n\n\n\n\n\nBaseClass(obj, args)\n\nThe constructor\n\nMethod Summary\n\n\n\n\n\nDoBase()\n\nDo the Base thing\n\n\n\nbaseFunction(x)\n\nReturn the base of x\n\nSee Also:\n\ntarget.submodule.ClassMeow\ntarget.package.ClassBar\nClassMeow\npackage.ClassBar"
    )


@pytest.mark.parametrize("confdict", [{"matlab_src_dir": "."}])
def test_root_relative_matlab_src_dir(app, confdict):
    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "root\n\n\n\nclass BaseClass\n\nA class in the very root of the directory\n\nBaseClass Methods:\n\nBaseClass - the constructor, whose description extends\n\nto the next line\n\nDoBase - another BaseClass method\n\nSee Also\n\ntarget.ClassExample, baseFunction, ClassExample\n\nConstructor Summary\n\n\n\n\n\nBaseClass(obj, args)\n\nThe constructor\n\nMethod Summary\n\n\n\n\n\nDoBase()\n\nDo the Base thing\n\n\n\nbaseFunction(x)\n\nReturn the base of x\n\nSee Also:\n\ntarget.submodule.ClassMeow\ntarget.package.ClassBar\nClassMeow\npackage.ClassBar"
    )


@pytest.mark.parametrize("confdict", [{"matlab_show_property_default_value": True}])
def test_root_show_default_value(app, confdict):
    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "root\n\n\n\nclass BaseClass\n\nA class in the very root of the directory\n\nBaseClass Methods:\n\nBaseClass - the constructor, whose description extends\n\nto the next line\n\nDoBase - another BaseClass method\n\nSee Also\n\ntarget.ClassExample, baseFunction, ClassExample\n\nConstructor Summary\n\n\n\n\n\nBaseClass(obj, args)\n\nThe constructor\n\nMethod Summary\n\n\n\n\n\nDoBase()\n\nDo the Base thing\n\n\n\nbaseFunction(x)\n\nReturn the base of x\n\nSee Also:\n\ntarget.submodule.ClassMeow\ntarget.package.ClassBar\nClassMeow\npackage.ClassBar"
    )


@pytest.mark.parametrize("confdict", [{"matlab_auto_link": "basic"}])
def test_root_auto_link_basic(app, confdict):
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


@pytest.mark.parametrize("confdict", [{"matlab_class_signature": True}])
def test_root_class_signature(app, confdict):
    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "root\n\n\n\nclass BaseClass(obj, args)\n\nA class in the very root of the directory\n\nBaseClass Methods:\n\nBaseClass - the constructor, whose description extends\n\nto the next line\n\nDoBase - another BaseClass method\n\nSee Also\n\ntarget.ClassExample, baseFunction, ClassExample\n\nConstructor Summary\n\n\n\n\n\nBaseClass(obj, args)\n\nThe constructor\n\nMethod Summary\n\n\n\n\n\nDoBase()\n\nDo the Base thing\n\n\n\nbaseFunction(x)\n\nReturn the base of x\n\nSee Also:\n\ntarget.submodule.ClassMeow\ntarget.package.ClassBar\nClassMeow\npackage.ClassBar"
    )
