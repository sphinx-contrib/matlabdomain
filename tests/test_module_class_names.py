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
def app(make_app, matlab_auto_link):
    srcdir = helper.rootdir(__file__) / "roots" / "test_module_class_names"
    confdict = {"matlab_auto_link": matlab_auto_link}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()
    return app


@pytest.mark.parametrize("matlab_auto_link", ["basic", "all"])
def test_index_matlab_auto_link(app, matlab_auto_link):
    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())

    if matlab_auto_link == "basic":
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

    elif matlab_auto_link == "all":
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
