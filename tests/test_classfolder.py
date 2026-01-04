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
    assert (
        content[0].astext()
        == "First\n\n\n\nclass First\n\nThe first class\n\nConstructor Summary\n\n\n\n\n\nFirst(a)\n\nConstructor for First\n\nProperty Summary\n\n\n\n\n\na\n\nThe property\n\nMethod Summary\n\n\n\n\n\nmethod_in_folder(varargin)\n\nA method defined in the folder\n\n\n\nmethod_inside_classdef(b)\n\nMethod inside class definition"
    )


def test_second(app):
    content = pickle.loads((app.doctreedir / "index_second.doctree").read_bytes())
    assert (
        content[0].astext()
        == "Second\n\n\n\nclass Second\n\nThe second class\n\nConstructor Summary\n\n\n\n\n\nSecond(b)\n\nConstructor for Second\n\nProperty Summary\n\n\n\n\n\nb\n\na property of a class folder\n\nMethod Summary\n\n\n\n\n\nmethod_in_folder(varargin)\n\nA method defined in the folder\n\n\n\nmethod_inside_classdef(c)\n\nMethod inside class definition"
    )


def test_third(app):
    content = pickle.loads((app.doctreedir / "index_third.doctree").read_bytes())
    assert (
        content[0].astext()
        == "Third\n\n\n\nclass Third\n\nThe third class\n\nConstructor Summary\n\n\n\n\n\nThird(c)\n\nConstructor for Third\n\nProperty Summary\n\n\n\n\n\nc\n\na property of a class folder\n\nMethod Summary\n\n\n\n\n\nmethod_in_folder(varargin)\n\nA method defined in the folder\n\n\n\nmethod_inside_classdef(d)\n\nMethod inside class definition"
    )
