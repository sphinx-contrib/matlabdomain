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
    return rootdir / "roots" / "test_numad"


def test_first(app):
    content = pickle.loads((app.doctreedir / "index_first.doctree").read_bytes())

    assert content.astext() == (
        "First Class\n\n\n\n"
        "class target.FirstClass\n\n"
        "First class with two properties\n\n"
        "Property Summary\n\n\n\n\n\n"
        "a\n\n"
        "The a property\n\n\n\n"
        "b\n\n"
        "The b property\n\n\n\n"
        "FirstClass.a\n\n"
        "The a property\n\n\n\n"
        "FirstClass.b\n\nThe b property"
    )


def test_second(app):
    content = pickle.loads((app.doctreedir / "index_second.doctree").read_bytes())

    assert content.astext() == (
        "Second Class\n\n\n\n"
        "class target.SecondClass\n\n"
        "Second class with methods and properties\n\n"
        "Constructor Summary\n\n\n\n\n\n"
        "SecondClass(a)\n\n"
        "The second class constructor\n\n"
        "Property Summary\n\n\n\n\n\n"
        "a\n\n"
        "The a property\n\n\n\n"
        "b\n\n"
        "The b property\n\n"
        "Method Summary\n\n\n\n\n\n"
        "first_method(b)\n\n"
    )
