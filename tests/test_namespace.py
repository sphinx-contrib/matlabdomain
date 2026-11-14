"""The namespace object: ``mat:namespace``, ``mat:autonamespace`` and the
``:mat:namespace:`` role; ``+`` folders shown as folders; the current
namespace; the namespace on ``scmd apidoc`` pages.
"""

import html as html_lib
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, cast

import pytest
from sphinx import addnodes
from sphinx.util import console
from sphinx.util.inventory import InventoryFile
from test_apidoc import FUNCTION, write
from test_incremental_equals_clean import differences, snapshot
from test_intersphinx import BASE, build_consumer, build_library, inventory

from sphinxcontrib.matlab_apidoc import main as apidoc

strip_escape_sequences = cast(Any, console).strip_escape_sequences

CONF = 'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "src"\n'
SHAPE = """\
classdef Shape < handle
    % Shape A shape of the namespace.
    properties
        Side = 1 % Length of a side.
    end
    methods
        function z = zeta(obj)
            % zeta Comes first in the file.
            z = obj.Side;
        end
        function a = alpha(obj)
            % alpha Comes second in the file.
            a = obj.Side;
        end
        function bare(obj)
        end
    end
end
"""
POLY = "classdef Poly\n    % Poly A class in a class folder.\nend\n"
POLY_AREA = "function a = area(obj)\n% area Area of the polygon.\na = 0;\nend\n"
SOURCES = {
    # the namespace ns has two folders, x/+ns/ and y/+ns/
    "src/x/+ns/f.m": FUNCTION.format(name="f"),
    "src/x/+ns/undoc.m": "function undoc()\nend\n",
    "src/x/+ns/Shape.m": SHAPE,
    "src/x/+ns/Contents.m": "% NS The ns toolbox.\n%   f - A function.\n",
    "src/x/+ns/private/p.m": FUNCTION.format(name="p"),
    "src/x/+ns/+sub/s.m": FUNCTION.format(name="s"),
    "src/x/+ns/@Poly/Poly.m": POLY,
    "src/x/+ns/@Poly/area.m": POLY_AREA,
    "src/y/+ns/g.m": FUNCTION.format(name="g"),
    "src/y/+ns/run_me.m": "% run_me A script of the namespace.\ndisp(1)\n",
    # the namespace solo has one folder
    "src/one/+solo/h.m": FUNCTION.format(name="h"),
    "src/plain/k.m": FUNCTION.format(name="k"),
}
TITLE = "Index\n=====\n\n"


def project(root, pages, conf="", sources=None):
    """Write the sources (``SOURCES`` and ``sources``), ``conf.py`` and the
    pages (``index`` is a page body below a title; others are whole files).
    """
    files = {**SOURCES, **(sources or {})}
    files["conf.py"] = CONF + conf
    for name, text in pages.items():
        files[f"{name}.rst"] = TITLE + text if name == "index" else text
    write(root, files)


def build(make_app, root, pages, conf="", sources=None, **kwargs):
    project(root, pages, conf, sources)
    app = make_app(srcdir=root, **kwargs)
    app.build()
    return app


def warnings(app):
    return strip_escape_sequences(app.warning.getvalue()).replace(
        str(app.srcdir) + os.sep, ""
    )


def body(app, page="index"):
    text = (Path(app.outdir) / f"{page}.html").read_text(encoding="utf-8")
    return text.split('<div class="body"')[1].split('<div class="sphinxsidebar"')[0]


def plain(text):
    return html_lib.unescape(re.sub(r"<[^>]+>", "", text))


def hrefs(text):
    return [html_lib.unescape(h) for h in re.findall(r'href="([^"]*mat-[^"]*)"', text)]


def signatures(app, page="index"):
    """``(anchor, text)`` of each object description on ``page``, in order."""
    doctree = app.env.get_doctree(page)
    return [
        (sig["ids"][0] if sig["ids"] else None, sig.astext())
        for sig in doctree.findall(addnodes.desc_signature)
    ]


def files_documented(app, page="index"):
    """Return the anchors of the namespace and the files on ``page``, in order
    (members of classes left out).
    """
    return [
        anchor
        for anchor, _ in signatures(app, page)
        if anchor and not re.search(r"\.m\.\w+$", anchor)
    ]


def objects(app):
    return app.env.domaindata["mat"]["objects"]


# --- the object, its links and its entries --------------------------------------


def test_namespace_directive_describes_one_object(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        {"index": ".. mat:namespace:: ns\n   :synopsis: The ns tools.\n\n   Text.\n"},
    )
    assert warnings(app) == ""
    assert objects(app) == {"+ns": ("index", "namespace", "ns")}
    assert app.env.domaindata["mat"]["folders"] == {
        "+ns": ("index", "The ns tools.", "", False)
    }
    assert signatures(app) == [("mat-+ns", "namespace ns")]
    assert "Text." in plain(body(app))
    entries = app.env.get_domain("index").entries["index"]
    assert ("single", "ns (namespace)", "mat-+ns", "", None) in entries


