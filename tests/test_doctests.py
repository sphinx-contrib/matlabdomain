# -*- coding: utf-8 -*-
from __future__ import unicode_literals 
import pickle
import os

import pytest

from docutils import nodes
from sphinx import addnodes
from sphinx import version_info
from sphinx.testing.fixtures import test_params, make_app
from sphinx.testing.path import path


@pytest.fixture(scope='module')
def reload_docutils():
    """ As we monkey-patch 'Body' in the 'states' module, we need to reload it
    to ensure that we can actually apply the change if it has already been
    loaded in another test.
    """
    import docutils.parsers.rst.states
    import importlib
    importlib.reload(docutils.parsers.rst.states)  


@pytest.fixture(scope='module')
def rootdir(reload_docutils):   
    return path(os.path.dirname(__file__)).abspath()


def test_setup(make_app, rootdir):
    srcdir = rootdir / 'roots' / 'test_doctests'
    app = make_app(srcdir=srcdir, freshenv=True)
    app.env.matlab_enable_doctest = True
    
    app.builder.build_all()

    contents = app.env.get_doctree('contents')    
    doctest_blocks = [node for node in contents.traverse(nodes.doctest_block)]
    assert len(doctest_blocks) == 1
    assert doctest_blocks[0].astext() == '>> getMyNumber()\n5'


if __name__ == '__main__':
    pytest.main([__file__])