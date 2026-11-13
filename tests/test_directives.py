"""Hand-written directives and roles of the mat domain."""

import os
import re
import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from sphinx import addnodes
from sphinx.util import console

from sphinxcontrib.matlab import MATLABFolderIndex

strip_escape_sequences = cast(Any, console).strip_escape_sequences

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


# --- where the warnings of directives point --------------------------------------

SLX = Path(__file__).parent / "simulink" / "fixtures" / "R2026b" / "slx"
# (directive, what it warns): each directive warns once, at the place it is
# written; a duplicate at the directive a person wrote in a reST or Markdown
# file (``AUTO``: the outermost auto directive of help text).
WARNING_DIRECTIVES = [
    (".. mat:function:: dup", "mat.ambiguous"),
    (".. mat:function:: g", "mat.duplicate"),
    (".. mat:currentfolder:: ns", "mat.ambiguous"),
    (".. mat:folder:: ns", "mat.ambiguous"),
    (".. mat:folder:: @K", "mat.directive"),
    (".. mat:currentfolder:: None", None),
    (".. mat:autofunction:: nosuch", "mat.not_found"),
    (".. mat:autofunction:: dup", "mat.ambiguous"),
    (".. mat:autofunction:: h", "mat.duplicate"),
    (".. mat:autofunction:: one\n   :members: [", "option"),
    (".. mat:autosimulink_model:: probeModel\n   :metadata: bogus", "mat.simulink"),
    (".. mat:autosimulink_library:: probeLib\n   :members: Nosuch", "mat.not_found"),
]
DIRECTIVES = "\n\n".join(directive for directive, _ in WARNING_DIRECTIVES) + "\n"
FUNCTION = "function y = {0}(x)\n% {0} help\ny = x;\nend\n"
PLACES = {
    # on the page
    "page": {"p.rst": "P\n=\n\n" + DIRECTIVES},
    # on the page, below an included file
    "below_include": {
        "p.rst": "P\n=\n\n.. include:: pad.txt\n\n" + DIRECTIVES,
        "pad.txt": "".join(f"Padding {i}.\n\n" for i in range(10)),
    },
    # in an included file
    "included": {
        "p.rst": "P\n=\n\nText.\n\nMore.\n\n.. include:: inc.txt\n",
        "inc.txt": "Included.\n\n" + DIRECTIVES,
    },
    # in a sidecar doc
    "sidecar": {
        "p.rst": "P\n=\n\nText.\n\nMore.\n\n.. mat:autosidecar:: guide.rst\n",
        "src/guide.rst": "Guide\n=====\n\nText.\n\n" + DIRECTIVES,
    },
    # in the help text of a file an auto directive documents
    "help": {
        "p.rst": "P\n=\n\nText.\n\n.. mat:autofunction:: f\n",
        "src/f.m": "function y = f(x)\n% F help\n%\n"
        + "".join(f"% {line}\n" if line else "%\n" for line in DIRECTIVES.split("\n"))
        + "y = x;\nend\n",
    },
    # in a sidecar doc that help text renders
    "sidecar_in_help": {
        "p.rst": "P\n=\n\nText.\n\n.. mat:autofunction:: f\n",
        "src/f.m": "function y = f(x)\n% F help\n%\n"
        "% .. mat:autosidecar:: guide.rst\ny = x;\nend\n",
        "src/guide.rst": "Guide\n=====\n\nText.\n\n" + DIRECTIVES,
    },
}
LOCATION_SOURCES = {
    "conf.py": 'extensions = ["sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "src"\n'
    'matlab_src_sidecar_suffixes = [".rst"]\n'
    'exclude_patterns = ["inc.txt", "pad.txt", "_build"]\n',
    "index.rst": "Index\n=====\n\n.. toctree::\n\n   a\n   p\n",
    # sorts before p: p's descriptions of g and h are the duplicates
    "a.rst": "A\n=\n\n.. mat:function:: g\n\n.. mat:autofunction:: h\n",
    "src/a/dup.m": FUNCTION.format("dup"),
    "src/b/dup.m": FUNCTION.format("dup"),
    "src/a/+ns/x.m": FUNCTION.format("x"),
    "src/b/+ns/y.m": FUNCTION.format("y"),
    "src/@K/K.m": "classdef K\n% K help\nend\n",
    "src/one.m": FUNCTION.format("one"),
    "src/h.m": FUNCTION.format("h"),
}
WARNING_LINE = re.compile(r"^(.*):(\d+): (?:WARNING|ERROR): (.*?)(?: \[(\S+)\])?$")


