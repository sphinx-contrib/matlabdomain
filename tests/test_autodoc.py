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
        == "target\n\n\n\nclass ClassExample\n\nBases: handle\n\nExample class\n\nClassExample Properties:\n\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample\n\nClassExample Methods:\n\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n\nSee also BaseClass, baseFunction, b, unknownEntity, mymethod,\npackage.ClassBar.bars, package.ClassBar.doFoo.\n\nConstructor Summary\n\n\n\n\n\nClassExample(a)\n\nLinks to fully qualified names package.ClassBar.foos,\npackage.ClassBar.doBar, and ClassExample.mymethod.\n\nProperty Summary\n\n\n\n\n\na\n\na property\n\n\n\nb\n\na property with default value\n\n\n\nc\n\na property with multiline default value\n\nMethod Summary\n\n\n\n\n\nmymethod(b)\n\nA method in ClassExample\n\nParameters\n\nb – an input to mymethod()"
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
        == "target\n\n\n\nclass ClassExample\n\nBases: handle\n\nExample class\n\nClassExample Properties:\n\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample\n\nClassExample Methods:\n\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n\nSee also BaseClass, baseFunction, b, unknownEntity, mymethod,\npackage.ClassBar.bars, package.ClassBar.doFoo.\n\nConstructor Summary\n\n\n\n\n\nClassExample(a)\n\nLinks to fully qualified names package.ClassBar.foos,\npackage.ClassBar.doBar, and ClassExample.mymethod.\n\nProperty Summary\n\n\n\n\n\na = 42\n\na property\n\n\n\nb = 10\n\na property with default value\n\n\n\nc = [10; ... 30]\n\na property with multiline default value\n\nMethod Summary\n\n\n\n\n\nmymethod(b)\n\nA method in ClassExample\n\nParameters\n\nb – an input to mymethod()"
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
        == "ClassExample Properties:\n* :mat:attr:`a <target/ClassExample.m.a>` - first property of ClassExample\n* :mat:attr:`b <target/ClassExample.m.b>` - second property of ClassExample\n* :mat:attr:`c <target/ClassExample.m.c>` - third property of ClassExample"
    )
    assert (
        method_section.rawsource
        == "ClassExample Methods:\n* :mat:meth:`ClassExample() <target/ClassExample.m.ClassExample>` - the constructor and a reference to mymethod()\n* :mat:meth:`mymethod() <target/ClassExample.m.mymethod>` - a method in ClassExample\n"
    )
    assert (
        see_also_line.rawsource
        == "See also :mat:class:`BaseClass <BaseClass.m>`, :mat:func:`baseFunction() <baseFunction.m>`, :mat:attr:`b <target/ClassExample.m.b>`, ``unknownEntity``, :mat:meth:`mymethod() <target/ClassExample.m.mymethod>`,\n:mat:attr:`package.ClassBar.bars <target/+package/ClassBar.m.bars>`, :mat:meth:`package.ClassBar.doFoo() <target/+package/ClassBar.m.doFoo>`."
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
        == "ClassExample Properties:\n* :mat:attr:`a <target/ClassExample.m.a>` - first property of :mat:class:`ClassExample <target/ClassExample.m>`\n* :mat:attr:`b <target/ClassExample.m.b>` - second property of :mat:class:`ClassExample <target/ClassExample.m>`\n* :mat:attr:`c <target/ClassExample.m.c>` - third property of :mat:class:`ClassExample <target/ClassExample.m>`"
    )
    assert (
        method_section.rawsource
        == "ClassExample Methods:\n* :mat:meth:`ClassExample() <target/ClassExample.m.ClassExample>` - the constructor and a reference to :mat:meth:`mymethod() <target/ClassExample.m.mymethod>`\n* :mat:meth:`mymethod() <target/ClassExample.m.mymethod>` - a method in :mat:class:`ClassExample <target/ClassExample.m>`\n"
    )
    assert (
        see_also_line.rawsource
        == "See also :mat:class:`BaseClass <BaseClass.m>`, :mat:func:`baseFunction() <baseFunction.m>`, :mat:attr:`b <target/ClassExample.m.b>`, ``unknownEntity``, :mat:meth:`mymethod() <target/ClassExample.m.mymethod>`,\n:mat:attr:`package.ClassBar.bars <target/+package/ClassBar.m.bars>`, :mat:meth:`package.ClassBar.doFoo() <target/+package/ClassBar.m.doFoo>`."
    )
    assert (
        constructor_desc.rawsource
        == "Links to fully qualified names :mat:attr:`package.ClassBar.foos <target/+package/ClassBar.m.foos>`,\n:mat:meth:`package.ClassBar.doBar() <target/+package/ClassBar.m.doBar>`, and :mat:meth:`ClassExample.mymethod() <target/ClassExample.m.mymethod>`."
    )


