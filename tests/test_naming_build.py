"""Path references in a build: discovery, anchors, folders and cross-references."""

import html as html_lib
import re
from collections import Counter
from pathlib import Path
from typing import Any, cast

import pytest
from sphinx.errors import ConfigError
from sphinx.util import console
from sphinx.util.inventory import InventoryFile

from sphinxcontrib import mat_naming
from sphinxcontrib.mat_types import find_source
from sphinxcontrib.matlab import DEFAULT_EXTERNAL_NAMES

strip_escape_sequences = cast(Any, console).strip_escape_sequences

CONF = 'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "."\n'


def write_files(root, files):
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_naming"


def html(app, page="index"):
    text = (app.outdir / f"{page}.html").read_text()
    return text.split('<div class="body"')[1].split('<div class="sphinxsidebar"')[0]


def ids(text):
    return [html_lib.unescape(i) for i in re.findall(r'\bid="([^"]*)"', text)]


def object_hrefs(text):
    hrefs = (html_lib.unescape(h) for h in re.findall(r'href="#([^"]*)"', text))
    return [h for h in hrefs if h.startswith("mat-")]


def index_names(app):
    index = app.env.domaindata["mat"]["index"]
    return {
        path.relative_to(app.srcdir).as_posix(): entry
        for path, entry in ((app.srcdir.joinpath(p), e) for p, e in index.items())
    }


@pytest.mark.parametrize("confdict", [{}])
def test_discovery_uses_path_references(app):
    index = index_names(app)
    found = {
        p: (e["reference"], e["matlab_name"], e["scope"]) for p, e in index.items()
    }
    assert found == {
        "+for/nm_kw.m": ("+for/nm_kw.m", None, None),  # keyword namespace
        "+nmpkg/@NmCls/NmCls.m": ("+nmpkg/@NmCls/NmCls.m", "nmpkg.NmCls", "./"),
        "+nmpkg/@NmCls/nm_helper.m": (
            "+nmpkg/@NmCls/nm_helper.m",
            "nmpkg.NmCls.nm_helper",
            "./",
        ),
        "+nmpkg/nm_func.m": ("+nmpkg/nm_func.m", "nmpkg.nm_func", "./"),
        "@NmBox/NmBox.m": ("@NmBox/NmBox.m", "NmBox", "./"),
        "@NmBox/sub/nm_legacy.m": ("@NmBox/sub/nm_legacy.m", None, None),  # R2026a
        "alpha/nm_shared.m": ("alpha/nm_shared.m", "nm_shared", "alpha/"),
        "beta/nm_shared.m": ("beta/nm_shared.m", "nm_shared", "beta/"),
        "my folder/nm_spaced.m": ("my folder/nm_spaced.m", "nm_spaced", "my folder/"),
        "private/nm_priv.m": ("private/nm_priv.m", "nm_priv", "./"),
    }
    assert [p for p, e in index.items() if e["private"]] == ["private/nm_priv.m"]
    data = app.env.domaindata["mat"]
    assert {n: sorted(r) for n, r in data["matlab_names"].items()} == {
        "NmBox": ["@NmBox/NmBox.m"],
        "nm_priv": ["private/nm_priv.m"],
        "nm_shared": ["alpha/nm_shared.m", "beta/nm_shared.m"],
        "nm_spaced": ["my folder/nm_spaced.m"],
        "nmpkg": ["+nmpkg/"],
        "nmpkg.NmCls": ["+nmpkg/@NmCls/NmCls.m"],
        "nmpkg.nm_func": ["+nmpkg/nm_func.m"],
    }
    folders = {r for r in data["entities_table"] if r.endswith("/")}
    assert folders == {
        "./",
        "+for/",
        "+nmpkg/",
        "+nmpkg/@NmCls/",
        "@NmBox/",
        "@NmBox/sub/",
        "alpha/",
        "beta/",
        "my folder/",
        "private/",
    }


