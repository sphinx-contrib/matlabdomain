"""Test the autodoc extension with the matlab_keep_package_prefix option.

:copyright: Copyright by the Isaac Lenton.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest
from sphinx import addnodes


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_package_prefix"


@pytest.fixture
def confdict(matlab_keep_package_prefix):
    return {"matlab_keep_package_prefix": matlab_keep_package_prefix}


@pytest.mark.parametrize("matlab_keep_package_prefix", [True, False])
def test_package_prefix(app, confdict):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    assert isinstance(content[4], addnodes.desc)
    if confdict["matlab_keep_package_prefix"]:
        assert content[4].astext() == "+package.func(x)\n\nReturns x"
    else:
        assert content[4].astext() == "package.func(x)\n\nReturns x"
