#! /usr/bin/env python
# -*- coding: utf-8 -*-
import helper
import pytest
from sphinx.testing.fixtures import make_app, test_params
from sphinxcontrib.mat_types import MatModule, MatObject, entities_table

from sphinxcontrib import mat_documenters as doc
from sphinxcontrib.matlab import mat_documenters as doc
from sphinxcontrib.matlab.mat_types import entities_table

rootdir = helper.rootdir(__file__)
matlab_src_dir = str(rootdir / "test_data")
MatObject.basedir = matlab_src_dir


@pytest.fixture
def app(make_app):
    # Create app to setup build environment
    srcdir = rootdir / "test_docs"
    app = make_app(srcdir=srcdir)
    MatObject.basedir = app.config.matlab_src_dir
    return app


@pytest.fixture
def mod(app):
    return MatObject.matlabify("test_data")


# def test_empty():
#     assert MatObject.matlabify("") is None


def test_unknown():
    assert MatObject.matlabify("not_test_data") is None


def test_script(mod, caplog):
    script = mod.getter("script")
    assert isinstance(script, doc.MatScript)


def test_module(mod):
    assert mod.getter("__name__") == "test_data"
    assert mod.getter("__path__")[0] == matlab_src_dir
    assert mod.getter("__file__") == matlab_src_dir
    assert mod.getter("__package__") == "test_data"
    assert not mod.getter("__module__")
    assert not mod.getter("__doc__")
    all_entities = mod.getter("__all__")
    all_items = {name for name, entity in all_entities}
    expected_items = {
        "+package",
        "@ClassFolder",
        "@ClassFolderWithoutClassDefinition",
        "@ClassFolderUsingBuiltins",
        "@EmptyClassFolder",
        "@NestedClassFolder",
        "Application",
        "ClassAbstract",
        "ClassExample",
        "ClassBySource",
        "ClassInheritHandle",
        "ClassWithEllipsisProperties",
        "ClassWithEndOfLineComment",
        "f_example",
        "f_with_nested_function",
        "submodule",
        "script",
        "Bool",
        "ClassWithEvent",
        "f_no_input_no_output_no_parentheses",
        "f_no_input_no_parentheses_no_docstring",
        "ClassWithCommentHeader",
        "f_with_comment_header",
        "f_with_dummy_argument",
        "f_with_string_ellipsis",
        "script_with_comment_header",
        "script_with_comment_header_2",
        "script_with_comment_header_3",
        "script_with_comment_header_4",
        "PropTypeOld",
        "ValidateProps",
        "ClassWithMethodAttributes",
        "ClassWithPropertyAttributes",
        "ClassWithoutIndent",
        "f_with_utf8",
        "f_with_latin_1",
        "f_with_name_mismatch",
        "ClassWithBuiltinOverload",
        "ClassWithBuiltinProperties",
        "ClassWithFunctionVariable",
        "ClassWithErrors",
        "f_inputargs_error",
        "ClassWithAttributes",
        "ClassWithLineContinuation",
        "ClassWithUnknownAttributes",
        "ClassWithNameMismatch",
        "ClassWithEnumMethod",
        "ClassWithEventMethod",
        "f_with_function_variable",
        "f_with_input_argument_block",
        "f_with_output_argument_block",
        "ClassWithUndocumentedMembers",
        "ClassWithGetterSetter",
        "ClassWithDoubleQuotedString",
        "ClassWithDummyArguments",
        "ClassWithStrings",
        "ClassWithFunctionArguments",
        "ClassWithMethodsWithSpaces",
        "ClassContainingParfor",
        "ClassWithStringEllipsis",
        "ClassLongProperty",
        "ClassWithGetMethod",
        "ClassWithLongPropertyDocstrings",
        "ClassWithLongPropertyTrailingEmptyDocstrings",
        "ClassWithPropertyValidators",
        "ClassWithTrailingCommentAfterBases",
        "ClassWithTrailingSemicolons",
        "ClassWithSeperatedComments",
        "ClassWithKeywordsAsFieldnames",
        "ClassWithPropertyCellValues",
        "ClassWithTests",
        "arguments",
    }
    assert all_items == expected_items
    assert mod.getter("__name__") in entities_table


