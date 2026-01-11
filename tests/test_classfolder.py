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
    return rootdir / "roots" / "test_classfolder"


def test_first(app):
    content = pickle.loads((app.doctreedir / "index_first.doctree").read_bytes())

    assert content[0].astext() == (
        "First\n\n\n\n"
        "class First\n\n"
        "The first class\n\n"
        "Constructor Summary\n\n\n\n\n\n"
        "First(a)\n\n"
        "Constructor for First\n\n"
        "Property Summary\n\n\n\n\n\n"
        "a\n\n"
        "The property\n\n"
        "Method Summary\n\n\n\n\n\n"
        "method_in_folder(varargin)\n\n"
        "A method defined in the folder\n\n\n\n"
        "method_inside_classdef(b)\n\n"
        "Method inside class definition"
    )


def test_second(app):
    content = pickle.loads((app.doctreedir / "index_second.doctree").read_bytes())

    assert content[0].astext() == (
        "Second\n\n\n\n"
        "class Second\n\n"
        "The second class\n\n"
        "Constructor Summary\n\n\n\n\n\n"
        "Second(b)\n\n"
        "Constructor for Second\n\n"
        "Property Summary\n\n\n\n\n\n"
        "b\n\n"
        "a property of a class folder\n\n"
        "Method Summary\n\n\n\n\n\n"
        "method_in_folder(varargin)\n\n"
        "A method defined in the folder\n\n\n\n"
        "method_inside_classdef(c)\n\n"
        "Method inside class definition"
    )


def test_third(app):
    content = pickle.loads((app.doctreedir / "index_third.doctree").read_bytes())

    assert content[0].astext() == (
        "Third\n\n\n\n"
        "class Third\n\n"
        "The third class\n\n"
        "Constructor Summary\n\n\n\n\n\n"
        "Third(c)\n\n"
        "Constructor for Third\n\n"
        "Property Summary\n\n\n\n\n\n"
        "c\n\n"
        "a property of a class folder\n\n"
        "Method Summary\n\n\n\n\n\n"
        "method_in_folder(varargin)\n\n"
        "A method defined in the folder\n\n\n\n"
        "method_inside_classdef(d)\n\n"
        "Method inside class definition"
    )