def test_autonamespace_describes_the_namespace_without_help_text(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        {"index": ".. mat:autonamespace:: ns\n   :platform: Linux\n\n   Added.\n"},
    )
    assert warnings(app) == ""
    assert objects(app) == {"+ns": ("index", "namespace", "ns")}
    assert app.env.domaindata["mat"]["folders"]["+ns"] == ("index", "", "Linux", False)
    assert signatures(app) == [("mat-+ns", "namespace ns")]
    # No help of its own (Contents.m is not read); the content is kept.
    # As for a folder, the content follows the description.
    content = app.env.get_doctree("index").next_node(addnodes.desc_content)
    assert content.astext() == ""
    assert "Added." in plain(body(app))


def test_role_links_to_the_namespace_from_another_page(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        {
            "index": ".. toctree::\n\n   a\n   b\n",
            "a": "A\n=\n\n.. mat:namespace:: ns\n   :synopsis: The ns tools.\n",
            "b": "B\n=\n\nLinks: :mat:namespace:`ns`, :mat:namespace:`~ns`, "
            ":mat:namespace:`+ns`, :mat:obj:`ns`, :any:`ns`.\n",
        },
        conf="nitpicky = True\n",
    )
    assert warnings(app) == ""
    links = body(app, "b").split("Links:")[1]
    assert hrefs(links) == ["a.html#mat-+ns"] * 5
    assert 'title="ns: The ns tools."' in links


def test_inventory_entry_and_stable_address(make_app, tmp_path):
    app = build(make_app, tmp_path, {"index": ".. mat:autonamespace:: ns\n"})
    out = Path(app.outdir)
    entry = inventory(out)["+ns"]
    assert entry == ("mat/ref/%2Bns.html", "ns")
    assert "+ns" in {name for name, *_ in app.env.get_domain("mat").get_objects()}
    redirect = (out / "mat/ref/+ns.html").read_text(encoding="utf-8")
    assert 'url=../../index.html#mat-+ns"' in redirect
    by_name = (out / "mat/name/ns.html").read_text(encoding="utf-8")
    assert 'url=../../index.html#mat-+ns"' in by_name
    # the "¶" link: the address by MATLAB name
    assert 'class="headerlink" href="mat/name/ns.html"' in body(app)
    # the general index
    genindex = plain((out / "genindex.html").read_text(encoding="utf-8"))
    assert "ns (namespace)" in genindex


def test_inventory_without_stable_addresses(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        {"index": ".. mat:namespace:: ns\n"},
        conf="matlab_stable_urls = False\n",
    )
    assert inventory(Path(app.outdir))["+ns"] == ("index.html#mat-+ns", "ns")


def test_namespace_reference_never_names_a_file(make_app, tmp_path):
    # The namespace a.m (+a/+m/) next to the file a.m: two objects, two
    # anchors, inventory entries and addresses.
    sources = {
        "src/a.m": FUNCTION.format(name="a"),
        "src/+a/+m/q.m": FUNCTION.format(name="q"),
    }
    page = (
        ".. mat:autofunction:: a.m\n\n"
        ".. mat:autonamespace:: a.m\n   :members:\n\n"
        "Links: :mat:namespace:`a.m`, :mat:obj:`a.m`, :mat:obj:`+a/+m`, "
        ":mat:func:`a`.\n"
    )
    app = build(make_app, tmp_path, {"index": page}, sources=sources)
    assert warnings(app) == ""
    assert objects(app) == {
        "a.m": ("index", "function", "a"),
        "+a/+m": ("index", "namespace", "a.m"),
        "+a/+m/q.m": ("index", "function", "a.m.q"),
    }
    out = Path(app.outdir)
    inv = inventory(out)
    assert inv["a.m"] == ("mat/ref/a.m.html", "a")
    assert inv["+a/+m"] == ("mat/ref/%2Ba/%2Bm.html", "a.m")
    assert (out / "mat/ref/a.m.html").is_file()
    assert (out / "mat/ref/+a/+m.html").is_file()
    assert 'url=../../index.html#mat-+a/+m"' in (out / "mat/name/a.m.html").read_text(
        encoding="utf-8"
    )
    links = body(app).split("Links:")[1]
    # a.m is a path reference before it is a MATLAB name
    assert hrefs(links) == ["#mat-+a/+m", "#mat-a.m", "#mat-+a/+m", "#mat-a.m"]


def test_folder_index_lists_the_namespace(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        {
            "index": ".. mat:namespace:: ns\n   :synopsis: The ns tools.\n"
            "   :deprecated:\n\n.. mat:folder:: x/+ns/\n"
        },
    )
    index = (Path(app.outdir) / "mat-folderindex.html").read_text(encoding="utf-8")
    assert re.search(
        r'<a href="index.html#mat-\+ns"><code class="xref">ns</code></a></td>'
        r"<td><strong>Deprecated:</strong>\s*<em>The ns tools.</em>",
        index,
    )
    assert '<code class="xref">x/+ns/</code>' in index


