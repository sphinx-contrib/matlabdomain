"""test_class_subfolder.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import helper
import pytest


@pytest.fixture
def srcdir():
    return helper.rootdir(__file__) / "roots" / "test_module_class_names"


@pytest.mark.parametrize(
    "confdict",
    [{"matlab_auto_link": "basic"}, {"matlab_auto_link": "all"}],
)
def test_module_class_names(app, confdict):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    if confdict["matlab_auto_link"] == "basic":
        assert content.astext() == (
            "Myclass\n\n\n\nclass Myclass\n\nMyclass\n\n"
            "See Also: YourClass\n\nConstructor Summary\n\n\n\n\n\n"
            "Myclass()\n\nThe Myclass constructor\n\n"
            "Property Summary\n\n\n\n\n\nprop\n\nThe property\n\n"
            "Method Summary\n\n\n\n\n\nadd(value)\n\nAdd the value\n\n"
            "YourClass\n\n\n\nclass YourClass\n\nYourClass\n\n"
            "See Also: Myclass\n\nConstructor Summary\n\n\n\n\n\n"
            "YourClass()\n\nThe YourClass constructor\n\n"
            "Property Summary\n\n\n\n\n\nprop\n\nThe property\n\n"
            "Method Summary\n\n\n\n\n\nadd(value)\n\n"
            "Add the value\n\n\n\n\n\n\n\nclass MyOtherClass\n\n"
            "myothertest\n\nProperty Summary\n\n\n\n\n\n"
            "otherprop\n\nprop\n\nMethod Summary\n\n\n\n\n\n"
            "otherf()\n\nfunction"
        )

    elif confdict["matlab_auto_link"] == "all":
        assert content.astext() == (
            "Myclass\n\n\n\nclass Myclass\n\nMyclass\n\n"
            "See Also: YourClass\n\nConstructor Summary\n\n\n\n\n\n"
            "Myclass()\n\nThe Myclass() constructor\n\n"
            "Property Summary\n\n\n\n\n\nprop\n\nThe property\n\n"
            "Method Summary\n\n\n\n\n\nadd(value)\n\nAdd the value\n\n"
            "YourClass\n\n\n\nclass YourClass\n\nYourClass\n\n"
            "See Also: Myclass\n\nConstructor Summary\n\n\n\n\n\n"
            "YourClass()\n\nThe YourClass() constructor\n\n"
            "Property Summary\n\n\n\n\n\nprop\n\nThe property\n\n"
            "Method Summary\n\n\n\n\n\nadd(value)\n\n"
            "Add the value\n\n\n\n\n\n\n\nclass MyOtherClass"
            "\n\nmyothertest\n\nProperty Summary\n\n\n\n\n\n"
            "otherprop\n\nprop\n\nMethod Summary\n\n\n\n\n\n"
            "otherf()\n\nfunction"
        )
