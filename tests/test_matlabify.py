import os
from sphinxcontrib import documenters as doc
from nose.tools import eq_, ok_

SRC = os.path.join('test_data', 'MyHandleClass')

def test_matlabify_class():
    """
    test matlabify class
    """
    m = doc.MatObject.matlabify('test_data')
    ok_(isinstance(m, doc.MatModule))
    eq_(m.name, 'test_data')
    eq_(m.path, '.\\tests')
    my_cls = m.getter('MyHandleClass')
    ok_(isinstance(my_cls, doc.MatClass))
    eq_(my_cls.name, 'MyHandleClass')
    eq_(my_cls.path, '.\\tests\\test_data')
    eq_(my_cls.bases, ['handle'])
    #eq_(my_cls.docstring, ['handle'])
    return m, my_cls


if __name__ == '__main__':
    m, my_cls = test_matlabify_class()
    print m, my_cls
    print my_cls.docstring
