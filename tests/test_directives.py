"""Hand-written directives and roles of the mat domain."""

import re

import pytest
from sphinx import addnodes

from sphinxcontrib.matlab import MATLABFolderIndex

CONF = 'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "."\n'

PAGE = """\
Index
=====

.. _mat-x:

A label with the anchor of ``x``.

.. mat:function:: x

.. mat:function:: f

.. mat:function:: opt(a, [b, [c]])

.. mat:function:: opt2(a[, b])

.. mat:function:: empty([, a])

.. mat:function:: unbalanced(a, ]b)

.. mat:function:: unclosed([a)

.. mat:function:: ret() -> out

.. mat:function:: ret2(a) -> out
   :annotation: = 3

.. mat:data:: CONST
   :annotation: = 42

.. mat:class:: Shape

   .. mat:attribute:: Area

.. mat:method:: lonely()

.. mat:folder:: +pkg

.. mat:folder:: +pkg

.. mat:folder:: nothere

Links: :mat:obj:`f()`, :mat:obj:`()`, :mat:attr:`~Shape.m.Area`.
"""


def build(make_app, tmp_path, page=PAGE, conf=CONF, **kwargs):
    files = {
        "conf.py": conf,
        "index.rst": page,
        "f.m": "function f\n% F\nend\n",
        "Shape.m": "classdef Shape\n% Shape\nproperties\nArea\nend\nend\n",
        "+pkg/g.m": "function g\n% G\nend\n",
    }
    for path, text in files.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text)
    app = make_app(srcdir=tmp_path, **kwargs)
    app.build()
    return app


@pytest.fixture
def built(make_app, tmp_path):
    return build(make_app, tmp_path)


def signature(app, ref):
    doctree = app.env.get_doctree("index")
    (node,) = (
        n for n in doctree.findall(addnodes.desc_signature) if f"mat-{ref}" in n["ids"]
    )
    return node


def texts(node, cls):
    return [n.astext() for n in node.findall(cls)]


def test_optional_arguments(built):
    assert len(texts(signature(built, "opt"), addnodes.desc_optional)) == 2
    assert len(texts(signature(built, "opt2"), addnodes.desc_optional)) == 1
    assert texts(signature(built, "empty"), addnodes.desc_parameter) == ["a"]
    # Unbalanced brackets: the argument list is shown as one parameter.
    assert texts(signature(built, "unbalanced"), addnodes.desc_parameter) == ["a, ]b"]
    assert texts(signature(built, "unclosed"), addnodes.desc_parameter) == ["[a"]


def test_return_annotation_and_annotation(built):
    assert texts(signature(built, "ret"), addnodes.desc_returns) == [" -> out"]
    ret2 = signature(built, "ret2")
    assert texts(ret2, addnodes.desc_returns) == [" -> out"]
    assert texts(ret2, addnodes.desc_annotation) == [" = 3"]
    assert texts(signature(built, "CONST"), addnodes.desc_annotation) == [" = 42"]


def test_index_entries(built):
    entries = {e[1] for e in built.env.get_domain("index").entries["index"]}
    assert {
        "CONST (data in ./)",
        "lonely()",
        "Shape (class in ./)",
        "Area (Shape attribute)",
    } <= entries


def test_object_and_label_share_an_anchor(built):
    assert "share the target id 'mat-x'; x is not linkable" in built.warning.getvalue()


def test_folders(built):
    assert signature(built, "+pkg/").astext() == "namespace pkg"
    assert signature(built, "nothere/").astext() == "folder nothere/"
    dom = built.env.get_domain("mat")
    assert set(dom.data["folders"]) == {"+pkg/", "nothere/"}
    content, _ = MATLABFolderIndex(dom).generate(docnames=["other"])
    assert content == []
    dom.clear_doc("index")
    assert dom.data["folders"] == {}


def test_roles(built):
    html = (built.outdir / "index.html").read_text(encoding="utf-8")
    link = r'href="#(mat-[^"]+)"[^>]*><code[^>]*><span class="pre">([^<]*)<'
    links = dict(re.findall(link, html))
    assert links["mat-f.m"] == "f()"
    assert links["mat-Shape.m.Area"] == "Area"
    assert '<span class="pre">()</span>' in html


def test_root_folder_without_a_project_root(make_app, tmp_path):
    page = "Index\n=====\n\n.. mat:folder:: .\n"
    app = build(make_app, tmp_path, page, 'extensions = ["sphinxcontrib.matlab"]\n')
    assert signature(app, "./").astext() == "folder ./"


def test_add_namespace_names(make_app, tmp_path):
    page = "Index\n=====\n\n.. mat:function:: pkg.g\n"
    app = build(
        make_app, tmp_path, page, confoverrides={"matlab_add_namespace_names": False}
    )
    sig = signature(app, "+pkg/g.m")
    assert texts(sig, addnodes.desc_addname) == []
    assert sig.astext() == "g()"


def test_add_module_names_is_not_read(make_app, tmp_path):
    page = "Index\n=====\n\n.. mat:function:: pkg.g\n"
    app = build(make_app, tmp_path, page, confoverrides={"add_module_names": False})
    assert signature(app, "+pkg/g.m").astext() == "pkg.g()"


def test_static_method_prefix(make_app, tmp_path):
    page = "Index\n=====\n\n.. mat:class:: Shape\n\n   .. mat:staticmethod:: make()\n"
    app = build(make_app, tmp_path, page)
    assert signature(app, "Shape.m.make").astext() == "static make()"


def test_attribute_flags(make_app, tmp_path):
    page = (
        "Index\n=====\n\n.. mat:class:: Shape\n   :sealed:\n   :abstract:\n\n"
        "   .. mat:staticmethod:: make()\n      :sealed:\n      :abstract:\n\n"
        "   .. mat:attribute:: Area\n      :read-only:\n      :dependent:\n"
        "      :constant:\n      :abstract:\n"
    )
    app = build(make_app, tmp_path, page)
    assert app.warning.getvalue() == ""
    assert signature(app, "Shape.m").astext() == "abstract sealed class Shape"
    assert signature(app, "Shape.m.make").astext() == "abstract sealed static make()"
    assert (
        signature(app, "Shape.m.Area").astext()
        == "abstract constant dependent read-only Area"
    )


def test_classmethod_directive_is_removed(make_app, tmp_path):
    page = "Index\n=====\n\n.. mat:class:: Shape\n\n   .. mat:classmethod:: create()\n"
    app = build(make_app, tmp_path, page)
    assert "classmethod" not in app.env.get_domain("mat").object_types
    assert 'Unknown directive type "mat:classmethod"' in app.warning.getvalue()