@pytest.mark.parametrize("parallel", [0, 2], ids=["serial", "parallel"])
def test_described_on_two_pages_without_a_duplicate_warning(
    make_app, tmp_path, parallel
):
    others = {f"c{i}": f"C{i}\n==\n\nText.\n" for i in range(1, 6)}
    toctree = "".join(f"   {d}\n" for d in ["a", "b", *others])
    app = build(
        make_app,
        tmp_path,
        {
            "index": f"See :mat:namespace:`ns`.\n\n.. toctree::\n\n{toctree}",
            "a": "A\n=\n\n.. mat:autonamespace:: ns\n",
            "b": "B\n=\n\n.. mat:namespace:: ns\n",
            **others,
        },
        parallel=parallel,
    )
    assert warnings(app) == ""
    assert objects(app)["+ns"] == ("b", "namespace", "ns")
    assert hrefs(body(app)) == ["b.html#mat-+ns"]


def test_incremental_build_moves_the_link_target(make_app, tmp_path):
    pages = {
        "index": "See :mat:namespace:`ns`.\n\n.. toctree::\n\n   a\n   b\n",
        "a": "A\n=\n\n.. mat:namespace:: ns\n",
        "b": "B\n=\n\n.. mat:namespace:: ns\n",
    }
    build(make_app, tmp_path / "inc", pages)
    (tmp_path / "inc" / "b.rst").write_text("B\n=\n\nNothing.\n", encoding="utf-8")
    later = time.time_ns() + 2_000_000_000
    os.utime(tmp_path / "inc" / "b.rst", ns=(later, later))
    app = make_app(srcdir=tmp_path / "inc")
    app.build()
    assert list(app.env.get_domain("mat").read_docnames) == ["b"]
    fresh = build(make_app, tmp_path / "fresh", {**pages, "b": "B\n=\n\nNothing.\n"})
    for name in ("objects", "folders"):
        assert app.env.domaindata["mat"][name] == fresh.env.domaindata["mat"][name]
    assert objects(app)["+ns"] == ("a", "namespace", "ns")
    assert "[mat." not in warnings(app)
    assert 'href="a.html#mat-+ns"' in body(app)


# --- members -----------------------------------------------------------------


def test_members_of_a_namespace_in_one_folder(make_app, tmp_path):
    app = build(
        make_app, tmp_path, {"index": ".. mat:autonamespace:: solo\n   :members:\n"}
    )
    assert warnings(app) == ""
    assert files_documented(app) == ["mat-+solo", "mat-one/+solo/h.m"]
    assert ("mat-one/+solo/h.m", "solo.h()") in signatures(app)


def test_members_of_all_folders_sorted_by_name(make_app, tmp_path):
    app = build(
        make_app, tmp_path, {"index": ".. mat:autonamespace:: ns\n   :members:\n"}
    )
    assert warnings(app) == ""
    # Sorted by name as in a folder; not private/, +sub/, Contents.m or the
    # undocumented undoc.m.
    assert files_documented(app) == [
        "mat-+ns",
        "mat-x/+ns/@Poly/Poly.m",
        "mat-x/+ns/Shape.m",
        "mat-x/+ns/f.m",
        "mat-y/+ns/g.m",
        "mat-y/+ns/run_me.m",
    ]
    found = objects(app)
    assert found["y/+ns/run_me.m"] == ("index", "script", "ns.run_me")
    # the class of the class folder, with the method in its own file
    assert found["x/+ns/@Poly/Poly.m"] == ("index", "class", "ns.Poly")
    assert found["x/+ns/@Poly/Poly.m.area"] == ("index", "method", "ns.Poly.area")
    # the options apply to the classes too: their documented members
    assert "x/+ns/Shape.m.zeta" in found
    assert "x/+ns/Shape.m.bare" not in found
    for left_out in ("private/p.m", "+sub/s.m", "Contents.m", "undoc.m"):
        assert f"x/+ns/{left_out}" not in found


def test_named_members_in_the_order_given(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        {"index": ".. mat:autonamespace:: ns\n   :members: g, Poly, nosuch\n"},
    )
    assert files_documented(app) == [
        "mat-+ns",
        "mat-y/+ns/g.m",
        "mat-x/+ns/@Poly/Poly.m",
    ]
    assert warnings(app) == (
        "index.rst:4: WARNING: [sphinxcontrib-matlabdomain] missing attribute "
        "mentioned in :members:: namespace ns, attribute nosuch [mat.not_found]\n"
    )


def test_special_files_only_when_named(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        {"index": ".. mat:autonamespace:: ns\n   :members: Contents\n"},
    )
    assert "x/+ns/Contents.m" in objects(app)