@pytest.mark.parametrize("confdict", [{}])
def test_not_callable_files_warn_once(app):
    warnings = app.warning.getvalue()
    for ref in ("+for/nm_kw.m", "@NmBox/sub/nm_legacy.m"):
        assert warnings.count(f"{ref} is not callable in MATLAB R2026a") == 1
    # private/nm_priv.m is callable from its parent folder: no warning.
    assert warnings.count("[mat.not_callable]") == 2


@pytest.mark.parametrize("confdict", [{"suppress_warnings": ["mat.not_callable"]}])
def test_not_callable_warning_can_be_suppressed(app):
    assert "not callable" not in app.warning.getvalue()


@pytest.mark.parametrize("confdict", [{}])
def test_anchors_and_signatures(app):
    text = html(app)
    anchors = [i for i in ids(text) if i.startswith("mat-")]
    assert anchors == [
        "mat-+nmpkg/nm_func.m",
        "mat-+nmpkg/@NmCls/NmCls.m",
        "mat-+nmpkg/@NmCls/NmCls.m.NmCls",
        "mat-+nmpkg/@NmCls/NmCls.m.nm_helper",
        "mat-alpha/nm_shared.m",
        "mat-beta/nm_shared.m",
        "mat-my~20folder/nm_spaced.m",
        "mat-private/nm_priv.m",
        "mat-+for/nm_kw.m",
        "mat-@NmBox/sub/nm_legacy.m",
        "mat-+nmpkg/",
        "mat-alpha/",
    ]
    assert all(n == 1 for n in Counter(ids(text)).values())
    plain = html_lib.unescape(re.sub(r"<[^>]+>", "", text))
    # MATLAB names; paths for files MATLAB cannot call; folder kinds.
    for sig in (
        "nmpkg.nm_func(x)",
        "class nmpkg.NmCls",
        "nm_priv()",
        "+for/nm_kw.m()",
        "@NmBox/sub/nm_legacy.m()",
        "namespace nmpkg",
        "folder alpha/",
    ):
        assert sig in plain


@pytest.mark.parametrize("confdict", [{}])
def test_cross_reference_resolution_order(app):
    sections = {
        chunk.split('"', 1)[0]: chunk for chunk in html(app).split('<section id="')[1:]
    }
    # Current folder alpha/ (set by "mat:folder:: alpha").
    assert object_hrefs(sections["matlab-names"]) == [
        "mat-+nmpkg/nm_func.m",
        "mat-+nmpkg/@NmCls/NmCls.m",
        "mat-+nmpkg/@NmCls/NmCls.m.nm_helper",
        "mat-my~20folder/nm_spaced.m",
        "mat-+nmpkg/nm_func.m",  # .nm_func
        "mat-+nmpkg/",
        "mat-alpha/nm_shared.m",  # relative to the current folder
    ]
    assert object_hrefs(sections["path-references"]) == [
        "mat-beta/nm_shared.m",
        "mat-private/nm_priv.m",
        "mat-+for/nm_kw.m",
        "mat-+nmpkg/@NmCls/NmCls.m.nm_helper",
        "mat-alpha/",
        "mat-my~20folder/nm_spaced.m",
    ]
    assert ">nm_spaced.m()<" in sections["path-references"]  # ~ shortens the title
    # From the root folder, its private/ files are visible by MATLAB name.
    assert object_hrefs(sections["root-folder"]) == [
        "mat-private/nm_priv.m",
        "mat-alpha/nm_shared.m",
    ]
    # Without a folder: an ambiguous name is not linked; private files are
    # reachable by path only.
    assert object_hrefs(sections["no-folder"]) == []
    warnings = app.warning.getvalue()
    assert (
        "'nm_shared' matches several objects: alpha/nm_shared.m, beta/nm_shared.m"
        in warnings
    )
    assert "reference target not found: nm_priv" in warnings
    assert "reference target not found: nm_shared" not in warnings