def test_parse_twice(mod):
    mod2 = MatObject.matlabify("test_data")
    assert mod == mod2


def test_classes(mod):
    assert isinstance(mod, MatModule)

    # test superclass
    cls = mod.getter("ClassInheritHandle")
    assert isinstance(cls, doc.MatClass)
    assert cls.getter("__name__") == "ClassInheritHandle"
    assert cls.getter("__module__") == "test_data"
    assert cls.bases == ["handle", "my.super.Class"]
    assert cls.attrs == {}
    assert cls.properties == {
        "x": {
            "attrs": {},
            "default": None,
            "docstring": "a property",
            "size": None,
            "type": None,
            "validators": None,
        }
    }
    assert cls.getter("__doc__") == "a handle class\n\n:param x: a variable"


def test_abstract_class(mod):
    # test abstract class with attributes
    abc = mod.getter("ClassAbstract")
    assert isinstance(abc, doc.MatClass)
    assert abc.getter("__name__") == "ClassAbstract"
    assert abc.getter("__module__") == "test_data"
    assert "ClassInheritHandle" in abc.getter("__bases__")
    assert "ClassExample" in abc.getter("__bases__")
    assert abc.bases == ["ClassInheritHandle", "ClassExample"]
    assert abc.attrs == {"Abstract": True, "Sealed": True}
    assert abc.properties == {
        "y": {
            "default": None,
            "docstring": "y variable",
            "attrs": {"GetAccess": "private", "SetAccess": "private"},
            "size": None,
            "type": None,
            "validators": None,
        },
        "version": {
            "default": "'0.1.1-beta'",
            "docstring": "version",
            "attrs": {"Constant": True},
            "size": None,
            "type": None,
            "validators": None,
        },
    }
    assert (
        abc.getter("__doc__")
        == "an abstract class\n\n:param y: a variable\n:type y: double"
    )
    assert abc.getter("__doc__") == abc.docstring

    abc_y = abc.getter("y")
    assert isinstance(abc_y, doc.MatProperty)
    assert abc_y.default is None
    assert abc_y.docstring == "y variable"
    assert abc_y.attrs == {"SetAccess": "private", "GetAccess": "private"}

    abc_version = abc.getter("version")
    assert isinstance(abc_version, doc.MatProperty)
    assert abc_version.default == "'0.1.1-beta'"
    assert abc_version.docstring == "version"
    assert abc_version.attrs == {"Constant": True}


def test_class_method(mod):
    cls_meth = mod.getter("ClassExample")
    assert isinstance(cls_meth, doc.MatClass)
    assert cls_meth.getter("__name__") == "ClassExample"
    assert (
        cls_meth.docstring
        == "test class methods\n\n:param a: the input to :class:`ClassExample`"
    )
    constructor = cls_meth.getter("ClassExample")
    assert isinstance(constructor, doc.MatMethod)
    assert constructor.getter("__name__") == "ClassExample"
    mymethod = cls_meth.getter("mymethod")
    assert isinstance(mymethod, doc.MatMethod)
    assert mymethod.getter("__name__") == "mymethod"
    # TODO: mymethod.args will contain ['obj', 'b'] if run standalone
    #       but if test_autodoc.py is run, the 'obj' is removed
    assert mymethod.args
    assert "b" in list(mymethod.args.keys())
    assert list(mymethod.retv.keys()) == ["c"]
    assert (
        mymethod.docstring
        == "a method in :class:`ClassExample`\n\n:param b: an input to :meth:`mymethod`"
    )