def test_options_reach_the_members(make_app, tmp_path):
    page = (
        ".. mat:autonamespace:: ns\n"
        "   :members:\n"
        "   :undoc-members:\n"
        "   :show-inheritance:\n"
        "   :exclude-members: f, run_me\n"
        "   :member-order: bysource\n"
    )
    app = build(make_app, tmp_path, {"index": page})
    assert warnings(app) == ""
    found = objects(app)
    assert "x/+ns/undoc.m" in found
    assert "x/+ns/Shape.m.bare" in found
    assert "x/+ns/f.m" not in found
    assert "y/+ns/run_me.m" not in found
    text = plain(body(app))
    assert "Bases: handle" in text
    # source order of the class members: zeta is above alpha in Shape.m
    anchors = [a for a, _ in signatures(app)]
    assert anchors.index("mat-x/+ns/Shape.m.zeta") < anchors.index(
        "mat-x/+ns/Shape.m.alpha"
    )


def test_default_options_as_for_a_folder(make_app, tmp_path):
    conf = 'autodoc_default_options = {"members": True, "undoc-members": True}\n'
    app = build(
        make_app,
        tmp_path,
        {"index": ".. mat:autonamespace:: ns\n\n.. mat:autofolder:: one/+solo/\n"},
        conf=conf,
    )
    found = objects(app)
    assert "x/+ns/undoc.m" in found
    assert "one/+solo/h.m" in found


def test_same_member_name_in_two_folders(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        {"index": ".. mat:autonamespace:: ns\n   :members: f\n"},
        sources={"src/y/+ns/f.m": FUNCTION.format(name="f")},
    )
    # Both are documented, by reference, as on the scmd apidoc page.
    assert files_documented(app) == ["mat-+ns", "mat-x/+ns/f.m", "mat-y/+ns/f.m"]
    assert warnings(app) == (
        "index.rst:4: WARNING: [sphinxcontrib-matlabdomain] 'ns.f' matches several "
        "objects: x/+ns/f.m, y/+ns/f.m; each is documented; link to one by its "
        "path reference [mat.ambiguous]\n"
    )


# --- arguments that are no namespace --------------------------------------------


@pytest.mark.parametrize("directive", ["namespace", "autonamespace"])
@pytest.mark.parametrize(
    "argument",
    ["nosuch", "plain", "plain/", "ns.Shape", "x/+ns/", "+ns", "ns.f", "one/+solo"],
)
def test_argument_that_is_no_namespace(make_app, tmp_path, directive, argument):
    app = build(make_app, tmp_path, {"index": f".. mat:{directive}:: {argument}\n"})
    assert warnings(app) == (
        f"index.rst:4: WARNING: [sphinxcontrib-matlabdomain] {argument!r} is not a "
        "namespace of the project; write the MATLAB name of a namespace (a.b for "
        "+a/+b/) [mat.not_found]\n"
    )
    assert objects(app) == {}


def test_arguments_or_return_annotation(make_app, tmp_path):
    app = build(make_app, tmp_path, {"index": ".. mat:autonamespace:: solo(a) -> b\n"})
    assert warnings(app) == (
        "index.rst:4: WARNING: [sphinxcontrib-matlabdomain] signature arguments or "
        "return annotation given for autonamespace solo [mat.directive]\n"
    )
    assert signatures(app) == [("mat-+solo", "namespace solo")]


# --- folders stay folders ---------------------------------------------------------


def inventory_entries(app):
    """``{(type, name): (uri, display)}`` of the mat entries of ``objects.inv``,
    read with Sphinx's loader.
    """
    with open(Path(app.outdir) / "objects.inv", "rb") as f:
        inv = InventoryFile.load(cast(Any, f), "", lambda _base, uri: uri)
    return {
        (objtype, name): (item[2], item[3])
        if isinstance(item, tuple)
        else (item.uri, item.display_name)
        for objtype, items in inv.items()
        if objtype.startswith("mat:")
        for name, item in items.items()
    }


def headerlinks(app, page="index"):
    """``{anchor: href}`` of the "¶" links of the object descriptions."""
    return dict(
        re.findall(
            r'<dt class="sig[^"]*" id="([^"]*)">.*?class="headerlink" href="([^"]*)"',
            (Path(app.outdir) / f"{page}.html").read_text(encoding="utf-8"),
            re.DOTALL,
        )
    )


def stable_target(app, stub):
    """Return where the stable address ``stub`` redirects to, or None for a
    chooser page.
    """
    text = (Path(app.outdir) / stub).read_text(encoding="utf-8")
    found = re.search(r'url=([^"]*)"', text)
    return html_lib.unescape(found[1]) if found else None


def chooser_refs(app, stub):
    text = (Path(app.outdir) / stub).read_text(encoding="utf-8")
    return re.findall(r'<span class="pre">([^<]*)</span></code></a> \((\w+)\)', text)


FOLDER_DIRECTIVES = ["folder", "autofolder"]


@pytest.mark.parametrize("directive", FOLDER_DIRECTIVES)
def test_only_folder_of_a_namespace_is_shown_by_its_name(make_app, tmp_path, directive):
    app = build(make_app, tmp_path, {"index": f".. mat:{directive}:: one/+solo/\n"})
    assert warnings(app) == ""
    assert signatures(app) == [("mat-one/+solo/", "namespace solo")]
    assert objects(app) == {"one/+solo/": ("index", "folder", "solo")}
    entries = {e[1] for e in app.env.get_domain("index").entries["index"]}
    assert entries == {"solo (namespace)"}
    assert inventory_entries(app) == {
        ("mat:folder", "one/+solo/"): ("mat/ref/one/%2Bsolo/index.html", "solo")
    }
    assert headerlinks(app) == {"mat-one/+solo/": "mat/name/solo.html"}
    assert stable_target(app, "mat/name/solo.html") == "../../index.html#mat-one/+solo/"


