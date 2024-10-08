#! /usr/bin/env python
# -*- coding: utf-8 -*-
from sphinxcontrib import mat_types
import os
import pytest


DIRNAME = os.path.abspath(os.path.dirname(__file__))
TESTDATA_ROOT = os.path.join(DIRNAME, "test_data")
TESTDATA_SUB = os.path.join(TESTDATA_ROOT, "submodule")


# @pytest.fixture(autouse=True)
# def setup():
#     try:
#         sys.modules.pop('test_data')
#     except KeyError:
#         pass


def test_ClassExample():
    mfile = os.path.join(TESTDATA_ROOT, "ClassExample.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassExample", "test_data")
    assert obj.name == "ClassExample"
    assert (
        obj.docstring
        == "test class methods\n\n:param a: the input to :class:`ClassExample`"
    )
    mymethod = obj.methods["mymethod"]
    assert mymethod.name == "mymethod"
    assert list(mymethod.retv.keys()) == ["c"]
    assert list(mymethod.args.keys()) == ["obj", "b"]
    assert (
        mymethod.docstring
        == "a method in :class:`ClassExample`\n\n:param b: an input to :meth:`mymethod`"
    )


def test_comment_after_docstring():
    mfile = os.path.join(TESTDATA_SUB, "f_comment_after_docstring.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_comment_after_docstring", "")
    assert obj.name == "f_comment_after_docstring"
    assert list(obj.retv.keys()) == ["output"]
    assert list(obj.args.keys()) == ["input"]
    assert obj.docstring == "Tests a function with comments after docstring"


def test_docstring_no_newline():
    mfile = os.path.join(TESTDATA_SUB, "f_docstring_no_newline.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_docstring_no_newline", "")
    assert obj.name == "f_docstring_no_newline"
    assert list(obj.retv.keys()) == ["y"]
    assert list(obj.args.keys()) == []
    assert obj.docstring == "Test a function without a newline after docstring"


def test_ellipsis_after_equals():
    mfile = os.path.join(TESTDATA_SUB, "f_ellipsis_after_equals.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_ellipsis_after_equals", "")
    assert obj.name == "f_ellipsis_after_equals"
    assert list(obj.retv.keys()) == ["output"]
    assert list(obj.args.keys()) == ["arg"]
    assert obj.docstring == "Tests a function with ellipsis after equals"


def test_ellipsis_empty_output():
    mfile = os.path.join(TESTDATA_SUB, "f_ellipsis_empty_output.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_ellipsis_empty_output", "")
    assert obj.name == "f_ellipsis_empty_output"
    assert list(obj.retv.keys()) == []
    assert list(obj.args.keys()) == ["arg"]
    assert obj.docstring == "Tests a function with ellipsis in the output"


def test_ellipsis_in_comment():
    mfile = os.path.join(TESTDATA_SUB, "f_ellipsis_in_comment.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_ellipsis_in_comment", "")
    assert obj.name == "f_ellipsis_in_comment"
    assert list(obj.retv.keys()) == ["y"]
    assert list(obj.args.keys()) == ["x"]
    assert obj.docstring == "Tests a function with ellipsis in the comment ..."


def test_ellipsis_in_output():
    mfile = os.path.join(TESTDATA_SUB, "f_ellipsis_in_output.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_ellipsis_in_output", "")
    assert obj.name == "f_ellipsis_in_output"
    assert list(obj.retv.keys()) == ["output", "with", "ellipsis"]
    assert list(obj.args.keys()) == ["arg"]
    assert obj.docstring == "Tests a function with ellipsis in the output"


def test_ellipsis_in_output_multiple():
    mfile = os.path.join(TESTDATA_SUB, "f_ellipsis_in_output_multiple.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_ellipsis_in_output_multiple", "")
    assert obj.name == "f_ellipsis_in_output_multiple"
    assert list(obj.retv.keys()) == ["output", "with", "ellipsis"]
    assert list(obj.args.keys()) == ["arg"]
    assert obj.docstring == "Tests a function with multiple ellipsis in the output"


def test_no_docstring():
    mfile = os.path.join(TESTDATA_SUB, "f_no_docstring.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_no_docstring", "")
    assert obj.name == "f_no_docstring"
    assert list(obj.retv.keys()) == ["y"]
    assert list(obj.args.keys()) == []
    assert obj.docstring is None


