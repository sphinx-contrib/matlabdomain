"""test_autodoc.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_autodoc"


@pytest.fixture
def confdict(show_default, show_specs):
    return {
        "matlab_show_property_default_value": show_default,
        "matlab_show_property_specs": show_specs,
    }


# We test the combination of
# - matlab_show_property_default_value
# - matlab_show_property_specs
@pytest.mark.parametrize("show_default", [True, False])
@pytest.mark.parametrize("show_specs", [True, False])
def test_target(app, show_default, show_specs):
    content = pickle.loads((app.doctreedir / "index_target.doctree").read_bytes())

    assert len(content) == 1

    summaries = content[0][2][1][4].rawsource

    if show_default:
        assert "= 42\n\n" in summaries

    if show_specs:
        assert "(1,:) {mustBeScalarOrEmpty}" in summaries
