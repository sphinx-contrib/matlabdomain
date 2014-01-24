#! /usr/bin/env python

from sphinxcontrib import mat_documenters as doc
from nose.tools import eq_, ok_
import json
import os
import sys

DIRNAME = doc.MatObject.basedir = os.path.abspath(os.path.dirname(__file__))

def test_matlabify_class():
    """
    test matlabify classes
    """
    # test module
    m = doc.MatObject.matlabify('test_data')
    ok_(isinstance(m, doc.MatModule))
    eq_(m.getter('__name__'), 'test_data')
    eq_(m.getter('__path__')[0], os.path.join(DIRNAME, 'test_data'))
    eq_(m.getter('__file__'), os.path.join(DIRNAME, 'test_data'))
    eq_(m.getter('__package__'), 'test_data')
    ok_(not m.getter('__doc__'))
    ok_(m.getter('__name__') in sys.modules)
    # test superclass
    my_cls = m.getter('MyHandleClass')
    ok_(isinstance(my_cls, doc.MatClass))
    eq_(my_cls.getter('__name__'), 'MyHandleClass')
    eq_(my_cls.getter('__module__'), 'test_data')
    eq_(my_cls.bases, ['handle', 'my.super.Class'])
    eq_(my_cls.attrs, {})
    eq_(my_cls.properties, {'x': {'attrs': {},
                                  'default': None,
                                  'docstring': ' a property'}})
    eq_(my_cls.getter('__doc__'), ' a handle class\n\n :param x: a variable\n')
    x = my_cls.getter('x')
    # test cls attr
    my_abc = m.getter('MyAbstractClass')
    ok_(isinstance(my_abc, doc.MatClass))
    eq_(my_abc.getter('__name__'), 'MyAbstractClass')
    eq_(my_abc.getter('__module__'), 'test_data')
    eq_(my_abc.bases, [u'MyHandleClass', 'MyClass'])
    eq_(my_abc.attrs, {'Abstract': True, 'Sealed': True})
    eq_(my_abc.properties,
        {'y': {'default': None,
               'docstring': ' y variable',
               'attrs': {'GetAccess': 'private', 'SetAccess': 'private'}},
        'version': {'default': "'0.1.1-beta'",
                    'docstring': ' version',
                    'attrs': {'Constant': True}}})
    eq_(my_abc.getter('__doc__'), ' an abstract class\n\n' +
        ' :param y: a variable\n :type y: double\n')
    y = my_abc.getter('y')
    version = my_abc.getter('version')
    return m, my_cls, x, my_abc, y, version

def test_function():
    """
    test matlabify function
    """
    # test function
    m = doc.MatObject.matlabify('test_data')
    ok_(isinstance(m, doc.MatModule))
    myfun = m.getter('myfun')
    ok_(isinstance(myfun, doc.MatFunction))
    eq_(myfun.getter('__name__'), 'myfun')
    eq_(myfun.retv, ['o1', 'o2', 'o3'])
    eq_(myfun.args, ['a1', 'a2'])
    return myfun


def test_method():
    """
    test matlabify methods
    """
    # test function
    m = doc.MatObject.matlabify('test_data')
    ok_(isinstance(m, doc.MatModule))
    my_cls_meth = m.getter('MyClass')
    ok_(isinstance(my_cls_meth, doc.MatClass))
    eq_(my_cls_meth.getter('__name__'), 'MyClass')
    constructor = my_cls_meth.getter('MyClass')
    ok_(isinstance(constructor, doc.MatMethod))
    eq_(constructor.getter('__name__'), 'MyClass')
    mymethod = my_cls_meth.getter('mymethod')
    ok_(isinstance(mymethod, doc.MatMethod))
    eq_(mymethod.getter('__name__'), 'mymethod')
    return my_cls_meth, constructor, mymethod

if __name__ == '__main__':
    m, my_cls, x, my_abc, y, version = test_matlabify_class()

    print '\nmodule: %s' % m
    print 'docstring:\n%s' % m.getter('__doc__')
   
    print '\nclass: %s' % my_cls
    print 'bases: %s' % my_cls.bases
    print 'class attributes: %s' % my_cls.attrs
    print 'properties:\n'
    print json.dumps(my_cls.properties, indent=2, sort_keys=True)
    print 'docstring:\n%s' % my_cls.getter('__doc__')

    print '\nx property: %s' % x
    print 'x default: %s' % x.default
    print 'x docstring: %s' % x.__doc__
    print 'x attrs: %s' % x.attrs
   
    print '\nclass: %s' % my_abc
    print 'bases: %s' % my_abc.bases
    print 'class attributes: %s' % my_abc.attrs
    print 'properties:\n'
    print json.dumps(my_abc.properties, indent=2, sort_keys=True)
    print 'docstring:\n%s' % my_abc.docstring

    print '\ny property: %s' % y
    print 'y docstring: %s' % y.__doc__
    print 'y default: %s' % y.default
    print 'y attrs: %s' % y.attrs
    print 'version property: %s' % version
    print 'version default: %s' % version.default
    print 'version docstring: %s' % version.__doc__
    print 'version attrs: %s' % version.attrs
    print '\n'

    myfun = test_function()
    print 'function: %s' % myfun
    print 'returns: %s' % myfun.retv
    print 'name: %s' % myfun.getter('__name__')
    print 'args: %s' % myfun.args
    print 'docstring:\n%s' % myfun.getter('__doc__')

    my_cls_meth, constructor, mymethod = test_method()
    print my_cls_meth
    print constructor
    print mymethod