def test_no_output():
    mfile = os.path.join(TESTDATA_SUB, "f_no_output.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_no_output", "")
    assert obj.name == "f_no_output"
    assert list(obj.retv.keys()) == []
    assert list(obj.args.keys()) == ["arg"]
    assert obj.docstring == "A function with no outputs"


def test_no_input_parentheses():
    mfile = os.path.join(TESTDATA_SUB, "f_no_input_parentheses.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_no_input_parentheses", "")
    assert obj.name == "f_no_input_parentheses"
    assert list(obj.retv.keys()) == ["y"]
    assert list(obj.args.keys()) == []
    assert obj.docstring == "Tests a function without parentheses in input"


def test_no_spaces():
    mfile = os.path.join(TESTDATA_SUB, "f_no_spaces.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_no_spaces", "")
    assert obj.name == "f_no_spaces"
    assert list(obj.retv.keys()) == ["a", "b", "c"]
    assert list(obj.args.keys()) == ["x", "y", "z"]
    assert obj.docstring == "Tests a function with no spaces in function signature"


def test_with_tabs():
    mfile = os.path.join(TESTDATA_SUB, "f_with_tabs.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_with_tabs", "")
    assert obj.name == "f_with_tabs"
    assert list(obj.retv.keys()) == ["y"]
    assert list(obj.args.keys()) == ["x"]
    assert obj.docstring == "A function with tabs"


def test_ClassWithEndOfLineComment():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithEndOfLineComment.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithEndOfLineComment", "test_data"
    )
    assert obj.name == "ClassWithEndOfLineComment"
    assert obj.docstring == ""
    method_test1 = obj.methods["test1"]
    assert method_test1.name == "test1"
    # TODO: Trailing comment get passed as docstring
    # assert method_test.docstring == ''
    method_test2 = obj.methods["test2"]
    assert method_test2.name == "test2"
    # TODO: Trailing comment get passed as docstring
    # assert method_test1.docstring == ''


def test_ClassWithEvent():
    # TODO: handle 'events' block
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithEvent.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithEvent", "test_data")
    assert obj.name == "ClassWithEvent"
    assert obj.docstring == ""


def test_ClassWithFunctionArguments():
    # TODO: handle 'events' block
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithFunctionArguments.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithFunctionArguments", "test_data"
    )
    assert obj.name == "ClassWithFunctionArguments"
    assert (
        obj.docstring
        == "test class methods with function arguments\n\n:param a: the input to :class:`ClassWithFunctionArguments`"
    )
    mymethod = obj.methods["mymethod"]
    assert mymethod.name == "mymethod"
    assert list(mymethod.retv.keys()) == ["c"]
    assert list(mymethod.args.keys()) == ["obj", "b"]
    assert (
        mymethod.docstring
        == "a method in :class:`ClassWithFunctionArguments`\n\n:param b: an input to :meth:`mymethod`"
    )