@pytest.mark.parametrize("directive", FOLDER_DIRECTIVES)
def test_folders_of_a_namespace_of_several_folders_are_shown_by_path(
    make_app, tmp_path, directive
):
    page = f".. mat:{directive}:: x/+ns/\n\n.. mat:{directive}:: y/+ns/\n"
    app = build(make_app, tmp_path, {"index": page})
    assert warnings(app) == ""
    assert signatures(app) == [
        ("mat-x/+ns/", "folder x/+ns/"),
        ("mat-y/+ns/", "folder y/+ns/"),
    ]
    assert objects(app) == {
        "x/+ns/": ("index", "folder", "x/+ns/"),
        "y/+ns/": ("index", "folder", "y/+ns/"),
    }
    entries = {e[1] for e in app.env.get_domain("index").entries["index"]}
    assert entries == {"x/+ns/ (folder)", "y/+ns/ (folder)"}
    # the display of a plain folder, and the chooser entry of the name
    assert inventory_entries(app) == {
        ("mat:folder", "x/+ns/"): ("mat/ref/x/%2Bns/index.html", "-"),
        ("mat:folder", "y/+ns/"): ("mat/ref/y/%2Bns/index.html", "-"),
        ("mat:folder", "ns"): ("mat/name/ns.html", "-"),
    }
    assert headerlinks(app) == {
        "mat-x/+ns/": "mat/ref/x/%2Bns/index.html",
        "mat-y/+ns/": "mat/ref/y/%2Bns/index.html",
    }
    assert stable_target(app, "mat/name/ns.html") is None
    assert chooser_refs(app, "mat/name/ns.html") == [
        ("x/+ns/", "folder"),
        ("y/+ns/", "folder"),
    ]


def test_display_counts_the_indexed_folders(make_app, tmp_path):
    # y/+ns/ is not described: x/+ns/ is still one of two folders.
    app = build(make_app, tmp_path, {"index": ".. mat:folder:: x/+ns/\n"})
    assert signatures(app) == [("mat-x/+ns/", "folder x/+ns/")]
    # the only described object of the name ns: a redirect, not a chooser
    assert stable_target(app, "mat/name/ns.html") == "../../index.html#mat-x/+ns/"


@pytest.mark.parametrize("chooser", [False, True])
def test_role_to_a_name_of_several_folders(make_app, tmp_path, chooser):
    page = (
        ".. mat:folder:: x/+ns/\n\n.. mat:folder:: y/+ns/\n\nLink: :mat:folder:`ns`.\n"
    )
    conf = f"matlab_link_shadowed_files_to_chooser_pages = {chooser}\n"
    app = build(make_app, tmp_path, {"index": page}, conf=conf)
    link = body(app).split("Link:")[1].split("</p>")[0]
    if chooser:
        assert warnings(app) == ""
        assert 'href="mat/name/ns.html"' in link
    else:
        assert warnings(app) == (
            "index.rst:8: WARNING: [sphinxcontrib-matlabdomain] 'ns' matches "
            "several objects: x/+ns/, y/+ns/; use a path reference for one "
            "folder, or mat:namespace, mat:autonamespace or :mat:namespace: for "
            "the whole namespace [mat.ambiguous]\n"
        )
        assert "href" not in link


def test_namespace_object_and_its_only_folder(make_app, tmp_path):
    page = (
        ".. mat:folder:: one/+solo/\n\n"
        ".. mat:namespace:: solo\n\n"
        "Links: :mat:folder:`solo`, :mat:namespace:`solo`, :mat:obj:`solo`, "
        ":any:`solo`.\n"
    )
    app = build(make_app, tmp_path, {"index": page})
    assert warnings(app) == ""
    assert objects(app)["one/+solo/"] == ("index", "folder", "solo")
    assert hrefs(body(app).split("Links:")[1]) == [
        "#mat-one/+solo/",
        "#mat-+solo",
        "#mat-+solo",
        "#mat-+solo",
    ]
    # the name is the namespace's; the folder keeps its address by path
    assert stable_target(app, "mat/name/solo.html") == "../../index.html#mat-+solo"
    assert headerlinks(app) == {
        "mat-one/+solo/": "mat/ref/one/%2Bsolo/index.html",
        "mat-+solo": "mat/name/solo.html",
    }
    assert inventory_entries(app) == {
        ("mat:folder", "one/+solo/"): ("mat/ref/one/%2Bsolo/index.html", "solo"),
        ("mat:namespace", "+solo"): ("mat/ref/%2Bsolo.html", "solo"),
    }


