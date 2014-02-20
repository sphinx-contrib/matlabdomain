#! /usr/bin/env python

from sphinxcontrib import mat_documenters as doc
from nose.tools import eq_, ok_
import os
from pprint import pprint

DIRNAME = doc.MatObject.basedir = os.path.abspath(os.path.dirname(__file__))

def test_output_with_ellipsis():
    """
    test function output with ellipsis
    """
    # test module
    test_data = doc.MatObject.matlabify('test_data')
    test_submodule = test_data.getter('test_submodule')
    ok_(isinstance(test_submodule, doc.MatModule))
    eq_(test_submodule.__package__, 'test_data.test_submodule')
    f = test_submodule.getter('f_output_with_ellipsis')
    ok_(isinstance(f, doc.MatFunction))
    eq_(f.retv, ['output', 'with', 'ellipsis'])
    eq_(f.args, ['arg'])
    return f

def test_inheritance():
    """
    test inheritance from different module
    """
    # test module
    test_data = doc.MatObject.matlabify('test_data')
    test_submodule = test_data.getter('test_submodule')
    sfdm = test_submodule.getter('super_from_diff_mod')
    ok_(isinstance(sfdm, doc.MatClass))
    eq_(sfdm.bases,['MyAbstractClass', 'MyHandleClass'])
    bases = sfdm.getter('__bases__')
    eq_(bases['MyAbstractClass'].module, 'test_data')
    eq_(bases['MyHandleClass'].module, 'test_data')
    return sfdm

def test_property_with_ellipsis():
    """
    test class property with ellipsis in an array or in an expression
    """
    test_data = doc.MatObject.matlabify('test_data')
    ellipsis_class = test_data.getter('EllipsisProperties')
    ok_(isinstance(ellipsis_class, doc.MatClass))
    A = ellipsis_class.getter('A')
    eq_(ellipsis_class.properties['A']['default'], A.default)
    B = ellipsis_class.getter('B')
    eq_(ellipsis_class.properties['B']['default'], B.default)
    C = ellipsis_class.getter('C')
    eq_(ellipsis_class.properties['C']['default'], C.default)
    return ellipsis_class, A, B, C


if __name__ == '__main__':
    f = test_output_with_ellipsis()
    print f.__name__
    print f.__module__
    print f.__doc__
    sfdm = test_inheritance()
    print sfdm.__name__
    print sfdm.__module__
    print sfdm.__doc__
    ep, A, B, C = test_property_with_ellipsis()
    print ep.__name__
    print ep.__module__
    print ep.__doc__
    pprint(A.__dict__)
    pprint(B.__dict__)
    pprint(C.__dict__)
