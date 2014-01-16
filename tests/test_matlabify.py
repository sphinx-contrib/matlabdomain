#! /usr/bin/env python

from sphinxcontrib import documenters as doc
from nose.tools import eq_, ok_
import json

def test_matlabify_class():
    """
    test matlabify class
    """
    # test module
    m = doc.MatObject.matlabify('test_data')
    ok_(isinstance(m, doc.MatModule))
    eq_(m.name, 'test_data')
    eq_(m.path, '.\\tests')
    # test superclass
    my_cls = m.getter('MyHandleClass')
    ok_(isinstance(my_cls, doc.MatClass))
    eq_(my_cls.name, 'MyHandleClass')
    eq_(my_cls.path, '.\\tests\\test_data')
    eq_(my_cls.bases, ['handle', 'my.super.Class'])
    eq_(my_cls.attrs, {})
    eq_(my_cls.properties, {'x': {'attrs': {},
                                  'default': None,
                                  'docstring': '% a property'}})
    eq_(my_cls.docstring, '% a handle class\n% :param x: a variable\n')
    x = my_cls.getter('x')
    # test cls attr
    my_abc = m.getter('MyAbstractClass')
    ok_(isinstance(my_abc, doc.MatClass))
    eq_(my_abc.name, 'MyAbstractClass')
    eq_(my_abc.path, '.\\tests\\test_data')
    eq_(my_abc.bases, [])
    eq_(my_abc.attrs, {'Abstract': True, 'Sealed': True})
    eq_(my_abc.properties,
        {'y': {'default': None,
               'docstring': '% y variable',
               'attrs': {'GetAccess': 'private', 'SetAccess': 'private'}},
        'version': {'default': "'0.1.1-beta'",
                    'docstring': '% version',
                    'attrs': {'Constant': True}}})
    eq_(my_abc.docstring, '% an abstract class with tabs\n' +
        '% :param y: a variable\n% :type y: double\n')
    y = my_abc.getter('y')
    version = my_abc.getter('version')
    return m, my_cls, x, my_abc, y, version


if __name__ == '__main__':
    m, my_cls, x, my_abc, y, version = test_matlabify_class()

    print '\nmodule: %s' % m
   
    print '\nclass: %s' % my_cls
    print 'bases: %s' % my_cls.bases
    print 'class attributes: %s' % my_cls.attrs
    print 'properties:\n'
    print json.dumps(my_cls.properties, indent=2, sort_keys=True)
    print 'docstring:\n%s' % my_cls.docstring

    print '\nx property: %s' % x
   
    print '\nclass: %s' % my_abc
    print 'bases: %s' % my_abc.bases
    print 'class attributes: %s' % my_abc.attrs
    print 'properties:\n'
    print json.dumps(my_abc.properties, indent=2, sort_keys=True)
    print 'docstring:\n%s' % my_abc.docstring

    print '\ny property: %s' % y
    print '\nversion property: %s' % version
    print '\n'
