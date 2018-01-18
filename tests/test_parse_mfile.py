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
    print(dir(mymethod))
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
    print(obj.methods)
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


def test_PropTypeOld():
    mfile = os.path.join(DIRNAME, 'test_data', 'PropTypeOld.m')
    obj = mat_types.MatObject.parse_mfile(mfile, 'PropTypeOld', 'test_data')
    assert obj.name == 'PropTypeOld'
    assert obj.docstring == ""



if __name__ == '__main__':
    pytest.main([os.path.abspath(__file__)])
#
#
# def test_ellipsis_after_equals():
#     """
#     test function with ellipsis after equals
#     """
#     # test module
#     test_data = doc.MatObject.matlabify('test_data')
#     submodule = test_data.getter('submodule')
#     assert isinstance(submodule, doc.MatModule)
#     assert submodule.__package__ == 'test_data.submodule'
#     f = submodule.getter('f_ellipsis_after_equals')
#     assert isinstance(f, doc.MatFunction)
#     assert f.retv == ['output']
#     assert f.args == ['arg']
#     assert f.docstring == " Tests a function with ellipsis in the output\n"
#     return f
#
#
# def test_no_args():
#     """
#     test function with no args
#     """
#     # test module
#     test_data = doc.MatObject.matlabify('test_data')
#     submodule = test_data.getter('submodule')
#     assert isinstance(submodule, doc.MatModule)
#     assert submodule.__package__  == 'test_data.submodule'
#     f = submodule.getter('f_no_args')
#     assert isinstance(f, doc.MatFunction)
#     assert f.retv == ['output', 'with', 'ellipsis']
#     assert not f.args
#     assert f.docstring == " Tests a function with ellipsis in the output\n"
#     return f
#
# def test_no_outputs():
#     """
#     test function with no outputs
#     """
#     # test module
#     test_data = doc.MatObject.matlabify('test_data')
#     submodule = test_data.getter('submodule')
#     assert isinstance(submodule, doc.MatModule)
#     assert submodule.__package__ == 'test_data.submodule'
#     f = submodule.getter('f_no_outputs')
#     assert isinstance(f, doc.MatFunction)
#     assert not f.retv
#     assert f.args == ['arg']
#     assert f.docstring == " Tests a function with ellipsis in the output\n"
#     return f
#
# def test_output_with_ellipsis():
#     """
#     test function output with ellipsis
#     """
#     # test module
#     test_data = doc.MatObject.matlabify('test_data')
#     submodule = test_data.getter('submodule')
#     assert isinstance(submodule, doc.MatModule)
#     assert submodule.__package__ == 'test_data.submodule'
#     f = submodule.getter('f_output_with_ellipsis')
#     assert isinstance(f, doc.MatFunction)
#     assert f.retv == ['output', 'with', 'ellipsis']
#     assert f.args == ['arg']
#     assert f.docstring == " Tests a function with ellipsis in the output\n"
#     return f
#
# def test_output_without_commas():
#     """
#     test function output without commas
#     """
#     # test module
#     test_data = doc.MatObject.matlabify('test_data')
#     submodule = test_data.getter('submodule')
#     assert isinstance(submodule, doc.MatModule)
#     assert submodule.__package__ == 'test_data.submodule'
#     f = submodule.getter('f_output_without_commas')
#     assert isinstance(f, doc.MatFunction)
#     assert f.retv == ['output', 'with', 'ellipsis']
#     assert f.args == ['arg']
#     assert f.docstring == " Tests a function with ellipsis in the output\n"
#     return f
#
# def test_inheritance():
#     """
#     test inheritance from different module
#     """
#     # test module
#     test_data = doc.MatObject.matlabify('test_data')
#     submodule = test_data.getter('submodule')
#     sfdm = submodule.getter('super_from_diff_mod')
#     assert isinstance(sfdm, doc.MatClass)
#     assert sfdm.bases == ['MyAbstractClass', 'MyHandleClass']
#     bases = sfdm.getter('__bases__')
#     assert bases['MyAbstractClass'].module == 'test_data'
#     assert bases['MyHandleClass'].module == 'test_data'
#     assert sfdm.docstring == " class which inherits bases from a different module\n"
#     return sfdm
#
# def test_property_with_ellipsis():
#     """
#     test class property with ellipsis in an array or in an expression
#     """
#     # TODO: Why does properties eat the trailing '\n'?
#     test_data = doc.MatObject.matlabify('test_data')
#     ellipsis_class = test_data.getter('EllipsisProperties')
#     assert isinstance(ellipsis_class, doc.MatClass)
#     assert ellipsis_class.docstring == " stuff\n"
#     A = ellipsis_class.getter('A')
#     assert ellipsis_class.properties['A']['default'] == A.default
#     assert A.docstring == " an expression with ellipsis"
#     B = ellipsis_class.getter('B')
#     assert ellipsis_class.properties['B']['default'] == B.default
#     assert B.docstring == " a cell array with ellipsis and other array notation"
#     C = ellipsis_class.getter('C')
#     assert ellipsis_class.properties['C']['default'] == C.default
#     assert C.docstring == " using end inside array"
#     return ellipsis_class, A, B, C
#
# def test_function_with_comment_after_docstring():
#     test_data = doc.MatObject.matlabify('test_data')
#     submodule = test_data.getter('submodule')
#     assert isinstance(submodule, doc.MatModule)
#     assert submodule.__package__ == 'test_data.submodule'
#     f = submodule.getter('f_with_comment_after_docstring')
#     assert f.args == ['input']
#     assert f.retv == ['output']
#     assert f.docstring == " Tests a function with comments after docstring\n"
#
#
# if __name__ == '__main__':
#     f1 = test_ellipsis_after_equals
#     print(f1.__name__)
#     print(f1.__module__)
#     print(f1.__doc__)
#     f2 = test_no_args()
#     print(f2.__name__)
#     print(f2.__module__)
#     print(f2.__doc__)
#     f3 = test_no_outputs()
#     print(f3.__name__)
#     print(f3.__module__)
#     print(f3.__doc__)
#     f4 = test_output_with_ellipsis()
#     print(f4.__name__)
#     print(f4.__module__)
#     print(f4.__doc__)
#     f5 = test_output_without_commas()
#     print(f5.__name__)
#     print(f5.__module__)
#     print(f5.__doc__)
#     sfdm = test_inheritance()
#     print(sfdm.__name__)
#     print(sfdm.__module__)
#     print(sfdm.__doc__)
#     ep, A, B, C = test_property_with_ellipsis()
#     print(ep.__name__)
#     print(ep.__module__)
#     print(ep.__doc__)
#     pprint(A.__dict__)
#     pprint(B.__dict__)
#     pprint(C.__dict__)
#     test_function_with_comment_after_docstring()