def located_warnings(app, root):
    """``{(file relative to root, line, kind)}`` of the warnings of ``app``."""
    found = set()
    text = strip_escape_sequences(app.warning.getvalue())
    for line in text.splitlines():
        match = WARNING_LINE.match(line)
        assert match is not None, line
        where, number, message, kind = match.groups()
        if kind is None and "An option to" in message:
            kind = "option"
        rel = os.path.relpath(where.partition(":docstring of ")[0], root)
        if ":docstring of " in where:
            rel += ":docstring of " + where.partition(":docstring of ")[2]
        found.add((rel.replace(os.sep, "/"), int(number), kind))
    return found


def expected_warnings(file, text, outer=None, source=None):
    """Return the warnings of ``WARNING_DIRECTIVES`` written in ``text`` of
    ``file``; ``outer`` is (file, line) of the outermost auto directive for
    help text, whose warnings are at ``source``.
    """
    lines = text.split("\n")
    expected = set()
    for directive, kind in WARNING_DIRECTIVES:
        if kind is None:
            continue
        first = directive.split("\n")[0]
        (line,) = [i for i, t in enumerate(lines, 1) if t.lstrip("% ") == first]
        if kind == "mat.duplicate" and outer is not None:
            expected.add((*outer, kind))
        else:
            expected.add((source or file, line, kind))
    return expected


def build_place(make_app, root, files, conf=""):
    sources = {**LOCATION_SOURCES, **files}
    sources["conf.py"] += conf
    for path, text in sources.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    (root / "src").mkdir(exist_ok=True)
    for name in ("probeModel", "probeLib"):
        shutil.copyfile(SLX / f"{name}.slx", root / "src" / f"{name}.slx")
    app = make_app(srcdir=root, freshenv=True)
    app.build()
    return app


@pytest.mark.parametrize("place", list(PLACES))
def test_directive_warnings_name_the_place_of_the_directive(make_app, tmp_path, place):
    files = PLACES[place]
    app = build_place(make_app, tmp_path, files)
    if place == "help":
        text = files["src/f.m"]
        expected = expected_warnings(
            "src/f.m",
            text,
            outer=("p.rst", 6),
            source="src/f.m:docstring of f.m",
        )
    else:
        file = {
            "included": "inc.txt",
            "sidecar": "src/guide.rst",
            "sidecar_in_help": "src/guide.rst",
        }.get(place, "p.rst")
        expected = expected_warnings(file, files[file])
    assert located_warnings(app, tmp_path) == expected


MARKDOWN_GUIDE = """\
# Guide

Text.

```{mat:function} dup
```

```{mat:function} g
```

```{mat:currentfolder} ns
```

```{mat:folder} @K
```

```{mat:currentfolder} None
```

```{eval-rst}
.. mat:autofunction:: nosuch

.. mat:autofunction:: h
```
"""


def test_directive_warnings_in_a_markdown_sidecar_doc(make_app, tmp_path):
    pytest.importorskip("myst_parser")
    files = {
        "p.rst": "P\n=\n\nText.\n\nMore.\n\n.. mat:autosidecar:: guide.md\n",
        "src/guide.md": MARKDOWN_GUIDE,
    }
    app = build_place(
        make_app,
        tmp_path,
        files,
        'extensions = ["sphinxcontrib.matlab", "myst_parser"]\n'
        'matlab_src_sidecar_suffixes = [".rst", ".md"]\n',
    )
    lines = MARKDOWN_GUIDE.split("\n")

    def at(text):
        return lines.index(text) + 1

    assert located_warnings(app, tmp_path) == {
        ("src/guide.md", at("```{mat:function} dup"), "mat.ambiguous"),
        ("src/guide.md", at("```{mat:function} g"), "mat.duplicate"),
        ("src/guide.md", at("```{mat:currentfolder} ns"), "mat.ambiguous"),
        ("src/guide.md", at("```{mat:folder} @K"), "mat.directive"),
        # auto directives write reST: in an eval-rst block
        ("src/guide.md", at(".. mat:autofunction:: nosuch"), "mat.not_found"),
        ("src/guide.md", at(".. mat:autofunction:: h"), "mat.duplicate"),
    }