def test_EnumerationBool():
    # TODO: handle 'enumeration' block
    mfile = os.path.join(DIRNAME, "test_data", "Bool.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "Bool", "test_data")
    assert obj.name == "Bool"
    assert obj.docstring == ""


def test_no_input_no_output_no_parentheses():
    mfile = os.path.join(DIRNAME, "test_data", "f_no_input_no_output_no_parentheses.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "f_no_input_no_output_no_parentheses", "test_data"
    )
    assert obj.name == "f_no_input_no_output_no_parentheses"
    assert (
        obj.docstring
        == "Tests a function without parentheses in input and no return value"
    )


def test_no_input_no_parentheses_no_docstring():
    mfile = os.path.join(
        DIRNAME, "test_data", "f_no_input_no_parentheses_no_docstring.m"
    )
    obj = mat_types.MatObject.parse_mfile(
        mfile, "f_no_input_no_parentheses_no_docstring", "test_data"
    )
    assert obj.name == "f_no_input_no_parentheses_no_docstring"
    assert list(obj.retv.keys()) == ["result"]
    assert list(obj.args.keys()) == []


def test_ClassWithCommentHeader():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithCommentHeader.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithCommentHeader", "test_data")
    assert obj.name == "ClassWithCommentHeader"
    assert obj.docstring == "A class with a comment header on the top."
    method_get_tform = obj.methods["getTransformation"]
    assert method_get_tform.name == "getTransformation"
    assert list(method_get_tform.retv.keys()) == ["tform"]
    assert list(method_get_tform.args.keys()) == ["obj"]


def test_with_comment_header():
    mfile = os.path.join(DIRNAME, "test_data", "f_with_comment_header.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_with_comment_header", "test_data")
    assert obj.name == "f_with_comment_header"
    assert obj.docstring == "A simple function with a comment header on the top."


def test_script_with_comment_header():
    mfile = os.path.join(DIRNAME, "test_data", "script_with_comment_header.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "script_with_comment_header", "test_data"
    )
    assert (
        obj.docstring
        == """This is a Comment Header
Copyright (C) <year>, by <full_name>

Some descriptions ...

This header and all further comments above the first command line
of the script will be ignored by the documentation system.

Lisence (GPL, BSD, etc.)
"""
    )


def test_script_with_comment_header_2():
    mfile = os.path.join(DIRNAME, "test_data", "script_with_comment_header_2.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "script_with_comment_header_2", "test_data"
    )
    assert (
        obj.docstring
        == """This is a Comment Header
Copyright (C) <year>, by <full_name>

Some descriptions ...

This header and all further comments above the first command line
of the script will be ignored by the documentation system.

Lisence (GPL, BSD, etc.)
"""
    )


def test_script_with_comment_header_3():
    mfile = os.path.join(DIRNAME, "test_data", "script_with_comment_header_3.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "script_with_comment_header_3", "test_data"
    )
    assert (
        obj.docstring
        == """This is a Comment Header with empty lines above
and many line comments.
"""
    )


def test_script_with_comment_header_4():
    mfile = os.path.join(DIRNAME, "test_data", "script_with_comment_header_4.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "script_with_comment_header_4", "test_data"
    )
    assert (
        obj.docstring
        == """This is a Comment Header with a single instruction above
and many line comments.
"""
    )


def test_PropTypeOld():
    mfile = os.path.join(DIRNAME, "test_data", "PropTypeOld.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "PropTypeOld", "test_data")
    assert obj.name == "PropTypeOld"
    assert obj.docstring == ""
    assert obj.properties == {
        "link_name": {
            "docstring": None,
            "attrs": {},
            "default": "'none'",
            "size": None,
            "type": "char",
            "validators": None,
        },  # 'type': ['char']
        "pos": {
            "docstring": None,
            "attrs": {},
            "default": "zeros(3,1)",
            "size": (":", "1"),
            "type": "double",
            "validators": None,
        },  # 'type': ['double', 'vector'],
        "rotm": {
            "docstring": None,
            "attrs": {},
            "default": "zeros(3,3)",
            "size": (":", ":"),
            "type": "double",
            "validators": None,
        },  # 'type': ['double', 'matrix'],
        "idx": {
            "docstring": None,
            "attrs": {},
            "default": "0",
            "size": ("1", "1"),
            "type": "uint8",
            "validators": None,
        },  # 'type': ['uint8', 'scalar'],
    }


def test_ValidateProps():
    mfile = os.path.join(DIRNAME, "test_data", "ValidateProps.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ValidateProps", "test_data")
    assert obj.name == "ValidateProps"
    assert obj.docstring == ""


def test_ClassWithMethodAttributes():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithMethodAttributes.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithMethodAttributes", "test_data"
    )
    assert obj.name == "ClassWithMethodAttributes"
    assert obj.docstring == "Class with different method attributes"
    assert obj.methods["testNormal"].attrs == {}
    assert obj.methods["testPublic"].attrs == {"Access": "public"}
    assert obj.methods["testProtected"].attrs == {"Access": "protected"}
    assert obj.methods["testPrivate1"].attrs == {"Access": "private"}
    assert obj.methods["testPrivate2"].attrs == {"Access": "'private'"}
    assert obj.methods["testHidden"].attrs == {"Hidden": True}
    assert obj.methods["testStatic"].attrs == {"Static": True}
    assert obj.methods["testFriend1"].attrs == {"Access": "?OtherClass"}
    assert obj.methods["testFriend2"].attrs == {
        "Access": ["?OtherClass", "?pack.OtherClass2"]
    }


def test_ClassWithPropertyAttributes():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithPropertyAttributes.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithPropertyAttributes", "test_data"
    )
    assert obj.name == "ClassWithPropertyAttributes"
    assert obj.docstring == "Class with different property attributes"
    assert obj.properties["testNormal"]["attrs"] == {}
    assert obj.properties["testPublic"]["attrs"] == {"Access": "public"}
    assert obj.properties["testProtected"]["attrs"] == {"Access": "protected"}
    assert obj.properties["testPrivate"]["attrs"] == {"Access": "private"}
    assert obj.properties["testGetPublic"]["attrs"] == {
        "GetAccess": "public",
        "SetAccess": "protected",
    }
    assert obj.properties["testGetProtected"]["attrs"] == {
        "GetAccess": "protected",
        "SetAccess": "private",
    }
    assert obj.properties["testGetPrivate"]["attrs"] == {
        "GetAccess": "private",
        "SetAccess": "private",
    }
    assert obj.properties["TEST_CONSTANT"]["attrs"] == {"Constant": True}
    assert obj.properties["TEST_CONSTANT_PROTECTED"]["attrs"] == {
        "Access": "protected",
        "Constant": True,
    }
    assert obj.properties["testDependent"]["attrs"] == {"Dependent": True}
    assert obj.properties["testHidden"]["attrs"] == {"Hidden": True}


