from __future__ import print_function
import pytest
import sphinx
import sphinxcontrib.matlab as mat
from sphinx.testing.fixtures import test_params, make_app
from sphinx.testing.path import path
import sys
import os



def test_setup(make_app):
    rootdir = path(os.path.dirname(__file__))
    srcdir= rootdir / 'test_docs'
    app = make_app('dummy', srcdir=srcdir)
    mat.setup(app)


if __name__ == '__main__':
    pytest.main([__file__])

