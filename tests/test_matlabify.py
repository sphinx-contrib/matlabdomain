#! /usr/bin/env python
from __future__ import print_function
from sphinxcontrib import mat_documenters as doc
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
    assert isinstance(m, doc.MatModule)
    assert m.getter('__name__') == 'test_data'
    assert m.getter('__path__')[0] == os.path.join(DIRNAME, 'test_data')
    assert m.getter('__file__') == os.path.join(DIRNAME, 'test_data')
    assert m.getter('__package__') == 'test_data'
    assert not m.getter('__doc__')
    assert m.getter('__name__') in sys.modules
    # test superclass
    my_cls = m.getter('MyHandleClass')
    assert isinstance(my_cls, doc.MatClass)
    assert my_cls.getter('__name__') == 'MyHandleClass'
    assert my_cls.getter('__module__') == 'test_data'
    assert my_cls.bases == ['handle', 'my.super.Class']
    assert my_cls.attrs == {}
    assert my_cls.properties == {'x': {'attrs': {}, 'default': None, 'docstring': ' a property'}}
    assert my_cls.getter('__doc__') == ' a handle class\n\n :param x: a variable\n'
    x = my_cls.getter('x')
    # test cls attr
    my_abc = m.getter('MyAbstractClass')
    assert isinstance(my_abc, doc.MatClass)
    assert my_abc.getter('__name__') == 'MyAbstractClass'
    assert my_abc.getter('__module__') == 'test_data'
    assert my_abc.bases == ['MyHandleClass', 'MyClass']
    assert my_abc.attrs == {'Abstract': True, 'Sealed': True}
    assert my_abc.properties == {'y': {'default': None,
                                       'docstring': ' y variable',
                                       'attrs': {'GetAccess': 'private', 'SetAccess': 'private'}},
                               'version': {'default': "'0.1.1-beta'",
                     'docstring': ' version',
                     'attrs': {'Constant': True}}}
    assert my_abc.getter('__doc__') ==  ' an abstract class\n\n :param y: a variable\n :type y: double\n'
    y = my_abc.getter('y')
    version = my_abc.getter('version')
    return m, my_cls, x, my_abc, y, version

def test_function():
    """
    test matlabify function
    """
    # test function
    m = doc.MatObject.matlabify('test_data')
    assert isinstance(m, doc.MatModule)
    myfun = m.getter('myfun')
    assert isinstance(myfun, doc.MatFunction)
    assert myfun.getter('__name__') == 'myfun'
    assert myfun.retv == ['o1', 'o2', 'o3']
    assert myfun.args == ['a1', 'a2']
    assert myfun.docstring == " a fun function\n\n :param a1: the first input\n :param a2: another input\n :returns: ``[o1, o2, o3]`` some outputs\n"
    return myfun


def test_method():
    """
    test matlabify methods
    """
    # test function
    m = doc.MatObject.matlabify('test_data')
    assert isinstance(m, doc.MatModule)
    my_cls_meth = m.getter('MyClass')
    assert isinstance(my_cls_meth, doc.MatClass)
    assert my_cls_meth.getter('__name__') == 'MyClass'
    assert my_cls_meth.docstring == " test class methods\n\n :param a: the input to :class:`MyClass`\n"
    constructor = my_cls_meth.getter('MyClass')
    assert isinstance(constructor, doc.MatMethod)
    assert constructor.getter('__name__') == 'MyClass'
    mymethod = my_cls_meth.getter('mymethod')
    assert isinstance(mymethod, doc.MatMethod)
    assert mymethod.getter('__name__') == 'mymethod'
    assert mymethod.args == ['obj', 'b']
    assert mymethod.retv == ['c']
    assert mymethod.docstring == " a method in :class:`MyClass`\n\n :param b: an input to :meth:`mymethod`\n"
    return my_cls_meth, constructor, mymethod

if __name__ == '__main__':
    m, my_cls, x, my_abc, y, version = test_matlabify_class()

    print('\nmodule: %s' % m)
    print('docstring:\n%s' % m.getter('__doc__'))

    print('\nclass: %s' % my_cls)
    print('bases: %s' % my_cls.bases)
    print('class attributes: %s' % my_cls.attrs)
    print('properties:\n')
    print(json.dumps(my_cls.properties, indent=2, sort_keys=True))
    print('docstring:\n%s' % my_cls.getter('__doc__'))

    print('\nx property: %s' % x)
    print('x default: %s' % x.default)
    print('x docstring: %s' % x.__doc__)
    print('x attrs: %s' % x.attrs)

    print('\nclass: %s' % my_abc)
    print('bases: %s' % my_abc.bases)
    print('class attributes: %s' % my_abc.attrs)
    print('properties:\n')
    print(json.dumps(my_abc.properties, indent=2, sort_keys=True))
    print('docstring:\n%s' % my_abc.docstring)

    print('\ny property: %s' % y)
    print('y docstring: %s' % y.__doc__)
    print('y default: %s' % y.default)
    print('y attrs: %s' % y.attrs)
    print('version property: %s' % version)
    print('version default: %s' % version.default)
    print('version docstring: %s' % version.__doc__)
    print('version attrs: %s' % version.attrs)
    print('\n')

    myfun = test_function()
    print('function: %s' % myfun)
    print('returns: %s' % myfun.retv)
    print('name: %s' % myfun.getter('__name__'))
    print('args: %s' % myfun.args)
    print('docstring:\n%s' % myfun.getter('__doc__'))

    my_cls_meth, constructor, mymethod = test_method()
    print(my_cls_meth)
    print(constructor)
    print(mymethod)