def test_ClassWithoutIndent():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithoutIndent.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithoutIndent", "test_data")
    assert obj.name == "ClassWithoutIndent"
    assert obj.docstring == "First line is not indented\nSecond line line is indented"


def test_f_with_utf8():
    mfile = os.path.join(DIRNAME, "test_data", "f_with_utf8.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_with_utf8", "test_data")
    assert obj.name == "f_with_utf8"
    assert obj.docstring == "Cambia ubicación de partículas."


def test_file_parsing_encoding_can_be_specified():
    mfile = os.path.join(DIRNAME, "test_data", "f_with_latin_1.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "f_with_latin_1", "test_data", encoding="latin-1"
    )
    assert obj.name == "f_with_latin_1"
    assert obj.docstring == "Analyse de la réponse à un créneau"


def test_file_parsing_with_no_encoding_specified():
    mfile = os.path.join(DIRNAME, "test_data", "f_with_latin_1.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_with_latin_1", "test_data")
    assert obj.name == "f_with_latin_1"
    assert obj.docstring == r"Analyse de la r\xe9ponse \xe0 un cr\xe9neau"


def test_ClassWithBuiltinOverload():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithBuiltinOverload.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithBuiltinOverload", "test_data"
    )
    assert obj.name == "ClassWithBuiltinOverload"
    assert obj.docstring == "Class that overloads a builtin"


def test_ClassWithBuiltinProperties():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithBuiltinProperties.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithBuiltinProperties", "test_data"
    )
    assert obj.name == "ClassWithBuiltinProperties"
    assert obj.docstring == "Class with properties that overload a builtin"
    assert set(obj.properties) == set(["omega", "alpha", "gamma", "beta"])
    assert obj.properties["omega"]["docstring"] == "a property"
    assert obj.properties["alpha"]["docstring"] == ("a property overloading a builtin")
    assert obj.properties["gamma"]["docstring"] == (
        "a property overloading a builtin with validation"
    )
    assert obj.properties["beta"]["docstring"] == ("another overloaded property")


# Fails when running with other test files. Warnings are already logged.
@pytest.mark.xfail
def test_f_with_name_mismatch(caplog):
    from logging import WARNING

    caplog.clear()
    mfile = os.path.join(DIRNAME, "test_data", "f_with_name_mismatch.m")
    mat_types.MatObject.parse_mfile(mfile, "f_with_name_mismatch", "test_data")
    records = caplog.record_tuples
    assert records == [
        (
            "sphinx.matlab-domain",
            WARNING,
            '[sphinxcontrib-matlabdomain] Unexpected function name: "f_name_with_mismatch".'
            ' Expected "f_with_name_mismatch"in module "test_data".',
        ),
    ]


