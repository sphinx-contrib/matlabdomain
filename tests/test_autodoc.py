# -*- coding: utf-8 -*-
"""
    test_autodoc
    ~~~~~~~~~~~~

    Test the autodoc extension.

    :copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import pickle
import os

import pytest

from sphinx import addnodes
from sphinx import version_info
from sphinx.testing.fixtures import test_params, make_app
from sphinx.testing.path import path


@pytest.fixture(scope='module')
def rootdir():
    return path(os.path.dirname(__file__)).abspath()


def test_setup(make_app, rootdir):
    srcdir = rootdir / 'roots' / 'test_autodoc'
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / 'contents.doctree').bytes())

    assert isinstance(content[3], addnodes.desc)
    assert content[3][0].astext() == 'class target.ClassExamplea'
    assert content[3][1].astext() == """Bases: handle

Example class

Parameters

a – a property of ClassExample



a = None

a property



mymethodb

A method in ClassExample

Parameters

b – an input to mymethod()"""
    # We still have warning regarding overriding auto...
    # assert app._warning.getvalue() == ''


if __name__ == '__main__':
    pytest.main([__file__])