@pytest.mark.parametrize("confdict", [{}])
def test_inventory_uses_path_references(app):
    dom = app.env.get_domain("mat")
    for name, dispname, _, _, anchor, _ in dom.get_objects():
        assert anchor == mat_naming.make_target_id(name)
        assert dispname == dom.data["objects"][name][2]
    with open(app.outdir / "objects.inv", "rb") as f:
        inv = InventoryFile.load(cast(Any, f), "", lambda _base, uri: uri)

    def entry(objtype, name):
        item = inv[objtype][name]
        if isinstance(item, tuple):
            return item[2], item[3]
        return item.uri, item.display_name

    assert entry("mat:function", "+nmpkg/nm_func.m") == (
        "index.html#mat-+nmpkg/nm_func.m",
        "nmpkg.nm_func",
    )
    assert entry("mat:method", "+nmpkg/@NmCls/NmCls.m.nm_helper") == (
        "index.html#mat-+nmpkg/@NmCls/NmCls.m.nm_helper",
        "nmpkg.NmCls.nm_helper",
    )
    assert entry("mat:function", "my folder/nm_spaced.m") == (
        "index.html#mat-my~20folder/nm_spaced.m",
        "nm_spaced",
    )
    assert entry("mat:folder", "+nmpkg/")[1] == "nmpkg"
    assert entry("mat:folder", "alpha/")[0] == "index.html#mat-alpha/"
    assert "mat:module" not in inv


@pytest.mark.parametrize(
    ("confdict", "callable_"),
    [
        ({"matlab_version": "R2024a"}, True),
        ({"matlab_version": "R2024b"}, True),
        ({"matlab_version": "R2025a"}, True),
        ({"matlab_version": "R2025b"}, True),
        ({"matlab_version": "R2026a"}, False),
    ],
)
def test_class_subfolder_callability_follows_matlab_version(app, callable_):
    entry = index_names(app)["@NmBox/sub/nm_legacy.m"]
    assert entry["matlab_name"] == ("nm_legacy" if callable_ else None)
    assert ("nm_legacy" in app.env.domaindata["mat"]["matlab_names"]) is callable_
    warned = "@NmBox/sub/nm_legacy.m is not callable" in app.warning.getvalue()
    assert warned is not callable_


@pytest.mark.parametrize(
    ("confdict", "expected"),
    [
        ({"matlab_version": "R2024b"}, 63),
        ({"matlab_version": "R2025a"}, 2048),
        ({"matlab_version": "R2026a"}, 2048),
    ],
)
def test_namelengthmax_in_build(app, expected):
    assert mat_naming.default_namelengthmax(app.config.matlab_version) == expected


@pytest.mark.parametrize(
    ("version", "callable_"), [("R2024b", False), ("R2025a", True)]
)
def test_long_identifier_follows_release(make_app, tmp_path, version, callable_):
    name = "a" * 64
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\n'
        f'matlab_src_code_project_root = "."\nmatlab_version = "{version}"\n'
    )
    (tmp_path / "index.rst").write_text("Index\n=====\n")
    (tmp_path / f"{name}.m").write_text(f"function {name}\n% Help.\nend\n")
    app = make_app(srcdir=tmp_path)
    app.build()
    record = app.env.get_domain("mat").data["index"][str(tmp_path / f"{name}.m")]
    assert record["matlab_name"] == (name if callable_ else None)


