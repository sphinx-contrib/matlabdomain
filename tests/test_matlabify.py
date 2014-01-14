import os
from sphinxcontrib import documenters as doc
from nose.tools import eq_, ok_

SRC = os.path.join('test_data', 'MyHandleClass')

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
    eq_(my_cls.bases, ['handle'])
    eq_(my_cls.docstring, '% a handle class\n% :param x: a variable\n')
    # test cls attr
    my_abc = m.getter('MyAbstractClass')
    ok_(isinstance(my_abc, doc.MatClass))
    eq_(my_abc.name, 'MyAbstractClass')
    eq_(my_abc.path, '.\\tests\\test_data')
    eq_(my_abc.attrs, {'Abstract': 'true'})
    eq_(my_abc.docstring,
        '% an abstract class with tabs\n% :param y: a variable\n% :type y: double\n')
    return m, my_cls, my_abc


if __name__ == '__main__':
    m, my_cls, my_abc = test_matlabify_class()
    print '\nmodule: %s\n' % m
    print 'class: %s' % my_cls
    print 'bases: %s' % my_cls.bases
    print 'docstring:\n%s\n' % my_cls.docstring
    print 'class: %s' % my_abc
    print 'class attributes: %s' % my_abc.attrs
    print 'docstring:\n%s\n' % my_abc.docstring