def test_f_with_dummy_argument():
    mfile = os.path.join(DIRNAME, "test_data", "f_with_dummy_argument.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_with_dummy_argument", "")
    assert obj.name == "f_with_dummy_argument"
    assert list(obj.retv.keys()) == ["obj"]
    assert list(obj.args.keys()) == ["~", "name"]
    assert obj.docstring == "Could be a callback, where first argument is ignored."


def test_f_with_string_ellipsis():
    mfile = os.path.join(DIRNAME, "test_data", "f_with_string_ellipsis.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_with_string_ellipsis", "test_data")
    assert obj.name == "f_with_string_ellipsis"
    assert obj.docstring == "A function with a string with ellipsis"


def test_ClassWithFunctionVariable():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithFunctionVariable.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithFunctionVariable", "test_data"
    )
    assert obj.name == "ClassWithFunctionVariable"
    assert obj.docstring == "This line contains functions!"
    methods = set(obj.methods.keys())
    assert methods == {"ClassWithFunctionVariable", "anotherMethodWithFunctions"}


def test_f_inputargs_error():
    mfile = os.path.join(DIRNAME, "test_data", "f_inputargs_error.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "f_inputargs_error", "test_data")


# Fails when running with other test files. Warnings are already logged.
@pytest.mark.xfail
def test_ClassWithErrors(caplog):
    from logging import WARNING

    caplog.clear()
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithErrors.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithErrors", "test_data")
    records = caplog.record_tuples
    assert records == [
        (
            "sphinx.matlab-domain",
            WARNING,
            "[sphinxcontrib-matlabdomain] Parsing failed in test_data.ClassWithErrors. Check if valid MATLAB code.",
        ),
    ]


def test_ClassWithLineContinuation():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithLineContinuation.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithLineContinuation", "test_data"
    )
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == "ClassWithLineContinuation"


# Fails when running with other test files. Warnings are already logged.
@pytest.mark.xfail
def test_ClassWithNameMismatch(caplog):
    from logging import WARNING

    caplog.clear()
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithNameMismatch.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithNameMismatch", "test_data")
    assert isinstance(obj, mat_types.MatClass)
    records = caplog.record_tuples
    assert records == [
        (
            "sphinx.matlab-domain",
            WARNING,
            '[sphinxcontrib-matlabdomain] Unexpected class name: "ClassWithMismatch". '
            'Expected "ClassWithNameMismatch" in "test_data.ClassWithNameMismatch".',
        ),
    ]


def test_ClassWithAttributes():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithAttributes.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithAttributes", "test_data")
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == "ClassWithAttributes"
    assert obj.attrs == {"Sealed": True}


# Fails when running with other test files. Warnings are already logged.
@pytest.mark.xfail
def test_ClassWithUnknownAttributes(caplog):
    from logging import WARNING

    caplog.clear()
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithUnknownAttributes.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithUnknownAttributes", "test_data"
    )
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == "ClassWithUnknownAttributes"
    assert list(obj.methods.keys()) == ["ClassWithUnknownAttributes"]
    records = caplog.record_tuples
    assert records == [
        (
            "sphinx.matlab-domain",
            WARNING,
            '[sphinxcontrib-matlabdomain] Unexpected class attribute: "Unknown". In "test_data.ClassWithUnknownAttributes".',
        ),
    ]


def test_ClassWithEnumMethod():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithEnumMethod.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithEnumMethod", "test_data")
    assert obj.name == "ClassWithEnumMethod"
    assert list(obj.methods.keys()) == ["myfunc"]


def test_ClassWithEventMethod():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithEventMethod.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithEventMethod", "test_data")
    assert obj.name == "ClassWithEventMethod"
    assert list(obj.methods.keys()) == ["myfunc"]


def test_f_with_function_variable():
    mfile = os.path.join(DIRNAME, "test_data", "f_with_function_variable.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "f_with_function_variable", "test_data"
    )
    assert obj.name == "f_with_function_variable"
    assert list(obj.retv.keys()) == ["obj"]
    assert list(obj.args.keys()) == ["the_functions", "~"]


def test_ClassWithGetterSetter():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithGetterSetter.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithGetterSetter", "test_data")
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == "ClassWithGetterSetter"
    assert list(obj.methods.keys()) == ["ClassWithGetterSetter"]
    assert obj.properties == {
        "a": {
            "docstring": "A nice property",
            "attrs": {},
            "default": None,
            "size": None,
            "type": None,
            "validators": None,
        }
    }