def test_namespace_object_and_its_several_folders(make_app, tmp_path):
    page = (
        ".. mat:folder:: x/+ns/\n\n.. mat:folder:: y/+ns/\n\n"
        ".. mat:namespace:: ns\n\n"
        "Links: :mat:namespace:`ns`, :mat:obj:`ns`, :any:`ns`.\n\n"
        "Folder: :mat:folder:`ns`.\n"
    )
    app = build(make_app, tmp_path, {"index": page})
    text = body(app)
    assert hrefs(text.split("Links:")[1].split("Folder:")[0]) == ["#mat-+ns"] * 3
    assert stable_target(app, "mat/name/ns.html") == "../../index.html#mat-+ns"
    assert ("mat:folder", "ns") not in inventory_entries(app)
    # the folder role prefers folders: the two are ambiguous, the namespace
    # object is not among them
    assert warnings(app) == (
        "index.rst:12: WARNING: [sphinxcontrib-matlabdomain] 'ns' matches "
        "several objects: x/+ns/, y/+ns/; use a path reference for one "
        "folder, or mat:namespace, mat:autonamespace or :mat:namespace: for "
        "the whole namespace [mat.ambiguous]\n"
    )


def _set_up_second_folder(root, present):
    second = root / "src" / "y" / "+solo"
    if present:
        write(root, {"src/y/+solo/z.m": FUNCTION.format(name="z")})
    elif second.exists():
        shutil.rmtree(second)


SECOND_FOLDER_PAGES = {
    "index": ".. toctree::\n\n   a\n   b\n",
    "a": "A\n=\n\n.. mat:autofolder:: one/+solo/\n   :members:\n",
    "b": "B\n=\n\nLink: :mat:folder:`one/+solo/`.\n",
}


@pytest.mark.parametrize("added", [True, False], ids=["added", "removed"])
def test_second_folder_incremental_equals_clean(make_app, tmp_path, added):
    root = tmp_path / "inc"
    project(root, SECOND_FOLDER_PAGES)
    _set_up_second_folder(root, not added)
    make_app(srcdir=root).build()
    _set_up_second_folder(root, added)
    app = make_app(srcdir=root)
    app.build()
    app.cleanup()
    shown = "folder one/+solo/" if added else "namespace solo"
    assert shown in [text for _, text in signatures(app, "a")]
    fresh_root = tmp_path / "fresh"
    project(fresh_root, SECOND_FOLDER_PAGES)
    _set_up_second_folder(fresh_root, added)
    fresh = make_app(srcdir=fresh_root)
    fresh.build()
    fresh.cleanup()
    assert differences(snapshot(Path(app.outdir)), snapshot(Path(fresh.outdir))) == []


def test_namespace_name_of_one_folder_names_the_folder(make_app, tmp_path):
    page = (
        ".. mat:folder:: solo\n\n"
        ".. mat:autofolder:: solo\n\n"
        ".. mat:currentfolder:: solo\n\n"
        ".. mat:autofunction:: h.m\n\n"
        "Links: :mat:folder:`solo`, :mat:namespace:`solo`.\n"
    )
    app = build(make_app, tmp_path, {"index": page}, conf="nitpicky = True\n")
    assert warnings(app) == ""
    assert set(objects(app)) == {"one/+solo/", "one/+solo/h.m"}
    # no namespace described: the role accepts the folder
    assert hrefs(body(app).split("Links:")[1]) == ["#mat-one/+solo/"] * 2


def test_namespace_name_of_several_folders_is_ambiguous(make_app, tmp_path):
    page = (
        ".. mat:folder:: x/+ns/\n\n"
        ".. mat:folder:: y/+ns/\n\n"
        ".. mat:folder:: ns\n\n"
        ".. mat:autofolder:: ns\n\n"
        ".. mat:currentfolder:: ns\n\n"
        "Link: :mat:folder:`ns`.\n"
    )
    app = build(make_app, tmp_path, {"index": page})
    hint = (
        "'ns' matches several objects: x/+ns/, y/+ns/; use a path reference for "
        "one folder, or mat:namespace, mat:autonamespace or :mat:namespace: for "
        "the whole namespace [mat.ambiguous]"
    )
    lines = warnings(app).splitlines()
    assert lines == [
        f"index.rst:{line}: WARNING: [sphinxcontrib-matlabdomain] {hint}"
        for line in (8, 10, 12, 14)
    ]


def test_role_types_with_a_namespace_and_its_folder(make_app, tmp_path):
    page = (
        ".. mat:folder:: one/+solo/\n\n"
        ".. mat:namespace:: solo\n\n"
        "Links: :mat:namespace:`solo`, :mat:folder:`solo`, :mat:obj:`solo`.\n"
    )
    app = build(make_app, tmp_path, {"index": page})
    assert warnings(app) == ""
    assert hrefs(body(app).split("Links:")[1]) == [
        "#mat-+solo",
        "#mat-one/+solo/",
        "#mat-+solo",
    ]


# --- the current namespace ------------------------------------------------------


