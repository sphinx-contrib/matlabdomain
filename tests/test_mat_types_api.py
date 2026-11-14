"""mat_types lookups: detached use, references, getters, member order, apps."""

import sys
import zipfile

import pytest

from sphinxcontrib import mat_handlers, mat_types
from sphinxcontrib.mat_types import (
    MatcodeError,
    MatEnumeration,
    MatFunction,
    MatModule,
    MatModuleAnalyzer,
    MatObject,
    MatProperty,
    MatScript,
    find_source,
    lookup_reference,
    resolve,
    source_scope,
)

CONF = 'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "."\n'

FILES = {
    "f.m": "function y = f(x)\n% F HELP\ny = x;\nend\n",
    "s.m": "% S HELP\nx = 1;\n",
    "Shape.m": (
        "classdef Shape < handle\n% SHAPE HELP\nproperties\nArea % the area\nend\n"
        "methods\nfunction a = area(obj)\n% AREA HELP\nend\nend\nend\n"
    ),
    "Color.m": (
        "classdef Color\n% COLOR HELP\nenumeration\nRed % the red\nGreen\nend\nend\n"
    ),
    "sub/g.m": "function g\n% G HELP\nend\n",
    "_build/h.m": "function h\nend\n",
    "_build/doctrees/environment.pickle": b"",
    ".git/i.m": "function i\nend\n",
    "notes.txt": "not MATLAB\n",
}


def write(root, files):
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            content = content.encode("utf-8")
        target.write_bytes(content)


@pytest.fixture
def detached(monkeypatch, tmp_path):
    """No Sphinx build: lookups list and parse files on every call."""
    write(tmp_path, FILES)
    monkeypatch.setattr(MatObject, "sphinx_env", None)
    monkeypatch.setattr(MatObject, "basedir", str(tmp_path))
    return tmp_path


@pytest.fixture
def built(make_app, tmp_path):
    write(tmp_path, {**FILES, "conf.py": CONF, "index.rst": "Index\n=====\n"})
    app = make_app(srcdir=tmp_path)
    app.build()
    return app


def test_detached_lookups_parse_on_demand(detached):
    root = MatObject.matlabify("")
    assert isinstance(root, MatModule)
    assert root.ref == "./"
    assert sorted(root.member_refs()) == [
        ("Color", "Color.m"),
        ("Shape", "Shape.m"),
        ("f", "f.m"),
        ("s", "s.m"),
        ("sub", "sub/"),
    ]
    f = MatObject.matlabify("f")
    assert isinstance(f, MatFunction)
    assert (f.ref, f.docstring) == ("f.m", "F HELP")
    assert MatObject.matlabify("sub").getter("g").docstring == "G HELP"
    for missing in ("_build", ".git", "missing", "notes.txt"):
        assert MatObject.matlabify(missing) is None
    assert MatObject.matlabify(None) is None
    # Without an index nothing is found by name, and bases stay unresolved.
    assert find_source(mat_types._domain(), "f.m") == []
    assert MatObject.matlabify("Shape").getter("__bases__") == {"handle": None}
    gone = MatModule("gone", str(detached / "gone"), "gone/")
    assert gone.member_refs() == []


def test_handler_without_an_object_gives_a_placeholder(detached, monkeypatch):
    class NoObject(mat_handlers.Handler):
        extension = ".xyz"

        def classify(self, path, text=None):
            return "unknown"

        def parse(self, path, stem, folder, encoding=None):
            return None

    monkeypatch.setitem(mat_handlers._HANDLERS, ".xyz", NoObject())
    (detached / "data.xyz").write_text("x")
    obj = MatObject.matlabify("data.xyz")
    assert isinstance(obj, MatScript)
    assert (obj.ref, obj.docstring, obj.source_type) == ("data.xyz", None, "unknown")


def test_lookup_reference(built):
    dom = built.env.get_domain("mat")
    assert isinstance(lookup_reference(dom, "Shape.m.Area"), MatProperty)
    red = lookup_reference(dom, "Color.m.Red")
    assert isinstance(red, MatEnumeration)
    assert (red.__doc__, red.__module__, red.ref_role()) == ("the red", "./", "enum")
    for reference in ("Shape", "nothere.m.x", "f.m.x", "Shape.m.Area.x"):
        assert lookup_reference(dom, reference) is None


def test_source_scope_of_undiscovered_references(built):
    dom = built.env.get_domain("mat")
    assert source_scope(dom, "f.m") == "./"
    assert source_scope(dom, "gone/") == "gone/"
    assert source_scope(dom, "lib/gone.m") == "lib/"


def test_getter_names_and_defaults(built):
    dom = built.env.get_domain("mat")
    for ref in ("f.m", "s.m", "Shape.m"):
        obj = resolve(dom, ref)
        assert obj.getter("__name__") == obj.name
        assert obj.getter("nothing") is None
        assert obj.getter("nothing", 7) == 7


def test_reference_roles(built):
    dom = built.env.get_domain("mat")
    roles = {}
    for ref in ("f.m", "s.m", "Shape.m", "Shape.m.Area", "Shape.m.area"):
        obj = lookup_reference(dom, ref)
        assert obj is not None
        roles[ref] = obj.ref_role()
    assert roles == {
        "f.m": "func",
        "s.m": "ref",
        "Shape.m": "class",
        "Shape.m.Area": "attr",
        "Shape.m.area": "meth",
    }
    assert resolve(dom, "sub/").ref_role() == "folder"


def test_module_analyzer_gives_source_order(built):
    analyzer = MatModuleAnalyzer.for_module("./")
    assert MatModuleAnalyzer.for_module("./") is analyzer
    assert analyzer.srcname == str(built.srcdir)
    order = analyzer.tagorder
    assert order.get("Shape") == order.order["Shape"]
    assert (order.get("Shape.Area"), order.get("Shape.area")) == (0, 1)
    assert order.get("Shape.nothing", -1) == -1
    assert order.get("f.x", -1) == -1  # not a class
    assert order.get("sub", -1) == -1
    assert len(order) == sys.maxsize
    for _ in range(2):  # the failure is cached
        with pytest.raises(MatcodeError, match="error importing 'gone/'"):
            MatModuleAnalyzer.for_module("gone/")


def mlapp(path, core, meta):
    ns = {
        "core": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
        "dc": "http://purl.org/dc/elements/1.1/",
        "app": "http://schemas.mathworks.com/appDesigner/app/2017/appMetadata",
    }
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "metadata/coreProperties.xml",
            f'<cp:coreProperties xmlns:cp="{ns["core"]}" xmlns:dc="{ns["dc"]}">'
            f"{core}</cp:coreProperties>",
        )
        z.writestr(
            "metadata/appMetadata.xml",
            f'<n:AppMetadata xmlns:n="{ns["app"]}">{meta}</n:AppMetadata>',
        )


@pytest.mark.parametrize(
    ("core", "meta", "docstring"),
    [
        (
            "<dc:description>CORE</dc:description>",
            "<n:description>META</n:description>",
            "CORE\n\nMETA",
        ),
        ("", "<n:description/>", ""),
    ],
    ids=["both", "none"],
)
def test_app_descriptions(tmp_path, core, meta, docstring):
    mlapp(tmp_path / "App.mlapp", core, meta)
    app = MatObject.parse_mlappfile(str(tmp_path / "App.mlapp"), "App", "./")
    assert app.docstring == docstring
