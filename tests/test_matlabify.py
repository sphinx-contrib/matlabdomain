#! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from sphinxcontrib import mat_documenters as doc
from sphinxcontrib.mat_types import modules
import os
import sys
import pytest

from sphinx.testing.fixtures import test_params, make_app
from sphinx.testing.path import path


rootdir = path(os.path.dirname(__file__)).abspath()
matlab_src_dir = os.path.join(rootdir, 'test_data')
doc.MatObject.basedir = matlab_src_dir


@pytest.fixture
def app(make_app):
    # Create app to setup build environment
    srcdir = rootdir / 'test_docs'
    app = make_app(srcdir=srcdir)
    doc.MatObject.basedir = app.config.matlab_src_dir
    return app


@pytest.fixture
def mod(app):
    return doc.MatObject.matlabify('test_data')


def test_empty():
    assert doc.MatObject.matlabify('') is None


def test_unknown():
    assert doc.MatObject.matlabify('not_test_data') is None


def test_script(mod, caplog):

    script = mod.getter('script')
    assert isinstance(script, doc.MatScript)


def test_module(mod):
    assert mod.getter('__name__') == 'test_data'
    assert mod.getter('__path__')[0] == matlab_src_dir
    assert mod.getter('__file__') == matlab_src_dir
    assert mod.getter('__package__') == 'test_data'
    assert not mod.getter('__module__')
    assert not mod.getter('__doc__')
    all_items = set(mod.getter('__all__'))
    expected_items = {'+package', '@ClassFolder', 'ClassAbstract', 'ClassExample', 'ClassBySource',
                      'ClassInheritHandle', 'ClassWithEllipsisProperties',
                      'ClassWithEndOfLineComment', 'f_example', 'f_with_nested_function',
                      'submodule', 'script', 'Bool', 'ClassWithEvent',
                      'f_no_input_no_output_no_parentheses', 'ClassWithCommentHeader',
                      'f_with_comment_header', 'f_with_dummy_argument', 'script_with_comment_header',
                      'script_with_comment_header_2', 'script_with_comment_header_3',
                      'script_with_comment_header_4',
                      'PropTypeOld', 'ValidateProps', 'ClassWithMethodAttributes', 'ClassWithPropertyAttributes',
                      'ClassWithoutIndent', 'f_with_utf8', 'f_with_latin_1', 'f_with_name_mismatch',
                      'ClassWithBuiltinOverload', 'ClassWithFunctionVariable',
                      'ClassWithErrors', 'f_inputargs_error',
                      'ClassWithAttributes', 'ClassWithLineContinuation',
                      'ClassWithUnknownAttributes', 'ClassWithNameMismatch',
                      'ClassWithEnumMethod', 'ClassWithEventMethod', 'f_with_function_variable',
                      'ClassWithUndocumentedMembers', 'ClassWithGetterSetter',
                      'ClassWithDoubleQuotedString', 'ClassWithDummyArguments',
                      'ClassWithStrings', 'ClassWithFunctionArguments'}
    assert all_items == expected_items
    assert mod.getter('__name__') in modules


def test_parse_twice(mod):
    mod2 = doc.MatObject.matlabify('test_data')
    assert mod == mod2


def test_classes(mod):
    assert isinstance(mod, doc.MatModule)

    # test superclass
    cls = mod.getter('ClassInheritHandle')
    assert isinstance(cls, doc.MatClass)
    assert cls.getter('__name__') == 'ClassInheritHandle'
    assert cls.getter('__module__') == 'test_data'
    assert cls.bases == ['handle', 'my.super.Class']
    assert cls.attrs == {}
    assert cls.properties == {'x': {'attrs': {},
                                    'default': None,
                                    'docstring': ' a property'}

                              }
    assert cls.getter('__doc__') == ' a handle class\n\n :param x: a variable\n'


def test_abstract_class(mod):
    # test abstract class with attributes
    abc = mod.getter('ClassAbstract')
    assert isinstance(abc, doc.MatClass)
    assert abc.getter('__name__') == 'ClassAbstract'
    assert abc.getter('__module__') == 'test_data'
    assert 'ClassInheritHandle' in abc.getter('__bases__')
    assert 'ClassExample' in abc.getter('__bases__')
    assert abc.bases == ['ClassInheritHandle', 'ClassExample']
    assert abc.attrs == {'Abstract': True, 'Sealed': True}
    assert abc.properties == {'y': {'default': None,
                                    'docstring': ' y variable',
                                    'attrs': {'GetAccess': 'private', 'SetAccess': 'private'},
                                    },
                              'version': {'default': "'0.1.1-beta'",
                                          'docstring': ' version',
                                          'attrs': {'Constant': True},
                                          }
                              }
    assert abc.getter('__doc__') == ' an abstract class\n\n :param y: a variable\n :type y: double\n'
    assert abc.getter('__doc__') == abc.docstring

    abc_y = abc.getter('y')
    assert isinstance(abc_y, doc.MatProperty)
    assert abc_y.default is None
    assert abc_y.docstring == ' y variable'
    assert abc_y.attrs == {'SetAccess': 'private', 'GetAccess': 'private'}

    abc_version = abc.getter('version')
    assert isinstance(abc_version, doc.MatProperty)
    assert abc_version.default == "'0.1.1-beta'"
    assert abc_version.docstring == ' version'
    assert abc_version.attrs == {'Constant': True}


