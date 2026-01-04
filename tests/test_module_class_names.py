"""test_class_subfolder.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_module_class_names"


@pytest.fixture
def confdict(matlab_auto_link):
    return {
        "matlab_auto_link": matlab_auto_link,
    }


@pytest.mark.parametrize("matlab_auto_link", ["basic", "all"])
def test_module_class_names(app, confdict, matlab_auto_link):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    expected_content = (
        "Myclass\n\n\n\n"
        "class Myclass\n\nMyclass\n\n"
        "See Also: YourClass\n\n"
        "Constructor Summary\n\n\n\n\n\n"
        "Myclass()\n\nThe Myclass{} constructor\n\n"
        "Property Summary\n\n\n\n\n\nprop\n\nThe property\n\n"
        "Method Summary\n\n\n\n\n\nadd(value)\n\nAdd the value\n\n"
        "YourClass\n\n\n\n"
        "class YourClass\n\nYourClass\n\n"
        "See Also: Myclass\n\n"
        "Constructor Summary\n\n\n\n\n\n"
        "YourClass()\n\nThe YourClass{} constructor\n\n"
        "Property Summary\n\n\n\n\n\nprop\n\nThe property\n\n"
        "Method Summary\n\n\n\n\n\nadd(value)\n\nAdd the value\n\n\n\n\n\n\n\n"
        "class MyOtherClass\n\n"
        "myothertest\n\n"
        "Property Summary\n\n\n\n\n\notherprop\n\nprop\n\n"
        "Method Summary\n\n\n\n\n\notherf()\n\nfunction"
    )

    if confdict["matlab_auto_link"] == "basic":
        assert content.astext() == expected_content.format("", "")

    elif confdict["matlab_auto_link"] == "all":
        assert content.astext() == expected_content.format("()", "()")