def test_section_and_object_ids_do_not_clash(make_app, tmp_path):
    (tmp_path / "conf.py").write_text('extensions = ["sphinxcontrib.matlab"]\n')
    (tmp_path / "index.rst").write_text(
        "first\n=====\n\n.. mat:function:: first\n\n.. mat:function:: second\n"
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    assert "WARNING" not in app.warning.getvalue()
    # Hand-written objects without a source file keep their written name.
    objects = app.env.domaindata["mat"]["objects"]
    assert objects["first"] == ("index", "function", "first")
    assert {"first", "mat-first", "mat-second"} <= set(ids(html(app)))


def test_unresolved_field_types_are_text(make_app, tmp_path):
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\nnitpicky = True\n'
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n"
        ".. mat:class:: Point\n\n"
        ".. mat:function:: f(a, b)\n\n"
        "   :param a: first\n"
        "   :type a: (1,1) double\n"
        "   :param b: second\n"
        "   :type b: Point\n"
        "   :param c: missing\n"
        "   :type c: Missing\n\n"
        "See :mat:class:`Absent`.\n"
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    warnings = app.warning.getvalue()
    assert "Absent" in warnings
    assert "double" not in warnings and "Missing" not in warnings
    page = html(app)
    assert 'href="#mat-Point"' in page
    assert '<span class="pre">double</span>' in page
    assert '<span class="pre">Missing</span>' in page


EXTERNAL_PAGE = (
    "Index\n=====\n\n"
    ".. mat:class:: datetime\n\n"
    "Bases :mat:class:`handle`, :mat:class:`matlab.mixin.Copyable`,\n"
    ":mat:class:`Simulink.IntEnumType`, :mat:class:`containers.Map`,\n"
    ":mat:func:`int32`, :mat:class:`datetime`, :mat:class:`sltest.TestCase`,\n"
    ":mat:class:`Absent`, :mat:class:`handles`.\n\n"
    "Other domains are left alone: :doc:`handle`.\n"
)


def build_external(make_app, tmp_path, conf=""):
    (tmp_path / "conf.py").write_text(
        f'extensions = ["sphinxcontrib.matlab"]\nnitpicky = True\n{conf}'
    )
    (tmp_path / "index.rst").write_text(EXTERNAL_PAGE)
    app = make_app(srcdir=tmp_path)
    app.build()
    return app, strip_escape_sequences(app.warning.getvalue())


def test_matlab_names_are_text_without_a_warning(make_app, tmp_path):
    app, warnings = build_external(make_app, tmp_path)
    missing = re.findall(r"reference target not found: (\S+)", warnings)
    assert sorted(missing) == ["Absent", "handles", "sltest.TestCase"]
    assert "unknown document: 'handle'" in warnings
    page = html(app)
    assert '<span class="pre">matlab.mixin.Copyable</span>' in page
    assert "#mat-matlab" not in page
    # A documented object of that name still links.
    assert 'href="#mat-datetime"' in page


def test_matlab_external_names_is_configurable(make_app, tmp_path):
    conf = 'matlab_external_names = [r"sltest\\..+", "Absent"]\n'
    _, warnings = build_external(make_app, tmp_path, conf)
    missing = re.findall(r"reference target not found: (\S+)", warnings)
    assert sorted(missing) == [
        "Simulink.IntEnumType",
        "containers.Map",
        "handle",
        "handles",
        "int32",
        "matlab.mixin.Copyable",
    ]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ('"handle"', "matlab_external_names must be a list, not 'handle'."),
        ("[1]", "matlab_external_names: 1 must be a str."),
        ('["a("]', "matlab_external_names: 'a(' is not a regular expression"),
    ],
)
def test_matlab_external_names_errors(make_app, tmp_path, value, message):
    (tmp_path / "conf.py").write_text(
        f'extensions = ["sphinxcontrib.matlab"]\nmatlab_external_names = {value}\n'
    )
    (tmp_path / "index.rst").write_text("Index\n=====\n")
    with pytest.raises(ConfigError, match=re.escape(message)):
        make_app(srcdir=tmp_path)


def test_no_external_names(make_app, tmp_path):
    _, warnings = build_external(make_app, tmp_path, "matlab_external_names = []\n")
    missing = re.findall(r"reference target not found: (\S+)", warnings)
    assert len(missing) == 8


def test_documented_default_external_names():
    reference = Path(__file__).parents[1] / "docs" / "reference" / "configuration.rst"
    block = "".join(f'          r"{p}",\n' for p in DEFAULT_EXTERNAL_NAMES)
    assert f"      [\n{block}      ]\n" in reference.read_text(encoding="utf-8")


