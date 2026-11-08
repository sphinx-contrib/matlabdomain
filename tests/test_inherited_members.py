"""test_inherited_members.

Test the ``:inherited-members:`` option for autoclass.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_inherited_members"


def test_inherited_members(app):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())
    text = content[0].astext()

    # The index documents DerivedTable twice: first without and then with the
    # :inherited-members: option. Split on the explanatory paragraph that
    # precedes the second directive to compare the two outputs.
    before, separator, after = text.partition("With inherited members")
    assert separator, "expected the second autoclass section to be present"

    # Without :inherited-members:, only members defined on DerivedTable appear.
    assert "ownMethod()" in before
    assert "derivedProp" in before
    assert "addRow(val)" not in before
    assert "baseProp" not in before

    # With :inherited-members:, members inherited from BaseTable appear
    # alongside the members defined on DerivedTable.
    assert "ownMethod()" in after
    assert "derivedProp" in after
    assert "addRow(val)" in after
    assert "baseProp" in after

    # The base class constructor must never be pulled into the documented
    # class's constructor summary.
    assert "BaseTable(x)" not in text