def test_classfolder(app):
    content = pickle.loads((app.doctreedir / "index_classfolder.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "classfolder\n\n\n\nclass ClassFolder\n\nA class in a folder\n\nProperty Summary\n\n\n\n\n\np\n\na property of a class folder\n\nMethod Summary\n\n\n\n\n\nstatic a_static_func(obj, args)\n\nA static method in @ClassFolder\n\n\n\nclassMethod(varargin)\n\nCLASSMETHOD A function within a package\n\nParameters\n\nobj – An instance of this class.\n\nvarargin – Variable input arguments.\n\nReturns\n\nvarargout\n\n\n\nmethod_inside_classdef(a, b)\n\nMethod inside class definition"
    )


def test_package(app):
    content = pickle.loads((app.doctreedir / "index_package.doctree").read_bytes())
    docstring1 = content[0][2][1][1]  # a bit fragile, I know
    docstring2 = content[0][2][1][2][0][1][1][4][1][0]  # a bit fragile, I know
    docstring3 = content[0][2][1][2][0][2][1][2][1][0]  # a bit fragile, I know
    assert len(content) == 1
    assert (
        content[0].astext()
        == "package\n\n\n\nclass package.ClassBar\n\nBases: handle\n\nThe Bar and Foo handler, with doFoo() and doBar() methods.\n\nConstructor Summary\n\n\n\n\n\nClassBar()\n\nInitialize the bars and foos\n\nProperty Summary\n\n\n\n\n\nbars\n\nNumber of bars\n\n\n\nfoos\n\nNumber of foos, used by doBar() method\n\nMethod Summary\n\n\n\n\n\ndoBar()\n\nImplement doBar stage, not called by ClassBar()\n\n\n\ndoFoo()\n\ndoFoo - Doing foo, without passing in @ClassExample\n\n\n\nnamespace package\n\n\n\n\n\npackage.funcFoo(u, t)\n\nFunction that does Foo\n\nx = package.funcFoo(u)\n\n[x, y] = package.funcFoo(u, t)\n\nTest for auto-linking with baseFunction and BaseClass, etc."
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
        == "package\n\n\n\nclass package.ClassBar\n\nBases: handle\n\nThe Bar and Foo handler, with doFoo() and doBar() methods.\n\nConstructor Summary\n\n\n\n\n\nClassBar()\n\nInitialize the bars and foos\n\nProperty Summary\n\n\n\n\n\nbars = 'bars'\n\nNumber of bars\n\n\n\nfoos = 10\n\nNumber of foos, used by doBar() method\n\nMethod Summary\n\n\n\n\n\ndoBar()\n\nImplement doBar stage, not called by ClassBar()\n\n\n\ndoFoo()\n\ndoFoo - Doing foo, without passing in @ClassExample\n\n\n\nnamespace package\n\n\n\n\n\npackage.funcFoo(u, t)\n\nFunction that does Foo\n\nx = package.funcFoo(u)\n\n[x, y] = package.funcFoo(u, t)\n\nTest for auto-linking with baseFunction and BaseClass, etc."
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
        == "package\n\n\n\nclass package.ClassBar\n\nBases: handle\n\nThe Bar and Foo handler, with doFoo() and doBar() methods.\n\nConstructor Summary\n\n\n\n\n\nClassBar()\n\nInitialize the bars and foos\n\nProperty Summary\n\n\n\n\n\nbars\n\nNumber of bars\n\n\n\nfoos\n\nNumber of foos, used by doBar() method\n\nMethod Summary\n\n\n\n\n\ndoBar()\n\nImplement doBar stage, not called by ClassBar()\n\n\n\ndoFoo()\n\ndoFoo() - Doing foo, without passing in @ClassExample\n\n\n\nnamespace package\n\n\n\n\n\npackage.funcFoo(u, t)\n\nFunction that does Foo\n\nx = package.funcFoo(u)\n\n[x, y] = package.funcFoo(u, t)\n\nTest for auto-linking with baseFunction() and BaseClass, etc."
    )
    assert (
        docstring1.rawsource
        == "The Bar and Foo handler, with :mat:meth:`doFoo() <target/+package/ClassBar.m.doFoo>` and doBar() methods."
    )
    assert (
        docstring2.rawsource
        == "Number of :mat:attr:`foos <target/+package/ClassBar.m.foos>`, used by :mat:meth:`doBar() <target/+package/ClassBar.m.doBar>` method"
    )
    assert (
        docstring3.rawsource == ":mat:meth:`doFoo() <target/+package/ClassBar.m.doFoo>`"
    )
    assert docstring4.rawsource == "``@ClassExample``"
    assert (
        docstring5.rawsource
        == "Implement **doBar** stage, not called by :mat:meth:`ClassBar() <target/+package/ClassBar.m.ClassBar>`"
    )


def test_submodule(app):
    content = pickle.loads((app.doctreedir / "index_submodule.doctree").read_bytes())
    bases_line = content[0][2][1][0]
    assert len(content) == 1
    assert (
        content[0].astext()
        == "submodule\n\n\n\nclass ClassMeow\n\nBases: package.ClassBar\n\nClass which inherits from a package\n\nMethod Summary\n\n\n\n\n\nsay()\n\nSay Meow\n\n\n\nfuncMeow(input)\n\nTests a function with comments after docstring"
    )
    assert (
        bases_line.rawsource
        == "Bases: :mat:class:`package.ClassBar <target/+package/ClassBar.m>`"
    )


@pytest.mark.parametrize("confdict", [{"matlab_show_property_default_value": True}])
def test_submodule_show_default_value(app, confdict):
    content = pickle.loads((app.doctreedir / "index_submodule.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "submodule\n\n\n\nclass ClassMeow\n\nBases: package.ClassBar\n\nClass which inherits from a package\n\nMethod Summary\n\n\n\n\n\nsay()\n\nSay Meow\n\n\n\nfuncMeow(input)\n\nTests a function with comments after docstring"
    )


def test_root(app):
    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "root\n\n\n\nclass BaseClass\n\nA class in the very root of the directory\n\nBaseClass Methods:\n\nBaseClass - the constructor, whose description extends\n\nto the next line\n\nDoBase - another BaseClass method\n\nSee Also\n\ntarget/ClassExample.m, baseFunction, ClassExample\n\nConstructor Summary\n\n\n\n\n\nBaseClass(obj, args)\n\nThe constructor\n\nMethod Summary\n\n\n\n\n\nDoBase()\n\nDo the Base thing\n\n\n\nbaseFunction(x)\n\nReturn the base of x\n\nSee Also:\n\ntarget/submodule/ClassMeow.m\ntarget/+package/ClassBar.m\nClassMeow\npackage.ClassBar"
    )


@pytest.mark.parametrize("confdict", [{"matlab_show_property_default_value": True}])
def test_root_show_default_value(app, confdict):
    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "root\n\n\n\nclass BaseClass\n\nA class in the very root of the directory\n\nBaseClass Methods:\n\nBaseClass - the constructor, whose description extends\n\nto the next line\n\nDoBase - another BaseClass method\n\nSee Also\n\ntarget/ClassExample.m, baseFunction, ClassExample\n\nConstructor Summary\n\n\n\n\n\nBaseClass(obj, args)\n\nThe constructor\n\nMethod Summary\n\n\n\n\n\nDoBase()\n\nDo the Base thing\n\n\n\nbaseFunction(x)\n\nReturn the base of x\n\nSee Also:\n\ntarget/submodule/ClassMeow.m\ntarget/+package/ClassBar.m\nClassMeow\npackage.ClassBar"
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
        == "BaseClass Methods:\n* :mat:meth:`BaseClass() <BaseClass.m.BaseClass>` - the constructor, whose description extends\n    to the next line\n* :mat:meth:`DoBase() <BaseClass.m.DoBase>` - another BaseClass method\n"
    )
    assert (
        see_also_line_1.rawsource
        == "See Also\n:mat:class:`target/ClassExample.m <target/ClassExample.m>`, :mat:func:`baseFunction() <baseFunction.m>`, :mat:class:`ClassExample <target/ClassExample.m>`\n\n"
    )
    assert (
        see_also_line_2.rawsource
        == "See Also:\n:mat:class:`target/submodule/ClassMeow.m <target/submodule/ClassMeow.m>`\n:mat:class:`target/+package/ClassBar.m <target/+package/ClassBar.m>`\n:mat:class:`ClassMeow <target/submodule/ClassMeow.m>`\n:mat:class:`package.ClassBar <target/+package/ClassBar.m>`"
    )


@pytest.mark.parametrize("confdict", [{"matlab_class_signature": True}])
def test_root_class_signature(app, confdict):
    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())
    assert len(content) == 1
    assert (
        content[0].astext()
        == "root\n\n\n\nclass BaseClass(obj, args)\n\nA class in the very root of the directory\n\nBaseClass Methods:\n\nBaseClass - the constructor, whose description extends\n\nto the next line\n\nDoBase - another BaseClass method\n\nSee Also\n\ntarget/ClassExample.m, baseFunction, ClassExample\n\nConstructor Summary\n\n\n\n\n\nBaseClass(obj, args)\n\nThe constructor\n\nMethod Summary\n\n\n\n\n\nDoBase()\n\nDo the Base thing\n\n\n\nbaseFunction(x)\n\nReturn the base of x\n\nSee Also:\n\ntarget/submodule/ClassMeow.m\ntarget/+package/ClassBar.m\nClassMeow\npackage.ClassBar"
    )