def test_current_namespace_of_one_folder(make_app, tmp_path):
    page = (
        ".. mat:namespace:: solo\n\n"
        "   In it: :mat:func:`h`.\n\n"
        "After it: :mat:func:`h`.\n\n"
        ".. mat:autofunction:: h\n\n"
        ".. mat:currentfolder:: None\n\n"
        "Cleared: :mat:func:`h`.\n"
    )
    app = build(make_app, tmp_path, {"index": page}, conf="nitpicky = True\n")
    assert "one/+solo/h.m" in objects(app)
    text = body(app)
    assert hrefs(text.split("In it:")[1].split("After it:")[0]) == [
        "#mat-one/+solo/h.m"
    ]
    assert hrefs(text.split("After it:")[1].split("</p>")[0]) == ["#mat-one/+solo/h.m"]
    assert hrefs(text.split("Cleared:")[1]) == []
    assert warnings(app) == (
        "index.rst:14: WARNING: mat:func reference target not found: h [ref.func]\n"
    )


def test_current_namespace_of_two_folders(make_app, tmp_path):
    page = (
        ".. mat:autonamespace:: ns\n\n"
        "   In it: :mat:func:`g`.\n\n"
        ".. mat:autofunction:: g\n\n"
        ".. mat:autofunction:: f\n\n"
        ".. mat:class:: Shape\n   :noindex:\n\n"
        ".. mat:function:: mex_only(x)\n\n"
        "Links: :mat:func:`f`.\n\n"
        ".. mat:currentfolder:: plain/\n\n"
        ".. mat:autofunction:: g\n"
    )
    app = build(make_app, tmp_path, {"index": page})
    found = objects(app)
    assert {"y/+ns/g.m", "x/+ns/f.m"} <= set(found)
    text = body(app)
    assert hrefs(text.split("In it:")[1].split("</p>")[0]) == ["#mat-y/+ns/g.m"]
    # a hand-written description names the file in the namespace; one
    # without a file keeps its name, as without a current folder
    assert (None, "class ns.Shape") in signatures(app)
    assert found["mex_only"] == ("index", "function", "mex_only")
    links = text.split("Links:")[1].split("</p>")[0]
    assert hrefs(links) == ["#mat-x/+ns/f.m"]
    assert warnings(app) == (
        "index.rst:21: WARNING: [sphinxcontrib-matlabdomain] don't know which "
        "object to document for 'g' (use a path reference, a MATLAB name, or a "
        '"mat:currentfolder" directive) [mat.not_found]\n'
    )


# --- scmd apidoc ------------------------------------------------------------------

API_SOURCES = {
    "a/+ns/f.m": FUNCTION.format(name="f"),
    "b/+ns/g.m": FUNCTION.format(name="g"),
    "b/+ns/+deep/d.m": FUNCTION.format(name="d"),
    "top.m": FUNCTION.format(name="top"),
}


def apidoc_project(root, conf=""):
    write(root / "src", API_SOURCES)
    (root / "conf.py").write_text(
        f"{CONF}matlab_apidoc_output_dir = 'api'\nnitpicky = True\n{conf}"
    )
    (root / "index.rst").write_text(
        f"{TITLE}Links: :mat:namespace:`ns`, :mat:namespace:`ns.deep`.\n\n"
        ".. toctree::\n\n   api/index\n"
    )
    assert apidoc(["-q", "-c", str(root)]) == 0
    return {
        p.name: p.read_text(encoding="utf-8")
        for p in (root / "api").glob("*")
        if p.is_file()
    }


def test_apidoc_namespace_page_describes_the_namespace(tmp_path):
    pages = apidoc_project(tmp_path)
    assert pages["ns.rst"].startswith(
        ".. Generated by scmd apidoc.\n\nnamespace ns\n============\n\n"
        ".. mat:namespace:: ns\n\n.. contents::\n"
    )
    # the members stay one directive each
    assert ".. mat:autofunction:: a/+ns/f.m\n" in pages["ns.rst"]
    assert ".. mat:autofunction:: b/+ns/g.m\n" in pages["ns.rst"]
    assert ".. mat:namespace:: ns.deep\n" in pages["ns.deep.rst"]
    assert "mat:namespace" not in pages["global.rst"]


def test_apidoc_namespace_on_its_first_page_only(tmp_path):
    pages = apidoc_project(tmp_path, "matlab_apidoc_page_size = 1\n")
    assert ".. mat:namespace:: ns\n" in pages["ns.rst"]
    assert "mat:namespace" not in pages["ns-2.rst"]


@pytest.mark.parametrize("separate", [False, True])
def test_apidoc_pages_are_the_link_target(make_app, tmp_path, separate):
    apidoc_project(tmp_path, f"matlab_apidoc_separate = {separate}\n")
    app = make_app(srcdir=tmp_path, warningiserror=True)
    app.build()
    assert warnings(app) == ""
    assert hrefs(body(app).split("Links:")[1]) == [
        "api/ns.html#mat-+ns",
        "api/ns.deep.html#mat-+ns/+deep",
    ]


