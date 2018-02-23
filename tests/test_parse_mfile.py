#! /usr/bin/env python
from __future__ import print_function
from sphinxcontrib import mat_types
import os
import pytest
from pprint import pprint


DIRNAME = os.path.abspath(os.path.dirname(__file__))
TESTDATA_ROOT = os.path.join(DIRNAME, 'test_data')
TESTDATA_SUB = os.path.join(TESTDATA_ROOT, 'submodule')


def test_ClassExample():
    mfile = os.path.join(TESTDATA_ROOT, 'ClassExample.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'ClassExample', 'test_data')
    assert obj.name == 'ClassExample'
    assert obj.docstring == " test class methods\n\n :param a: the input to :class:`ClassExample`\n"
    mymethod = obj.methods['mymethod']
    assert mymethod.name == 'mymethod'
    assert mymethod.retv == ['c']
    assert mymethod.args == ['obj', 'b']
    assert mymethod.docstring == " a method in :class:`ClassExample`\n\n :param b: an input to :meth:`mymethod`\n"


def test_comment_after_docstring():
    mfile = os.path.join(TESTDATA_SUB, 'f_comment_after_docstring.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_comment_after_docstring', '')
    assert obj.name == 'f_comment_after_docstring'
    assert obj.retv == ['output']
    assert obj.args == ['input']
    assert obj.docstring == ' Tests a function with comments after docstring\n'


def test_docstring_no_newline():
    mfile = os.path.join(TESTDATA_SUB, 'f_docstring_no_newline.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_docstring_no_newline', '')
    assert obj.name == 'f_docstring_no_newline'
    assert obj.retv == ['y']
    assert obj.args is None
    assert obj.docstring == ' Test a function without a newline after docstring\n'


def test_ellipsis_after_equals():
    mfile = os.path.join(TESTDATA_SUB, 'f_ellipsis_after_equals.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_ellipsis_after_equals', '')
    assert obj.name == 'f_ellipsis_after_equals'
    assert obj.retv == ['output']
    assert obj.args == ['arg']
    assert obj.docstring == ' Tests a function with ellipsis after equals\n'


def test_ellipsis_empty_output():
    mfile = os.path.join(TESTDATA_SUB, 'f_ellipsis_empty_output.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_ellipsis_empty_output', '')
    assert obj.name == 'f_ellipsis_empty_output'
    assert obj.retv is None
    assert obj.args == ['arg']
    assert obj.docstring == ' Tests a function with ellipsis in the output\n'


def test_ellipsis_in_comment():
    mfile = os.path.join(TESTDATA_SUB, 'f_ellipsis_in_comment.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_ellipsis_in_comment', '')
    assert obj.name == 'f_ellipsis_in_comment'
    assert obj.retv == ['y']
    assert obj.args == ['x']
    assert obj.docstring == ' Tests a function with ellipsis in the comment ...\n'


def test_ellipsis_in_output():
    mfile = os.path.join(TESTDATA_SUB, 'f_ellipsis_in_output.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_ellipsis_in_output', '')
    assert obj.name == 'f_ellipsis_in_output'
    assert obj.retv == ['output', 'with', 'ellipsis']
    assert obj.args == ['arg']
    assert obj.docstring == ' Tests a function with ellipsis in the output\n'


def test_ellipsis_in_output_multiple():
    mfile = os.path.join(TESTDATA_SUB, 'f_ellipsis_in_output_multiple.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_ellipsis_in_output_multiple', '')
    assert obj.name == 'f_ellipsis_in_output_multiple'
    assert obj.retv == ['output', 'with', 'ellipsis']
    assert obj.args == ['arg']
    assert obj.docstring == ' Tests a function with multiple ellipsis in the output\n'


def test_no_docstring():
    mfile = os.path.join(TESTDATA_SUB, 'f_no_docstring.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_no_docstring', '')
    assert obj.name == 'f_no_docstring'
    assert obj.retv == ['y']
    assert obj.args is None
    assert obj.docstring == ''


def test_no_output():
    mfile = os.path.join(TESTDATA_SUB, 'f_no_output.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_no_output', '')
    assert obj.name == 'f_no_output'
    assert obj.retv is None
    assert obj.args == ['arg']
    assert obj.docstring == ' A function with no outputs\n'


def test_no_input_parentheses():
    mfile = os.path.join(TESTDATA_SUB, 'f_no_input_parentheses.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_no_input_parentheses', '')
    assert obj.name == 'f_no_input_parentheses'
    assert obj.retv == ['y']
    assert obj.args is None
    assert obj.docstring == ' Tests a function without parentheses in input\n'


def test_no_spaces():
    mfile = os.path.join(TESTDATA_SUB, 'f_no_spaces.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_no_spaces', '')
    assert obj.name == 'f_no_spaces'
    assert obj.retv == ['a', 'b', 'c']
    assert obj.args == ['x', 'y', 'z']
    assert obj.docstring == " Tests a function with no spaces in function signature\n"


def test_ClassWithEndOfLineComment():
    mfile = os.path.join(DIRNAME, 'test_data', 'ClassWithEndOfLineComment.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'ClassWithEndOfLineComment', 'test_data')
    assert obj.name == 'ClassWithEndOfLineComment'
    assert obj.docstring == ''
    method_test1 = obj.methods['test1']
    assert method_test1.name == 'test1'
    # TODO: Trailing comment get passed as docstring
    # assert method_test.docstring == ''
    method_test2 = obj.methods['test2']
    assert method_test2.name == 'test2'
    # TODO: Trailing comment get passed as docstring
    # assert method_test1.docstring == ''


def test_ClassWithEvent():
    # TODO: handle 'events' block
    mfile = os.path.join(DIRNAME, 'test_data', 'ClassWithEvent.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'ClassWithEvent', 'test_data')
    assert obj.name == 'ClassWithEvent'
    assert obj.docstring == ""


def test_EnumerationBool():
    # TODO: handle 'enumeration' block
    mfile = os.path.join(DIRNAME, 'test_data', 'Bool.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'Bool', 'test_data')
    assert obj.name == 'Bool'
    assert obj.docstring == ""


def test_no_input_no_output_no_parentheses():
    mfile = os.path.join(DIRNAME, 'test_data', 'f_no_input_no_output_no_parentheses.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_no_input_no_output_no_parentheses', 'test_data')
    assert obj.name == 'f_no_input_no_output_no_parentheses'
    assert obj.docstring == " Tests a function without parentheses in input and no return value\n"


def test_ClassWithCommentHeader():
    mfile = os.path.join(DIRNAME, 'test_data', 'ClassWithCommentHeader.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'ClassWithCommentHeader', 'test_data')
    assert obj.name == 'ClassWithCommentHeader'
    assert obj.docstring == " A class with a comment header on the top.\n"
    method_get_tform = obj.methods['getTransformation']
    assert method_get_tform.name == 'getTransformation'
    assert method_get_tform.retv == ['tform']
    assert method_get_tform.args == ['obj']


def test_with_comment_header():
    mfile = os.path.join(DIRNAME, 'test_data', 'f_with_comment_header.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'f_with_comment_header', 'test_data')
    assert obj.name == 'f_with_comment_header'
    assert obj.docstring == " A simple function with a comment header on the top.\n"


def test_script_with_comment_header():
    mfile = os.path.join(DIRNAME, 'test_data', 'script_with_comment_header.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'script_with_comment_header', 'test_data')
    assert obj.docstring == ""


def test_PropTypeOld():
    mfile = os.path.join(DIRNAME, 'test_data', 'PropTypeOld.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'PropTypeOld', 'test_data')
    assert obj.name == 'PropTypeOld'
    assert obj.docstring == ""
    assert obj.properties == {'link_name': {'docstring': None, 'attrs': {},
                                            'default': "'none'"},  # 'type': ['char']
                              'pos': {'docstring': None, 'attrs': {},
                                      'default': 'zeros(3,1)'},  # 'type': ['double', 'vector'],
                              'rotm': {'docstring': None, 'attrs': {},
                                       'default': 'zeros(3,3)'},  # 'type': ['double', 'matrix'],
                              'idx': {'docstring': None, 'attrs': {},
                                      'default': '0'}  # 'type': ['uint8', 'scalar'],
                              }


def test_ValidateProps():
    mfile = os.path.join(DIRNAME, 'test_data', 'ValidateProps.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'ValidateProps', 'test_data')
    assert obj.name == 'ValidateProps'
    assert obj.docstring == ""


if __name__ == '__main__':
    pytest.main([os.path.abspath(__file__)])