def test_submodule_class(mod):
    cls = mod.getter("submodule.TestFibonacci")
    assert isinstance(cls, doc.MatClass)
    assert cls.docstring == "Test of MATLAB unittest method attributes"
    assert cls.attrs == {}
    assert cls.bases == ["matlab.unittest.TestCase"]
    assert "compareFirstThreeElementsToExpected" in cls.methods
    assert cls.module == "test_data.submodule"
    assert cls.properties == {}
    method = cls.getter("compareFirstThreeElementsToExpected")
    assert isinstance(method, doc.MatMethod)
    assert method.name == "compareFirstThreeElementsToExpected"
    assert method.retv == {}
    assert list(method.args.keys()) == ["tc"]
    assert method.docstring == "Test case that compares first three elements"
    assert method.attrs == {"Test": None}


def test_folder_class(mod):
    cls_mod = mod.getter("@ClassFolder")
    assert isinstance(cls_mod, MatModule)
    cls = cls_mod.getter("ClassFolder")
    assert cls.docstring == "A class in a folder"
    assert cls.attrs == {}
    assert cls.bases == []
    assert cls.module == "test_data.@ClassFolder"
    assert cls.properties == {
        "p": {
            "attrs": {},
            "default": None,
            "docstring": "a property of a class folder",
            "size": None,
            "type": None,
            "validators": None,
        }
    }

    assert "ClassFolder" in cls.methods

    func = cls_mod.getter("a_static_func")
    assert isinstance(func, doc.MatFunction)
    assert func.name == "a_static_func"
    assert list(func.args.keys()) == ["args"]
    assert list(func.retv.keys()) == ["retv"]
    assert func.docstring == "method in :class:`~test_data.@ClassFolder`"
    func = cls_mod.getter("classMethod")
    assert isinstance(func, doc.MatFunction)
    assert func.name == "classMethod"
    assert list(func.args.keys()) == ["obj", "varargin"]
    assert list(func.retv.keys()) == ["varargout"]
    assert (
        func.docstring
        == "CLASSMETHOD A function within a package\n\n:param obj: An instance of this class.\n"
        ":param varargin: Variable input arguments.\n:returns: varargout"
    )


def test_function(mod):
    assert isinstance(mod, MatModule)
    func = mod.getter("f_example")
    assert isinstance(func, doc.MatFunction)
    assert func.getter("__name__") == "f_example"
    assert list(func.retv.keys()) == ["o1", "o2", "o3"]
    assert list(func.args.keys()) == ["a1", "a2"]
    assert (
        func.docstring
        == "a fun function\n\n:param a1: the first input\n:param a2: another input\n:returns: ``[o1, o2, o3]`` some outputs"
    )


def test_function_getter(mod):
    assert isinstance(mod, MatModule)
    func = mod.getter("f_example")
    assert isinstance(func, doc.MatFunction)
    assert func.getter("__name__") == "f_example"
    assert (
        func.getter("__doc__")
        == "a fun function\n\n:param a1: the first input\n:param a2: another input\n:returns: ``[o1, o2, o3]`` some outputs"
    )
    assert func.getter("__module__") == "test_data"


def test_package_function(mod):
    assert isinstance(mod, MatModule)
    func = mod.getter("f_example")
    assert isinstance(func, doc.MatFunction)
    assert func.getter("__name__") == "f_example"
    assert list(func.retv.keys()) == ["o1", "o2", "o3"]
    assert list(func.args.keys()) == ["a1", "a2"]
    assert (
        func.docstring
        == "a fun function\n\n:param a1: the first input\n:param a2: another input\n:returns: ``[o1, o2, o3]`` some outputs"
    )


def test_class_with_get_method(mod):
    the_class = mod.getter("ClassWithGetMethod")
    assert isinstance(the_class, doc.MatClass)
    assert the_class.getter("__name__") == "ClassWithGetMethod"
    assert the_class.docstring == "Class with a method named get"
    the_method = the_class.getter("get")
    assert isinstance(the_method, doc.MatMethod)
    assert the_method.getter("__name__") == "get"
    assert list(the_method.retv.keys()) == ["varargout"]
    assert the_method.docstring.startswith(
        "Gets the numbers 1-n and fills in the outputs with them"
    )


if __name__ == "__main__":
    pytest.main([__file__])