def test_ClassWithDoubleQuotedString():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithDoubleQuotedString.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithDoubleQuotedString", "test_data"
    )
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == "ClassWithDoubleQuotedString"
    assert set(obj.methods.keys()) == set(["ClassWithDoubleQuotedString", "method1"])
    assert obj.properties == {
        "Property1": {
            "docstring": None,
            "attrs": {},
            "default": None,
            "size": None,
            "type": None,
            "validators": None,
        }
    }


def test_ClassWithStrings():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithStrings.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithStrings", "test_data")
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == "ClassWithStrings"
    assert set(obj.methods.keys()) == set(["raiseError"])


def test_ClassWithDummyArguments():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithDummyArguments.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithDummyArguments", "test_data")
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == "ClassWithDummyArguments"
    assert set(obj.methods.keys()) == set(["someMethod1", "someMethod2"])
    m1 = obj.methods["someMethod1"]
    assert list(m1.args.keys()) == ["obj", "argument"]
    m2 = obj.methods["someMethod2"]
    assert list(m2.args.keys()) == ["~", "argument"]


def test_ClassFolderClassdef():
    mfile = os.path.join(DIRNAME, "test_data", "@ClassFolder", "ClassFolder.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassFolder", "@ClassFolder")
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == "ClassFolder"
    assert set(obj.methods.keys()) == set(["ClassFolder", "method_inside_classdef"])
    m1 = obj.methods["ClassFolder"]
    assert list(m1.args.keys()) == ["p"]
    m2 = obj.methods["method_inside_classdef"]
    assert list(m2.args.keys()) == ["obj", "a", "b"]


def test_ClassWithMethodsWithSpaces():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithMethodsWithSpaces.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithMethodsWithSpaces", "test_data"
    )
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == "ClassWithMethodsWithSpaces"
    assert set(obj.methods.keys()) == set(["static_method"])
    assert (
        obj.docstring == "Class with methods that have space after the function name."
    )
    assert obj.methods["static_method"].attrs == {"Static": True}


def test_ClassContainingParfor():
    mfile = os.path.join(DIRNAME, "test_data", "ClassContainingParfor.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassContainingParfor", "test_data")
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == "ClassContainingParfor"
    assert set(obj.methods.keys()) == set(["test"])
    assert obj.docstring == "Parfor is a keyword"


def test_ClassWithStringEllipsis():
    mfile = os.path.join(DIRNAME, "test_data", "ClassWithStringEllipsis.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithStringEllipsis", "test_data")
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == "ClassWithStringEllipsis"
    assert set(obj.methods.keys()) == set(["test"])
    assert obj.docstring == "Contains ellipsis in string"


def test_ClassLongProperty():
    mfile = os.path.join(TESTDATA_ROOT, "ClassLongProperty.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassLongProperty", "test_data")
    assert obj.name == "ClassLongProperty"
    assert (
        obj.docstring == "test class property with long docstring\n\n"
        ":param a: the input to :class:`ClassExample`"
    )
    assert obj.properties["a"]["docstring"] == "short description"
    assert (
        obj.properties["b"]["docstring"] == "A property with a long "
        "documentation\nThis is the second line\nAnd a third"
    )
    assert obj.properties["c"]["docstring"] is None


def test_ClassWithLongPropertyDocstrings():
    mfile = os.path.join(TESTDATA_ROOT, "ClassWithLongPropertyDocstrings.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithLongPropertyDocstrings", "test_data"
    )
    assert obj.name == "ClassWithLongPropertyDocstrings"
    assert (
        obj.properties["a"]["docstring"] == "This line is deleted\n"
        "This line documents another property"
    )
    assert obj.properties["b"]["docstring"] == "Document this property"


def test_ClassWithLongPropertyTrailingEmptyDocstrings():
    mfile = os.path.join(
        TESTDATA_ROOT, "ClassWithLongPropertyTrailingEmptyDocstrings.m"
    )
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithLongPropertyTrailingEmptyDocstrings", "test_data"
    )
    assert obj.name == "ClassWithLongPropertyTrailingEmptyDocstrings"
    assert (
        obj.properties["a"]["docstring"] == "This line is deleted\n"
        "This line documents another property"
    )
    assert obj.properties["b"]["docstring"] == "Document this property"


