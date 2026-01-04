"""test_class_subfolder.
~~~~~~~~~~~~

Test the autodoc extension.

:copyright: Copyright 2007-2018 by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import pickle

import helper
import pytest


@pytest.fixture(scope="module")
def rootdir():
    return helper.rootdir(__file__)


def test_index(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_module_class_names"
    app = make_app(srcdir=srcdir)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())
    assert (
        content.astext()
        == "Myclass\n\n\n\nclass Myclass\n\nMyclass\n\nSee Also: YourClass\n\nConstructor Summary\n\n\n\n\n\nMyclass()\n\nThe Myclass constructor\n\nProperty Summary\n\n\n\n\n\nprop\n\nThe property\n\nMethod Summary\n\n\n\n\n\nadd(value)\n\nAdd the value\n\nYourClass\n\n\n\nclass YourClass\n\nYourClass\n\nSee Also: Myclass\n\nConstructor Summary\n\n\n\n\n\nYourClass()\n\nThe YourClass constructor\n\nProperty Summary\n\n\n\n\n\nprop\n\nThe property\n\nMethod Summary\n\n\n\n\n\nadd(value)\n\nAdd the value"
        + "\n\n\n\n\n\n\n\nclass MyOtherClass\n\nmyothertest\n\nProperty Summary\n\n\n\n\n\notherprop\n\nprop\n\nMethod Summary\n\n\n\n\n\notherf()\n\nfunction"
    )


def test_index_auto_link_all(make_app, rootdir):
    srcdir = rootdir / "roots" / "test_module_class_names"
    confdict = {"matlab_auto_link": "all"}
    app = make_app(srcdir=srcdir, confoverrides=confdict)
    app.builder.build_all()

    content = pickle.loads((app.doctreedir / "index.doctree").read_bytes())
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


if __name__ == "__main__":
    pytest.main([__file__])
