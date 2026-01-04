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


@pytest.fixture
def confdict(matlab_keep_package_prefix):
    return {"matlab_keep_package_prefix": matlab_keep_package_prefix}


@pytest.mark.parametrize("matlab_keep_package_prefix", [True, False])
def test_duplicate_link(app, confdict, matlab_keep_package_prefix):
    content = pickle.loads((app.doctreedir / "groups.doctree").read_bytes())

    assert isinstance(content[0], docutils.nodes.section)

    elems = len(content[0])
    section = content[0][elems - 1]

    expected_content = (
        "NiceFiniteGroup\n\n\n\n"
        "class {}replab.NiceFiniteGroup\n\n"
        "Bases: {}replab.FiniteGroup\n\n"
        "A nice finite group is a finite group equipped "
        "with an injective homomorphism into a permutation group\n\n"
        "Reference that triggers the error: eqv"
    )

    if confdict["matlab_keep_package_prefix"]:
        assert section.astext() == expected_content.format("+", "+")
    else:
        assert section.astext() == expected_content.format("", "")