def test_ClassWithPropertyValidators():
    mfile = os.path.join(TESTDATA_ROOT, "ClassWithPropertyValidators.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithPropertyValidators", "test_data"
    )
    assert obj.name == "ClassWithPropertyValidators"
    assert obj.properties["Location"]["docstring"] == "The location"
    assert obj.properties["Label"]["docstring"] == "The label"
    assert obj.properties["State"]["docstring"] == "The state"
    assert obj.properties["ReportLevel"]["docstring"] == "The report level"


def test_ClassWithTrailingCommentAfterBases():
    mfile = os.path.join(TESTDATA_ROOT, "ClassWithTrailingCommentAfterBases.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithTrailingCommentAfterBases", "test_data"
    )
    assert obj.name == "ClassWithTrailingCommentAfterBases"
    assert obj.bases == ["handle", "my.super.Class"]
    assert (
        obj.docstring
        == "test class methods\n\n:param a: the input to :class:`ClassWithTrailingCommentAfterBases`"
    )
    mymethod = obj.methods["mymethod"]
    assert mymethod.name == "mymethod"
    assert list(mymethod.retv.keys()) == ["c"]
    assert list(mymethod.args.keys()) == ["obj", "b"]
    assert (
        mymethod.docstring
        == "a method in :class:`ClassWithTrailingCommentAfterBases`\n\n:param b: an input to :meth:`mymethod`"
    )


def test_ClassWithEllipsisProperties():
    # TODO change this when the functionality to "nicely" generate one line defaults exists
    mfile = os.path.join(TESTDATA_ROOT, "ClassWithEllipsisProperties.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithEllipsisProperties", "test_data"
    )
    assert obj.name == "ClassWithEllipsisProperties"
    assert obj.bases == ["handle"]
    assert obj.docstring == "stuff"
    assert len(obj.methods) == 0

    assert obj.properties["A"]["docstring"] == "an expression with ellipsis"
    assert obj.properties["A"]["default"] == "1 + 2 + 3 +             4 + 5"
    assert (
        obj.properties["B"]["docstring"]
        == "a cell array with ellipsis and other array notation"
    )
    assert obj.properties["B"]["default"].startswith("{'hello', 'bye';")
    assert obj.properties["B"]["default"].endswith("}")
    assert obj.properties["C"]["docstring"] == "using end inside array"
    assert obj.properties["C"]["default"] == "ClassWithEllipsisProperties.B(2:end, 1)"
    assert obj.properties["D"]["docstring"] == "String with line continuation"
    assert obj.properties["D"]["default"] == "'...'"
    assert obj.properties["E"]["docstring"] == "The string with spaces"
    assert obj.properties["E"]["default"] == "'some string with spaces'"


#         mymethod.docstring
#         == " a method in :class:`ClassWithTrailingCommentAfterBases`\n\n :param b: an input to :meth:`mymethod`"
#     )


#  A = 1 + 2 + 3 + ... my butt
#             4 + 5; % an expression with ellipsis
#         B = {'hello', 'bye'; ...
#             'foo', 'bar';
#             'this', 'that'
#             'also' 'too'
#             } % a cell array with ellipsis and other array notation
#         C = ClassWithEllipsisProperties.B(2:end, 1) % using end inside array
#         D = '...'; % String with line continuation


def test_ClassWithTrailingSemicolons():
    mfile = os.path.join(TESTDATA_ROOT, "ClassWithTrailingSemicolons.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithTrailingSemicolons", "test_data"
    )
    assert (
        obj.docstring
        == "Smoothing like it is performed withing Cxx >v7.0 (until v8.2 at least).\nUses constant 228p_12k frequency vector:"
    )
    assert obj.bases == ["hgsetget"]
    assert list(obj.methods.keys()) == [
        "ClassWithTrailingSemicolons",
        "CxxSmoothing",
        "CalculateSigma",
    ]
    assert list(obj.properties.keys()) == [
        "m_dSmoothingWidth",
        "m_nExtL",
        "m_nExtR",
        "m_dSigmaSquared",
        "m_dFreqExtended",
        "m_dFreqLeft",
        "m_dFreqRight",
        "m_dBandWidth",
        "m_dFreq",
    ]