def test_class_method(mod):
    cls_meth = mod.getter('ClassExample')
    assert isinstance(cls_meth, doc.MatClass)
    assert cls_meth.getter('__name__') == 'ClassExample'
    assert cls_meth.docstring == " test class methods\n\n :param a: the input to :class:`ClassExample`\n"
    constructor = cls_meth.getter('ClassExample')
    assert isinstance(constructor, doc.MatMethod)
    assert constructor.getter('__name__') == 'ClassExample'
    mymethod = cls_meth.getter('mymethod')
    assert isinstance(mymethod, doc.MatMethod)
    assert mymethod.getter('__name__') == 'mymethod'
    # TODO: mymethod.args will contain ['obj', 'b'] if run standalone
    #       but if test_autodoc.py is run, the 'obj' is removed
    assert mymethod.args
    assert mymethod.args[-1] == 'b'
    assert mymethod.retv == ['c']
    assert mymethod.docstring == " a method in :class:`ClassExample`\n\n :param b: an input to :meth:`mymethod`\n"
    return cls_meth, constructor, mymethod


def test_submodule_class(mod):
    cls = mod.getter('submodule.TestFibonacci')
    assert isinstance(cls, doc.MatClass)
    assert cls.docstring == " Test of MATLAB unittest method attributes\n"
    assert cls.attrs == {}
    assert cls.bases == ['matlab.unittest.TestCase']
    assert 'compareFirstThreeElementsToExpected' in cls.methods
    assert cls.module == 'test_data.submodule'
    assert cls.properties == {}
    method = cls.getter('compareFirstThreeElementsToExpected')
    assert isinstance(method, doc.MatMethod)
    assert method.name == 'compareFirstThreeElementsToExpected'
    assert method.retv is None
    assert method.args == ['tc']
    assert method.docstring == ' Test case that compares first three elements\n'
    assert method.attrs == {'Test': True}


def test_folder_class(mod):
    cls_mod = mod.getter('@ClassFolder')
    assert isinstance(cls_mod, doc.MatModule)
    cls = cls_mod.getter('ClassFolder')
    assert cls.docstring == " A class in a folder\n"
    assert cls.attrs == {}
    assert cls.bases == []
    assert cls.module == 'test_data.@ClassFolder'
    assert cls.properties == {'p': {'attrs': {},
                                    'default': None,
                                    'docstring': ' a property of a class folder',
                                    }}

    assert 'ClassFolder' in cls.methods

    func = cls_mod.getter('a_static_func')
    assert isinstance(func, doc.MatFunction)
    assert func.name == 'a_static_func'
    assert func.args == ['args']
    assert func.retv == ['retv']
    assert func.docstring == ' method in :class:`~test_data.@ClassFolder`\n'
    func = cls_mod.getter('classMethod')
    assert isinstance(func, doc.MatFunction)
    assert func.name == 'classMethod'
    assert func.args == ['obj', 'varargin']
    assert func.retv == ['varargout']
    assert func.docstring == ' CLASSMETHOD A function within a package\n\n :param obj: An instance of this class.\n :param varargin: Variable input arguments.\n :returns: varargout\n'


def test_function(mod):
    assert isinstance(mod, doc.MatModule)
    func = mod.getter('f_example')
    assert isinstance(func, doc.MatFunction)
    assert func.getter('__name__') == 'f_example'
    assert func.retv == ['o1', 'o2', 'o3']
    assert func.args == ['a1', 'a2']
    assert func.docstring == " a fun function\n\n :param a1: the first input\n :param a2: another input\n :returns: ``[o1, o2, o3]`` some outputs\n"


def test_function_getter(mod):
    assert isinstance(mod, doc.MatModule)
    func = mod.getter('f_example')
    assert isinstance(func, doc.MatFunction)
    assert func.getter('__name__') == 'f_example'
    assert func.getter('__doc__') == ' a fun function\n\n :param a1: the first input\n :param a2: another input\n :returns: ``[o1, o2, o3]`` some outputs\n'
    assert func.getter('__module__') == 'test_data'


def test_package_function(mod):
    assert isinstance(mod, doc.MatModule)
    func = mod.getter('f_example')
    assert isinstance(func, doc.MatFunction)
    assert func.getter('__name__') == 'f_example'
    assert func.retv == ['o1', 'o2', 'o3']
    assert func.args == ['a1', 'a2']
    assert func.docstring == " a fun function\n\n :param a1: the first input\n :param a2: another input\n :returns: ``[o1, o2, o3]`` some outputs\n"


if __name__ == '__main__':
    pytest.main([__file__])
