from __future__ import print_function
import pytest
import sphinx
import sphinxcontrib.matlab as mat
from sphinx.testing.fixtures import test_params, make_app
from sphinx.testing.path import path
from sphinx.testing.util import assert_node
from sphinx import addnodes
import os

@pytest.fixture(scope='module')
def rootdir():
    return path(os.path.dirname(__file__)).abspath()


def test_setup(rootdir, make_app):
    srcdir = rootdir / 'test_docs'
    app = make_app('dummy', srcdir=srcdir)
    app.builder.build_all()

    def assert_refnode(node, module_name, class_name, target, reftype=None,
                       domain='mat'):
        attributes = {
            'refdomain': domain,
            'reftarget': target,
        }
        if reftype is not None:
            attributes['reftype'] = reftype
        if module_name is not False:
            attributes['mat:module'] = module_name
        if class_name is not False:
            attributes['mat:class'] = class_name
        assert_node(node, **attributes)

    doctree = app.env.get_doctree('index')
    refnodes = list(doctree.traverse(addnodes.pending_xref))

    assert_refnode(refnodes[0],  u'test_data', None, u'test_data', u'mod')
    #assert_refnode(refnodes[1], u'test_data', u'ClassInheritHandle', u'handle')
    app.cleanup()


if __name__ == '__main__':
    pytest.main([__file__])

