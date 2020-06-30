# -*- coding: utf-8 -*-
"""
    test_package_function
    ~~~~~~~~~~~~~~~~~~~~~

    Test the autodoc extension with the matlab_keep_package_prefix option.

    :copyright: Copyright 2019 by the Isaac Lenton.
    :license: BSD, see LICENSE for details.
"""
from __future__ import unicode_literals
import pickle
import os
import sys

import pytest

from sphinx import addnodes
from sphinx.testing.fixtures import make_app, test_params   # noqa: F811;
from sphinx.testing.path import path


@pytest.fixture(scope='module')
def rootdir():
    return path(os.path.dirname(__file__)).abspath()


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_with_prefix(make_app, rootdir):
    srcdir = rootdir / 'roots' / 'test_package_prefix'
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / 'index.doctree').read_bytes())

    assert isinstance(content[4], addnodes.desc)
    assert content[4].astext() == '+package.func(x)\n\nReturns x'


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_without_prefix(make_app, rootdir):
    srcdir = rootdir / 'roots' / 'test_package_prefix'
    confdict = { 'matlab_keep_package_prefix' : False }
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / 'index.doctree').read_bytes())

    assert isinstance(content[4], addnodes.desc)
    assert content[4].astext() == 'package.func(x)\n\nReturns x'


if __name__ == '__main__':
    pytest.main([__file__])
