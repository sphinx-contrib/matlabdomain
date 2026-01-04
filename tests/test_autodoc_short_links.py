"""test_autodoc.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_autodoc"


@pytest.mark.parametrize("confdict", [{"matlab_short_links": True}])
def test_target(app, confdict):
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


@pytest.mark.parametrize(
    "confdict",
    [{"matlab_short_links": True, "matlab_show_property_default_value": True}],
)
def test_target_show_default_value(app, confdict):
    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())

    assert len(content) == 1

    assert (
        content[0].astext()
        == "target\n\n\n\nclass ClassExample\n\nBases: handle\n\nExample class\n\nClassExample Properties:\n\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample\n\nClassExample Methods:\n\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n\nSee also BaseClass, baseFunction, b, unknownEntity, mymethod,\npackage.ClassBar.bars, package.ClassBar.doFoo.\n\nConstructor Summary\n\n\n\n\n\nClassExample(a)\n\nLinks to fully qualified names package.ClassBar.foos,\npackage.ClassBar.doBar, and ClassExample.mymethod.\n\nProperty Summary\n\n\n\n\n\na = 42\n\na property\n\n\n\nb = 10\n\na property with default value\n\n\n\nc = [10; ... 30]\n\na property with multiline default value\n\nMethod Summary\n\n\n\n\n\nmymethod(b)\n\nA method in ClassExample\n\nParameters\n\nb – an input to mymethod()"
    )

    property_section = content[0][2][1][2][0]  # a bit fragile, I know
    assert (
        property_section.rawsource
        == "ClassExample Properties:\na - first property of ClassExample\nb - second property of ClassExample\nc - third property of ClassExample"
    )

    method_section = content[0][2][1][2][1]  # a bit fragile, I know
    assert (
        method_section.rawsource
        == "ClassExample Methods:\nClassExample - the constructor and a reference to mymethod()\nmymethod - a method in ClassExample\n"
    )


@pytest.mark.parametrize(
    "confdict",
    [
        {"matlab_short_links": True, "matlab_auto_link": "basic"},
        {"matlab_short_links": True, "matlab_auto_link": "all"},
    ],
)
def test_target_auto_link_basic(app, confdict):
    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())

    assert len(content) == 1

    see_also_line = content[0][2][1][3]  # a bit fragile, I know
    assert see_also_line.rawsource == (
        "See also :class:`BaseClass`, :func:`baseFunction`, "
        ":attr:`b <ClassExample.b>`, ``unknownEntity``, "
        ":meth:`mymethod() <ClassExample.mymethod>`,\n"
        ":attr:`package.ClassBar.bars`, :meth:`package.ClassBar.doFoo`."
    )

    property_section = content[0][2][1][2][0]  # a bit fragile, I know
    class_example_pattern = "ClassExample"
    if confdict.get("matlab_auto_link") == "all":
        class_example_pattern = ":class:`ClassExample`"
    expected_property_section = (
        "ClassExample Properties:\n"
        f"* :attr:`a <ClassExample.a>` - first property of {class_example_pattern}\n"
        f"* :attr:`b <ClassExample.b>` - second property of {class_example_pattern}\n"
        f"* :attr:`c <ClassExample.c>` - third property of {class_example_pattern}"
    )
    assert property_section.rawsource == expected_property_section

    method_section = content[0][2][1][2][1]  # a bit fragile, I know
    constructor_desc = content[0][2][1][4][0][0][1][2][1][0]  # a bit fragile, I know
    if confdict.get("matlab_auto_link") == "all":
        assert method_section.rawsource == (
            "ClassExample Methods:\n"
            "* :meth:`ClassExample() <ClassExample.ClassExample>` "
            "- the constructor and a reference to :meth:`mymethod() <ClassExample.mymethod>`\n"
            "* :meth:`mymethod() <ClassExample.mymethod>` "
            "- a method in :class:`ClassExample`\n"
        )
        assert constructor_desc.rawsource == (
            "Links to fully qualified names :attr:`package.ClassBar.foos`,\n"
            ":meth:`package.ClassBar.doBar`, and :meth:`ClassExample.mymethod`."
        )
    else:
        assert method_section.rawsource == (
            "ClassExample Methods:\n"
            "* :meth:`ClassExample() <ClassExample.ClassExample>` "
            "- the constructor and a reference to mymethod()\n"
            "* :meth:`mymethod() <ClassExample.mymethod>` "
            "- a method in ClassExample\n"
        )
        assert constructor_desc.rawsource == (
            "Links to fully qualified names package.ClassBar.foos,\n"
            "package.ClassBar.doBar, and ClassExample.mymethod."
        )


@pytest.mark.parametrize("confdict", [{"matlab_short_links": True}])
def test_classfolder(app, confdict):
    content = pickle.loads((app.doctreedir / "index_classfolder.doctree").read_bytes())

    assert len(content) == 1

    assert content[0].astext() == (
        "classfolder\n\n\n\n"
        "class ClassFolder\n\n"
        "A class in a folder\n\n"
        "Property Summary\n\n\n\n\n\n"
        "p\n\n"
        "a property of a class folder\n\n"
        "Method Summary\n\n\n\n\n\n"
        "a_static_func(args)\n\n"
        "A static method in @ClassFolder\n\n\n\n"
        "classMethod(varargin)\n\n"
        "CLASSMETHOD A function within a package\n\n"
        "Parameters\n\n"
        "obj – An instance of this class.\n\n"
        "varargin – Variable input arguments.\n\n"
        "Returns\n\n"
        "varargout\n\n\n\n"
        "method_inside_classdef(a, b)\n\n"
        "Method inside class definition"
    )


@pytest.mark.parametrize(
    "confdict",
    [
        {"matlab_short_links": True},
        {"matlab_short_links": True, "matlab_show_property_default_value": True},
        {"matlab_short_links": True, "matlab_auto_link": "all"},
    ],
)
def test_package(app, confdict):
    content = pickle.loads((app.doctreedir / "index_package.doctree").read_bytes())

    assert len(content) == 1

    to_add = ""
    if confdict.get("matlab_auto_link", "basic") == "all":
        to_add = "()"

    expected_content = (
        "package\n\n\n\n"
        "class package.ClassBar\n\n"
        "Bases: handle\n\n"
        "The Bar and Foo handler, with doFoo() and doBar() methods.\n\n"
        "Constructor Summary\n\n\n\n\n\n"
        "ClassBar()\n\n"
        "Initialize the bars and foos\n\n"
        "Property Summary\n\n\n\n\n\n"
        "bars{}\n\n"
        "Number of bars\n\n\n\n"
        "foos{}\n\n"
        "Number of foos, used by doBar() method\n\n"
        "Method Summary\n\n\n\n\n\n"
        "doBar()\n\n"
        "Implement doBar stage, not called by ClassBar()\n\n\n\n"
        "doFoo()\n\n"
        f"doFoo{to_add} - Doing foo, without passing in @ClassExample\n\n\n\n\n\n\n\n"
        "package.funcFoo(u, t)\n\n"
        "Function that does Foo\n\n"
        "x = package.funcFoo(u)\n\n"
        "[x, y] = package.funcFoo(u, t)\n\n"
        f"Test for auto-linking with baseFunction{to_add} and BaseClass, etc."
    )

    if not confdict.get("matlab_show_property_default_value", False):
        assert content[0].astext() == expected_content.format("", "")
    else:
        assert content[0].astext() == expected_content.format(" = 'bars'", " = 10")

    docstring1 = content[0][2][1][1]  # a bit fragile, I know
    docstring2 = content[0][2][1][2][0][1][1][4][1][0]  # a bit fragile, I know
    if confdict.get("matlab_auto_link", "basic") == "all":
        assert docstring1.rawsource == (
            "The Bar and Foo handler, "
            "with :meth:`doFoo() <package.ClassBar.doFoo>` and doBar() methods."
        )
        assert docstring2.rawsource == (
            "Number of :attr:`foos <package.ClassBar.foos>`, "
            "used by :meth:`doBar() <package.ClassBar.doBar>` method"
        )

        docstring3 = content[0][2][1][2][0][2][1][4][1][0][0]  # a bit fragile, I know
        assert docstring3.rawsource == ":meth:`doFoo() <package.ClassBar.doFoo>`"

        docstring4 = content[0][2][1][2][0][2][1][4][1][0][2]  # a bit fragile, I know
        assert docstring4.rawsource == "``@ClassExample``"

        docstring5 = content[0][2][1][2][0][2][1][2][1][0]  # a bit fragile, I know
        assert docstring5.rawsource == (
            "Implement **doBar** stage, "
            "not called by :meth:`ClassBar() <package.ClassBar.ClassBar>`"
        )

    else:
        assert (
            docstring1.rawsource
            == "The Bar and Foo handler, with doFoo() and doBar() methods."
        )
        assert docstring2.rawsource == "Number of foos, used by doBar() method"

        docstring3 = content[0][2][1][2][0][2][1][2][1][0]  # a bit fragile, I know
        assert (
            docstring3.rawsource
            == "Implement **doBar** stage, not called by ClassBar()"
        )


@pytest.mark.parametrize(
    "confdict",
    [
        {"matlab_short_links": True},
        {"matlab_short_links": True, "matlab_show_property_default_value": True},
    ],
)
def test_submodule(app, confdict):
    content = pickle.loads((app.doctreedir / "index_submodule.doctree").read_bytes())

    assert len(content) == 1

    assert content[0].astext() == (
        "submodule\n\n\n\n"
        "class ClassMeow\n\n"
        "Bases: package.ClassBar\n\n"
        "Class which inherits from a package\n\n"
        "Method Summary\n\n\n\n\n\n"
        "say()\n\n"
        "Say Meow\n\n\n\n"
        "funcMeow(input)\n\n"
        "Tests a function with comments after docstring"
    )

    bases_line = content[0][2][1][0]
    assert bases_line.rawsource == "Bases: :class:`package.ClassBar`"


@pytest.mark.parametrize(
    "confdict",
    [
        {"matlab_short_links": True},
        {"matlab_short_links": True, "matlab_show_property_default_value": True},
    ],
)
def test_root(app, confdict):
    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())

    assert len(content) == 1

    assert content[0].astext() == (
        "root\n\n\n\n"
        "class BaseClass\n\n"
        "A class in the very root of the directory\n\n"
        "BaseClass Methods:\n\n"
        "BaseClass - the constructor, whose description extends\n\n"
        "to the next line\n\n"
        "DoBase - another BaseClass method\n\n"
        "See Also\n\n"
        "target.ClassExample, baseFunction, ClassExample\n\n"
        "Constructor Summary\n\n\n\n\n\n"
        "BaseClass(obj, args)\n\n"
        "The constructor\n\n"
        "Method Summary\n\n\n\n\n\n"
        "DoBase()\n\n"
        "Do the Base thing\n\n\n\n"
        "baseFunction(x)\n\n"
        "Return the base of x\n\n"
        "See Also:\n\n"
        "target.submodule.ClassMeow\n"
        "target.package.ClassBar\n"
        "ClassMeow\n"
        "package.ClassBar"
    )


@pytest.mark.parametrize(
    "confdict", [{"matlab_short_links": True, "matlab_auto_link": "basic"}]
)
def test_root_auto_link_basic(app, confdict):
    content = pickle.loads((app.doctreedir / "index_root.doctree").read_bytes())

    assert len(content) == 1

    method_section = content[0][2][1][1][0]  # a bit fragile, I know
    assert method_section.rawsource == (
        "BaseClass Methods:\n"
        "* :meth:`BaseClass() <BaseClass.BaseClass>` - the constructor, whose description extends\n"
        "    to the next line\n"
        "* :meth:`DoBase() <BaseClass.DoBase>` - another BaseClass method\n"
    )

    see_also_line_1 = content[0][2][1][1][1]  # a bit fragile, I know
    assert (
        see_also_line_1.rawsource
        == "See Also\n:class:`target.ClassExample`, :func:`baseFunction`, :class:`ClassExample`\n\n"
    )

    see_also_line_2 = content[0][4][1][1][0]  # a bit fragile, I know
    assert see_also_line_2.rawsource == (
        "See Also:\n"
        ":class:`target.submodule.ClassMeow`\n"
        ":class:`target.package.ClassBar`\n"
        ":class:`ClassMeow`\n"
        ":class:`package.ClassBar`"
    )
