"""test_package_links.py.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import docutils
import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_duplicate_link"


@pytest.mark.parametrize(
    "confdict",
    [{"matlab_keep_package_prefix": True}, {"matlab_keep_package_prefix": False}],
)
def test_duplicate_link(app, confdict):
    content = pickle.loads((app.doctreedir / "groups.doctree").read_bytes())

    assert isinstance(content[0], docutils.nodes.section)

    elems = len(content[0])
    section = content[0][elems - 1]
    if confdict["matlab_keep_package_prefix"]:
        assert (
            section.astext()
            == "NiceFiniteGroup\n\n\n\nclass +replab.NiceFiniteGroup\n\nBases: "
            "+replab.FiniteGroup\n\nA nice finite group is a finite group equipped "
            "with an injective homomorphism into a permutation group\n\nReference that triggers the error: eqv"
        )
    else:
        assert (
            section.astext()
            == "NiceFiniteGroup\n\n\n\nclass replab.NiceFiniteGroup\n\nBases: replab.FiniteGroup\n\nA nice finite group is a finite group equipped with an injective homomorphism into a permutation group\n\nReference that triggers the error: eqv"
        )
