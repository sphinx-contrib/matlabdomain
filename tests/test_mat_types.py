#! /usr/bin/env python

from sphinxcontrib import mat_documenters as doc
from nose.tools import eq_, ok_
import os

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

if __name__ == '__main__':
    f = test_output_with_ellipsis()
    print f.__name__
    print f.__module__
    print f.__doc__
    sfdm = test_inheritance()
    print sfdm.__name__
    print sfdm.__module__
    print sfdm.__doc__