def test_ClassWithSeperatedComments():
    mfile = os.path.join(TESTDATA_ROOT, "ClassWithSeperatedComments.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithSeperatedComments", "test_data"
    )
    assert obj.name == "ClassWithSeperatedComments"
    assert obj.bases == []
    assert "prop" in obj.properties
    prop = obj.properties["prop"]
    assert prop["docstring"] == "Another comment"


def test_ClassWithKeywordsAsFieldnames():
    mfile = os.path.join(TESTDATA_ROOT, "ClassWithKeywordsAsFieldnames.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithKeywordsAsFieldnames", "test_data"
    )
    assert obj.name == "ClassWithKeywordsAsFieldnames"
    assert obj.bases == []
    assert "a" in obj.properties
    assert "b" in obj.properties
    assert "c" in obj.properties
    assert "calculate" in obj.methods
    meth = obj.methods["calculate"]
    assert meth.docstring == "Returns the value of `d`"


def test_ClassWithNamedAsArguments():
    mfile = os.path.join(TESTDATA_ROOT, "arguments.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "arguments", "test_data")
    assert obj.name == "arguments"
    assert obj.bases == ["handle", "matlab.mixin.Copyable"]
    assert "value" in obj.properties
    meth = obj.methods["arguments"]
    assert meth.docstring == "Constructor for arguments"
    meth = obj.methods["add"]
    assert meth.docstring == "Add new argument"


def test_ClassWithPropertyCellValues():
    mfile = os.path.join(TESTDATA_ROOT, "ClassWithPropertyCellValues.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "ClassWithPropertyCellValues", "test_data"
    )
    assert obj.name == "ClassWithPropertyCellValues"
    assert obj.bases == []
    assert "fields" in obj.properties
    assert "getLevel" in obj.methods


def test_ClassWithTests():
    mfile = os.path.join(TESTDATA_ROOT, "ClassWithTests.m")
    obj = mat_types.MatObject.parse_mfile(mfile, "ClassWithTests", "test_data")
    assert obj.name == "ClassWithTests"
    assert obj.bases == ["matlab.unittest.TestCase"]
    assert "testRunning" in obj.methods
    testRunning = obj.methods["testRunning"]
    assert testRunning.attrs["TestTags"] == ["'Unit'"]


def test_f_with_input_argument_block():
    mfile = os.path.join(DIRNAME, "test_data", "f_with_input_argument_block.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "f_with_input_argument_block", "test_data"
    )
    assert obj.name == "f_with_input_argument_block"
    assert list(obj.retv.keys()) == ["o1", "o2", "o3"]
    assert list(obj.args.keys()) == ["a1", "a2"]

    assert obj.args["a1"]["size"] == ("1", "1")
    assert obj.args["a1"]["default"] == "0"
    assert obj.args["a1"]["type"] == "double"
    assert obj.args["a1"]["docstring"] == "the first input"

    assert obj.args["a2"]["size"] == ("1", "1")
    assert obj.args["a2"]["default"] == "a1"
    assert obj.args["a1"]["type"] == "double"
    assert obj.args["a2"]["docstring"] == "another input"


def test_f_with_output_argument_block():
    mfile = os.path.join(DIRNAME, "test_data", "f_with_output_argument_block.m")
    obj = mat_types.MatObject.parse_mfile(
        mfile, "f_with_output_argument_block", "test_data"
    )
    assert obj.name == "f_with_output_argument_block"
    assert list(obj.retv.keys()) == ["o1", "o2", "o3"]
    assert list(obj.args.keys()) == ["a1", "a2"]

    assert obj.retv["o1"]["size"] == ("1", "1")
    assert obj.retv["o1"]["type"] == "double"
    assert obj.retv["o1"]["docstring"] == "Output one"

    assert obj.retv["o2"]["size"] == ("1", ":")
    assert obj.retv["o2"]["type"] == "double"
    assert obj.retv["o2"]["docstring"] == "Another output"

    assert obj.retv["o3"]["size"] == ("1", "1")
    assert obj.retv["o3"]["type"] == "double"
    assert obj.retv["o3"]["docstring"] == "A third output"
    assert obj.retv["o3"]["validators"] == ["mustBePositive"]


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__)])
