"""Test that a member name several classes share is warned about, not linked.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest
from docutils import nodes


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_shared_member_name"


def test_shared_member_name_is_not_linked(app):
    content = pickle.loads((app.doctreedir / "groups.doctree").read_bytes())

    assert isinstance(content[0], nodes.section)

    elems = len(content[0])
    section = content[0][elems - 1]

    assert section.astext() == (
        "NiceFiniteGroup\n\n\n\n"
        "class replab.NiceFiniteGroup\n\n"
        "Bases: replab.FiniteGroup\n\n"
        "A nice finite group is a finite group equipped "
        "with an injective homomorphism into a permutation group\n\n"
        "Reference that triggers the error: eqv"
    )
    # ".eqv" matches the eqv of several classes: warned, not linked.
    assert "'eqv' matches several objects" in app.warning.getvalue()
