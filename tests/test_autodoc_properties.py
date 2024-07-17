# -*- coding: utf-8 -*-
"""
    test_autodoc
    ~~~~~~~~~~~~

    Test the autodoc extension.

    :copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import pickle
import sys
import helper

import pytest

from sphinx import addnodes
from sphinx.testing.fixtures import make_app, test_params  # noqa: F811;


@pytest.fixture(scope="module")
def rootdir():
    return helper.rootdir(__file__)


# We test the combination of
# - matlab_show_property_default_value
# - matlab_show_property_specs
testdata = [(False, False), (False, True), (True, False), (True, True)]


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
@pytest.mark.parametrize("show_default,show_specs", testdata)
def test_target(make_app, rootdir, show_default, show_specs):
    srcdir = rootdir / "roots" / "test_autodoc"
    confdict = {
        "matlab_show_property_default_value": show_default,
        "matlab_show_property_specs": show_specs,
    }
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())
    summaries = content[0][2][1][4].rawsource

    assert len(content) == 1

    if show_default:
        assert "= 42\n\n" in summaries

    if show_specs:
        assert "(1,:) {mustBeScalarOrEmpty}" in summaries


if __name__ == "__main__":
    pytest.main([__file__])
