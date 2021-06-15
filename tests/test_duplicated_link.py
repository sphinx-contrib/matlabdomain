# -*- coding: utf-8 -*-
"""
    test_package_links.py
    ~~~~~~~~~~~~

    Test the autodoc extension.

    :copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import unicode_literals
import pickle
import os
import sys
import docutils

import pytest

from sphinx import addnodes
from sphinx import version_info
from sphinx.testing.fixtures import test_params, make_app
from sphinx.testing.path import path


@pytest.fixture(scope='module')
def rootdir():
    return path(os.path.dirname(__file__)).abspath()


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_with_prefix(make_app, rootdir):
    srcdir = rootdir / 'roots' / 'test_duplicate_link'
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / 'groups.doctree').read_bytes())

    assert isinstance(content[0], docutils.nodes.section)
    section = content[0][7]
    assert section.astext() == 'NiceFiniteGroup\n\n\n\nclass +replab.NiceFiniteGroup\n\nBases: +replab.FiniteGroup\n\nA nice finite group is a finite group equipped with an injective homomorphism into a permutation group\n\nReference that triggers the error: eqv'    


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_without_prefix(make_app, rootdir):
    srcdir = rootdir / 'roots' / 'test_duplicate_link'    
    confdict = { 'matlab_keep_package_prefix' : False }
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / 'groups.doctree').read_bytes())

    assert isinstance(content[0], docutils.nodes.section)
    section = content[0][7]
    assert section.astext() == 'NiceFiniteGroup\n\n\n\nclass replab.NiceFiniteGroup\n\nBases: replab.FiniteGroup\n\nA nice finite group is a finite group equipped with an injective homomorphism into a permutation group\n\nReference that triggers the error: eqv'    


if __name__ == '__main__':
    pytest.main([__file__])