def test_auto_directives_without_listing_autodoc(make_app, tmp_path):
    write_files(
        tmp_path,
        {
            "f.m": "function f\n% F\nend\n",
            "g.m": "function g\n% G\nend\n",
            "conf.py": CONF,
        },
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n"
        ".. mat:autofunction:: f\n\n"
        ".. mat:autofunction:: g\n   :bogus:\n"
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    warnings = app.warning.getvalue()
    assert f"{tmp_path / 'index.rst'}:6:" in warnings
    assert "An option to mat:autofunction is either unknown" in warnings
    assert set(app.env.domaindata["mat"]["objects"]) == {"f.m"}


def test_auto_directive_resolution_order(make_app, tmp_path):
    for path, text in {
        "a/f.m": "function f\n% A f\nend\n",
        "b/f.m": "function f\n% B f\nend\n",
        "a/private/p.m": "function p\n% A private p\nend\n",
        "+pk/g.m": "function g\n% G\n%\n% See also f, b/f.m\nend\n",
    }.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text)
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "."\n'
        'matlab_auto_link = "basic"\n'
        'primary_domain = "mat"\n'
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n"
        ".. mat:autofunction:: f\n\n"  # ambiguous
        ".. mat:autofunction:: p\n\n"  # private: not by MATLAB name from elsewhere
        ".. mat:currentfolder:: a\n\n"
        ".. mat:autofunction:: p\n\n"  # a/private/p.m
        ".. mat:autofunction:: f\n\n"  # a/f.m
        ".. mat:autofunction:: b/f.m\n\n"  # exact path reference
        ".. mat:autofunction:: pk.g\n"  # MATLAB name
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    objects = app.env.domaindata["mat"]["objects"]
    assert set(objects) == {"a/private/p.m", "a/f.m", "b/f.m", "+pk/g.m"}
    warnings = app.warning.getvalue()
    assert "'f' matches several objects: a/f.m, b/f.m" in warnings
    assert "don't know which object to document for 'p'" in warnings
    # "See also" in +pk/g.m: an ambiguous MATLAB name warns and stays literal.
    assert "'f' in the docstring of +pk/g.m matches several objects" in warnings
    assert object_hrefs(html(app)).count("mat-b/f.m") == 1  # See also
    # The ambiguous name gives the "¶" link the address by path (mat_urls).
    assert 'class="headerlink" href="mat/ref/b/f.m.html"' in html(app)


def test_folder_directive_and_roles(make_app, tmp_path):
    for path, text in {
        "a/f.m": "function f\nend\n",
        "+pk/g.m": "function g\nend\n",
        "@C/C.m": "classdef C\nend\n",
    }.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text)
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "."\n'
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n"
        ".. mat:folder:: a\n   :synopsis: Tools.\n   :platform: Linux\n"
        "   :deprecated:\n\n"
        ".. mat:folder:: +pk\n\n"
        ".. mat:folder:: .\n\n"
        ".. mat:folder:: @C\n\n"
        ".. mat:function:: pk.g\n\n"
        "Links: :mat:folder:`a`, :mat:folder:`pk`, :mat:folder:`.`, "
        ":any:`pk.g`, :mat:func:`a/f.m()`.\n"
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    warnings = app.warning.getvalue()
    assert "@C/ is a class folder; document its class instead" in warnings
    assert "[mat.directive]" in warnings
    objects = app.env.domaindata["mat"]["objects"]
    assert objects["a/"] == ("index", "folder", "a/")
    assert objects["+pk/"] == ("index", "folder", "pk")
    assert objects["./"] == ("index", "folder", "./")
    assert objects["+pk/g.m"] == ("index", "function", "pk.g")
    assert "@C/" not in objects
    text = html(app)
    assert 'title="a/: Tools. (deprecated) (Linux)"' in text
    assert object_hrefs(text) == ["mat-a/", "mat-+pk/", "mat-./", "mat-+pk/g.m"]
    # "¶" links: by MATLAB name where there is one, else by path.
    assert re.findall(r'class="headerlink" href="(mat/[^"]*)"', text) == [
        "mat/ref/a/index.html",
        "mat/name/pk.html",
        "mat/ref/index.html",
        "mat/name/pk.g.html",
    ]
    # a/f.m is not documented: the role keeps its text and parentheses.
    assert "a/f.m()" in text
    assert '<span class="pre">.</span>' in text  # root folder link title
    assert app.env.domaindata["mat"]["folders"]["a/"][1:] == (
        "Tools.",
        "Linux",
        True,
    )