def test_intersphinx_links_to_the_namespace_by_name(make_app, tmp_path):
    outdir = build_library(make_app, tmp_path / "lib", group="namespace")
    mapping = {"lib": (BASE, str(outdir / "objects.inv"))}
    references = {
        "name": ":mat:namespace:`geom`",
        "ref": ":mat:namespace:`+geom/+io`",
        "any": ":mat:obj:`geom.io`",
    }
    links, found = build_consumer(make_app, tmp_path / "app", mapping, references)
    assert links == {
        "name": (f"{BASE}mat/ref/%2Bgeom.html", "geom"),
        "ref": (f"{BASE}mat/ref/%2Bgeom/%2Bio.html", "geom.io"),
        "any": (f"{BASE}mat/ref/%2Bgeom/%2Bio.html", "geom.io"),
    }
    assert found == ""


def test_intersphinx_to_the_only_folder_of_a_namespace(make_app, tmp_path):
    # folder grouping: +geom/ is the only folder of geom and no namespace
    # object is described
    outdir = build_library(make_app, tmp_path / "lib")
    mapping = {"lib": (BASE, str(outdir / "objects.inv"))}
    references = {
        "folder": ":mat:folder:`geom`",
        "namespace": ":mat:namespace:`geom`",
    }
    links, found = build_consumer(make_app, tmp_path / "app", mapping, references)
    assert links == {
        "folder": (f"{BASE}mat/ref/%2Bgeom/index.html", "geom"),
        "namespace": (f"{BASE}mat/ref/%2Bgeom/index.html", "geom"),
    }
    assert found == ""


@pytest.mark.parametrize("chooser", [False, True])
def test_intersphinx_to_a_namespace_of_several_folders(make_app, tmp_path, chooser):
    outdir = build_library(make_app, tmp_path / "lib", extra=["other/+geom/extra.m"])
    assert inventory(outdir)["geom"] == ("mat/name/geom.html", "-")
    mapping = {"lib": (BASE, str(outdir / "objects.inv"))}
    conf = f"matlab_link_shadowed_files_to_chooser_pages = {chooser}\n"
    references = {
        "folder": ":mat:folder:`geom`",
        # no namespace object and no only folder to fall back to
        "namespace": ":mat:namespace:`geom`",
    }
    links, found = build_consumer(make_app, tmp_path / "app", mapping, references, conf)
    assert links["namespace"] == (None, "geom")
    assert "mat:namespace reference target not found: geom" in found
    if chooser:
        assert links["folder"] == (f"{BASE}mat/name/geom.html", "geom")
        assert found.count("WARNING") == 1
    else:
        assert links["folder"] == (None, "geom")
        assert (
            "'geom' matches several objects: +geom/, other/+geom/; use a path "
            "reference for one folder, or mat:namespace, mat:autonamespace or "
            ":mat:namespace: for the whole namespace [mat.ambiguous]"
        ) in strip_escape_sequences(found)
        assert found.count("WARNING") == 2


# --- builds -------------------------------------------------------------------------

BUILD_PAGES = {
    "index": ".. toctree::\n\n" + "".join(f"   p{i}\n" for i in range(1, 7)),
    "p1": "P1\n==\n\n.. mat:autonamespace:: ns\n   :members:\n",
    "p2": "P2\n==\n\n.. mat:namespace:: ns\n\nSee :mat:func:`g`.\n",
    "p3": "P3\n==\n\n.. mat:autonamespace:: solo\n   :members:\n",
    "p4": "P4\n==\n\n.. mat:folder:: x/+ns/\n\n.. mat:folder:: ns\n\n"
    ".. mat:autofolder:: one/+solo/\n",
    "p5": "P5\n==\n\n:mat:namespace:`ns`, :mat:namespace:`solo`.\n",
    "p6": "P6\n==\n\n.. mat:autonamespace:: nosuch\n",
}


def test_serial_and_parallel_builds_agree(make_app, tmp_path):
    outputs, found = [], []
    for parallel in (0, 2):
        root = tmp_path / f"j{parallel}"
        app = build(make_app, root, BUILD_PAGES, parallel=parallel)
        app.cleanup()
        outputs.append(snapshot(Path(app.outdir)))
        found.append(sorted(warnings(app).replace(str(root), "").splitlines()))
    assert differences(*outputs) == []
    assert found[0] == found[1]
    assert len(found[0]) == 2  # nosuch; ns names two folders


def test_incremental_build_after_adding_a_file_equals_a_clean_one(make_app, tmp_path):
    root = tmp_path / "inc"
    build(make_app, root, BUILD_PAGES).cleanup()
    added = {"src/y/+ns/added.m": FUNCTION.format(name="added")}
    write(root, added)
    app = make_app(srcdir=root)
    app.build()
    app.cleanup()
    assert "y/+ns/added.m" in objects(app)
    assert "p1" in app.env.get_domain("mat").read_docnames
    fresh = build(make_app, tmp_path / "fresh", BUILD_PAGES, sources=added)
    fresh.cleanup()
    assert differences(snapshot(Path(app.outdir)), snapshot(Path(fresh.outdir))) == []
    shutil.rmtree(tmp_path / "fresh")