def test_names_ignore_folders_above_the_project_root(make_app, tmp_path):
    srcdir = tmp_path / "@work" / "+docs"
    write_files(
        srcdir,
        {
            "conf.py": CONF,
            "index.rst": "Index\n=====\n",
            "f.m": "function f\nend\n",
            "+pk/g.m": "function g\nend\n",
        },
    )
    app = make_app(srcdir=srcdir)
    app.build()
    assert "not callable" not in app.warning.getvalue()
    names = app.env.domaindata["mat"]["matlab_names"]
    assert names == {"f": ["f.m"], "pk.g": ["+pk/g.m"], "pk": ["+pk/"]}


def test_private_functions_are_visible_from_their_parent_folder(make_app, tmp_path):
    write_files(
        tmp_path,
        {
            "conf.py": CONF,
            "index.rst": "Index\n=====\n",
            "@C/C.m": "classdef C\nend\n",
            "@C/private/y.m": "function y\nend\n",
            "a/private/p.m": "function p\nend\n",
        },
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    dom = app.env.get_domain("mat")
    assert [ref for ref, _ in find_source(dom, "y", "@C/")] == ["@C/private/y.m"]
    assert find_source(dom, "y", "./") == []
    assert [ref for ref, _ in find_source(dom, "p", "a/")] == ["a/private/p.m"]
    assert find_source(dom, "p", "./") == []


def test_folder_paths_and_ambiguous_names(make_app, tmp_path):
    write_files(
        tmp_path,
        {
            "conf.py": CONF,
            "pk/h.m": "function h\nend\n",
            "+pk/g.m": "function g\nend\n",
            "a/f.m": "function f\nend\n",
            "b/f.m": "function f\nend\n",
            "a/k.m": "function k\nend\n",
            "b/k.m": "function k\nend\n",
            "a/+ns/u.m": "function u\nend\n",
            "b/+ns/v.m": "function v\nend\n",
            "index.rst": "Index\n=====\n\n"
            # A path without "/" never shadows a MATLAB name: pk is +pk/.
            ".. mat:folder:: pk/\n\n"
            ".. mat:folder:: pk\n\n"
            ".. mat:currentfolder:: ns\n\n"
            ".. mat:currentfolder:: None\n\n"
            ".. mat:function:: k\n\n"
            ".. mat:function:: a/f.m\n\n"
            ".. mat:function:: b/f.m\n\n"
            "Links: :mat:folder:`pk`, :mat:folder:`pk/`, :any:`f`.\n",
        },
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    objects = app.env.domaindata["mat"]["objects"]
    assert objects["pk/"] == ("index", "folder", "pk/")
    assert objects["+pk/"] == ("index", "folder", "pk")
    links = html(app).split("Links:")[1].split("</p>")[0]
    assert object_hrefs(links) == ["mat-+pk/", "mat-pk/"]  # :any:`f` unlinked
    warnings = app.warning.getvalue()
    assert "'ns' matches several objects: a/+ns/, b/+ns/" in warnings
    assert "'k' matches several objects: a/k.m, b/k.m" in warnings
    assert "'f' matches several objects: a/f.m, b/f.m" in warnings
    assert "more than one target found" not in warnings
