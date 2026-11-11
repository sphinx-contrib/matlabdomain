"""scmd apidoc: output names, pages, templates, writing, the CLI and
builds of its output (plan.md Section 2.8, Phase 7).
"""

import importlib.metadata
import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
from sphinx.util.inventory import InventoryFile

from sphinxcontrib import mat_handlers, mat_types
from sphinxcontrib.mat_classify import is_hidden
from sphinxcontrib.mat_config import CONFIG
from sphinxcontrib.mat_types import IndexSettings, build_index
from sphinxcontrib.matlab_apidoc import (
    ApidocOptions,
    _cli,
    _generate,
    _names,
    generate,
    main,
)
from sphinxcontrib.matlab_apidoc._generate import MARKER, build_pages, render

TESTS = Path(__file__).parent
ROOT = TESTS / "roots" / "test_apidoc_basics"
GOLDEN = TESTS / "apidoc_golden"
EXAMPLE = TESTS.parent / "examples" / "apidoc"
NOT_CALLABLE = {
    "+for/nm_kw.m": "folder name 'for' is a MATLAB keyword",
    "@Bad/Other.m": "a class in @Bad must be named Bad",
    "@NmBox/sub/nm_legacy.m": (
        "files in subfolders of a class folder are not callable since R2026a"
    ),
    "bad-name.m": "its name 'bad-name' is not a valid MATLAB identifier",
}
FOLDER_PAGES = [
    "+a/+b/index",
    "+a/index",
    "+for/index",
    "+nmpkg/index",
    "+nmpkg/private/index",
    "alpha/index",
    "beta/index",
    "donn~C3~A9es/index",
    "index",
    "my~20folder/index",
    "private/index",
    "root",
]
PAGE_KEYS = {
    "docname",
    "ref",
    "title",
    "kind",
    "is_root",
    "page",
    "pages",
    "first",
    "last",
    "sections",
    "separate",
    "maxdepth",
    "sidecars",
    "readme",
}
ROOT_PAGE_KEYS = {"docname", "title", "pages", "maxdepth"}
ENTRY_KEYS = {
    "ref",
    "kind",
    "directive",
    "argument",
    "options",
    "title",
    "display",
    "matlab_name",
    "callable",
    "private",
    "docname",
}
FUNCTION = "function {name}()\n% {name} help.\nend\n"
FOLDER = 'matlab_apidoc_group = "folder"\nmatlab_apidoc_private = True\n'


def tree(folder):
    """``{relative path: bytes}`` of the files below ``folder``."""
    folder = Path(folder)
    return {
        p.relative_to(folder).as_posix(): p.read_bytes()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


def write(root, files):
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def pages_of(root, **options):
    """Pages of ``root``; folder grouping, with private files, unless given."""
    options.setdefault("group", "folder")
    if options["group"] == "folder":
        options.setdefault("private", True)
    source_index = build_index(IndexSettings(str(root)))
    return build_pages(source_index, ApidocOptions("out", **options))


def run(root, out, *flags):
    """Generate the pages of ``root``; folder grouping, with private files,
    unless given.
    """
    options = {"group": "folder", **dict(flags)}
    if options["group"] == "folder":
        options.setdefault("private", True)
    return generate(
        build_index(IndexSettings(str(root))), ApidocOptions(str(out), **options)
    )


def conf_dir(folder, out, conf="", root=ROOT):
    """Write ``folder/conf.py`` for the MATLAB root ``root`` and the output
    folder ``out`` (absolute paths) plus ``conf``; return the folder for -c.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "conf.py").write_text(
        f"matlab_src_code_project_root = {str(root)!r}\n"
        f"matlab_apidoc_output_dir = {str(out)!r}\n{conf}"
    )
    return str(folder)


@pytest.fixture
def project(tmp_path):
    """Copy the fixture (a Sphinx project whose root is the MATLAB root)."""
    dst = tmp_path / "project"
    shutil.copytree(ROOT, dst)
    return dst


# --- output names (_names.py), the same on every OS --------------------------


@pytest.mark.parametrize(
    ("segment", "expected"),
    [
        ("+pkg", "+pkg"),
        ("@Cls", "@Cls"),
        ("Cls.m", "Cls.m"),
        ("a_b-c.d", "a_b-c.d"),
        ("my folder", "my~20folder"),
        ("donn\u00e9es", "donn~C3~A9es"),
        ("~x", "~7Ex"),
        ("50%#", "50~25~23"),
        ("aux", "~61ux"),
        ("AUX.m", "~41UX.m"),
        ("com1.m.rst", "~63om1.m.rst"),
        ("Lpt9", "~4Cpt9"),
        ("COM10", "COM10"),
        ("auxiliary", "auxiliary"),
        ("x.", "x~2E"),
        ("nul.", "~6Eul~2E"),
        ("_x.m", "_x.m"),
    ],
)
def test_escape_segment(segment, expected):
    assert _names.escape_segment(segment) == expected


def test_escape_upper_and_long_paths():
    assert _names.escape_upper("Utils~20B") == "~55tils~20~42"
    assert not _names.too_long("x" * 259)
    assert _names.too_long("x" * 260)


def test_docnames_mirror_the_folder_tree():
    refs = ["./", "a/", "a/+p/", "a/+p/Cls.m", "Top.m", "a/@C/sub/f.m"]
    names, collisions = _names.docnames(refs, suffix="txt", tocfile="api")
    assert names == {
        "./": "api",
        "a/": "a/index",
        "a/+p/": "a/+p/index",
        "a/+p/Cls.m": "a/+p/Cls.m",
        "Top.m": "Top.m",
        "a/@C/sub/f.m": "a/@C/sub/f.m",
    }
    assert collisions == []


def test_docnames_escape_a_leading_underscore_of_folders():
    refs = ["_util/", "_util/_x.m", "a/__b/c.m", "_y.m"]
    names, collisions = _names.docnames(refs)
    assert names == {
        "_util/": "~5Futil/index",
        "_util/_x.m": "~5Futil/_x.m",
        "a/__b/c.m": "a/~5F_b/c.m",
        "_y.m": "_y.m",
    }
    assert collisions == []


def test_docnames_escape_case_collisions():
    refs = ["./", "Utils/", "utils/", "Utils/A.m", "Utils/a.m", "Foo.m", "foo.m", "x/"]
    names, collisions = _names.docnames(refs)
    assert names == {
        "./": "index",
        "Utils/": "~55tils/index",
        "utils/": "utils/index",
        "Utils/A.m": "~55tils/~41.m",
        "Utils/a.m": "~55tils/a.m",
        "Foo.m": "~46oo.m",
        "foo.m": "foo.m",
        "x/": "x/index",
    }
    assert collisions == [
        ("", ["Foo.m", "foo.m"]),
        ("", ["Utils/", "utils/"]),
        ("~55tils", ["A.m", "a.m"]),
    ]


def test_docnames_avoid_the_page_name():
    names, collisions = _names.docnames(["./", "INDEX.RST/"])
    assert names["INDEX.RST/"] == "~49~4E~44~45~58.~52~53~54/index"
    assert collisions == [("", ["INDEX.RST/"])]
    names, collisions = _names.docnames(
        ["./", "a/", "a/index.rst/", "api.m"], tocfile="api.m"
    )
    assert names["a/index.rst/"] == "a/~69ndex.rst/index"
    assert names["api.m"] == "~61pi.m"
    assert collisions == [("", ["api.m"]), ("a", ["index.rst/"])]


@pytest.mark.parametrize("suffix", ["rst", "txt"])
@pytest.mark.parametrize("stem", ["guide-md", "Cls.m"])
def test_docnames_avoid_file_folder_collisions(suffix, stem):
    folder = f"{stem}.{suffix}"
    literal = f"{stem}~2E{suffix}/"
    refs = ["./", stem, f"{folder}/", f"{folder}/child.m", literal]
    names, collisions = _names.docnames(refs, suffix=suffix)
    assert names[stem] == stem
    page_file = f"{names[stem]}.{suffix}"
    output_folder = names[f"{folder}/"].rsplit("/", 1)[0]
    assert page_file.lower() != output_folder.lower()
    assert output_folder.lower() != names[literal].rsplit("/", 1)[0].lower()
    assert names[f"{folder}/child.m"] == f"{output_folder}/child.m"
    assert collisions == [("", sorted([stem, f"{folder}/"]))]
    assert _names.docnames(reversed(refs), suffix=suffix) == (names, collisions)


def test_docnames_keep_case_only_file_folder_names():
    names, collisions = _names.docnames(["./", "Cls.m", "cls.m.rst/", "cls.m.rst/x.m"])
    assert names["Cls.m"] == "~43ls.m"
    assert names["cls.m.rst/x.m"] == "cls.m.rst/x.m"
    assert collisions == [("", ["Cls.m", "cls.m.rst/"])]


def test_docnames_are_injective_and_case_insensitive_unique():
    segments = [
        "a b", "a~20b", "a%20b", "~", "~7E", "aux", "~61ux", "AUX", "Aux",
        "x.", "x~2E", "\u00dc", "\u00fc", "~C3~9C", "Utils", "utils", "UTILS",
    ]  # fmt: skip
    refs = ["./", *(f"{s}/" for s in segments), *(f"{s}.m" for s in segments)]
    names, _ = _names.docnames(refs)
    values = list(names.values())
    assert len(set(values)) == len(values)
    assert len({v.lower() for v in values}) == len(values)
    assert all(v.isascii() for v in values)


# --- page model -------------------------------------------------------------


def test_pages_of_the_fixture():
    pages = {p.docname: p for p in pages_of(ROOT)}
    assert sorted(pages) == FOLDER_PAGES
    index = pages.pop("index")
    assert index.template == "root.rst.jinja"
    assert set(index.context) == ROOT_PAGE_KEYS
    # Flat: the root folder first, then by path.
    assert index.context["pages"] == [
        "root",
        "+a/index",
        "+a/+b/index",
        "+for/index",
        "+nmpkg/index",
        "+nmpkg/private/index",
        "alpha/index",
        "beta/index",
        "donn~C3~A9es/index",
        "my~20folder/index",
        "private/index",
    ]
    for page in pages.values():
        assert page.template == "folder.rst.jinja"
        assert set(page.context) == PAGE_KEYS
        assert (page.context["page"], page.context["pages"]) == (1, 1)
        for _, entries in page.context["sections"]:
            assert all(set(entry) == ENTRY_KEYS for entry in entries)

    root = pages["root"].context
    assert (root["kind"], root["title"], root["is_root"]) == ("root", "folder ./", True)
    sections = {
        title: [e["ref"] for e in entries] for title, entries in root["sections"]
    }
    assert list(sections) == ["Classes", "Functions", "Scripts", "Apps"]
    # @ folders go on the page above them; sorted by casefold(title), ref
    assert sections["Classes"] == ["@Bad/Other.m", "@ApCls/ApCls.m", "@NmBox/NmBox.m"]
    # An @ folder that is not a class (old style, or no @X/X.m classdef)
    # lists its functions; files that are not callable are listed by path.
    assert sections["Functions"] == [
        "@NmBox/sub/nm_legacy.m",
        "@ApCls/private/ap_cls_helper.m",
        "bad-name.m",
        "@Bad/bad_fn.m",
        "@OldStyle/OldStyle.m",
        "@OldStyle/display.m",
    ]
    assert sections["Apps"] == ["Application.mlapp"]
    listed = {
        e["ref"]: e
        for page in pages.values()
        for _, entries in page.context["sections"]
        for e in entries
    }
    # Class folder methods and hidden files are not listed.
    for ref in ("@ApCls/ap_method.m", "+nmpkg/@NmCls/nm_helper.m"):
        assert ref not in listed
    assert not any(is_hidden(ref) for ref in listed)
    assert listed["+nmpkg/@NmCls/NmCls.m"]["options"] == {
        "members": "",
        "undoc-members": "",
        "show-inheritance": "",
    }
    assert listed["+nmpkg/@NmCls/NmCls.m"]["directive"] == "mat:autoclass"
    assert listed["Application.mlapp"]["directive"] == "mat:autoapplication"
    assert listed["bad-name.m"]["title"] == "bad-name.m"
    assert listed["bad-name.m"]["callable"] is False
    assert listed["private/nm_priv.m"]["private"] is True
    assert listed["+nmpkg/nm_func.m"]["title"] == "nmpkg.nm_func"

    nmpkg = pages["+nmpkg/index"].context
    assert (nmpkg["kind"], nmpkg["title"]) == ("namespace", "folder +nmpkg/")
    assert pages["+for/index"].context["title"] == "folder +for/"
    assert pages["my~20folder/index"].context["ref"] == "my folder/"


def test_separate_pages():
    pages = {p.docname: p for p in pages_of(ROOT, separate=True)}
    assert len(pages) == len(FOLDER_PAGES) + 23
    nmpkg = pages["+nmpkg/index"].context
    assert [
        (t, [e["docname"] for e in entries]) for t, entries in nmpkg["sections"]
    ] == [
        ("Classes", ["@NmCls/NmCls.m"]),
        ("Functions", ["nm_func.m"]),
    ]
    page = pages["+nmpkg/@NmCls/NmCls.m"]
    assert page.template == "object.rst.jinja"
    assert set(page.context) == ENTRY_KEYS
    assert page.context["docname"] == "+nmpkg/@NmCls/NmCls.m"


def test_only_a_class_file_makes_a_class_folder(tmp_path):
    write(
        tmp_path,
        {
            # @C/C.m is a classdef: function files are methods; another
            # classdef and a script are listed
            "@C/C.m": "classdef C\nend\n",
            "@C/K.m": "classdef K\nend\n",
            "@C/m.m": FUNCTION.format(name="m"),
            "@C/s.m": "x = 1;\n",
            # no @D/D.m: not a class, even with a single classdef
            "@D/Other.m": "classdef Other\nend\n",
            "@D/f.m": FUNCTION.format(name="f"),
            # @E/E.m is not a classdef (old style): not a class
            "@E/E.m": FUNCTION.format(name="E"),
            "@E/g.m": FUNCTION.format(name="g"),
            # no class file: not a class
            "@F/h.m": FUNCTION.format(name="h"),
        },
    )
    pages = {p.docname: p for p in pages_of(tmp_path)}
    assert sorted(pages) == ["index", "root"]
    listed = sorted(
        e["ref"] for _, entries in pages["root"].context["sections"] for e in entries
    )
    assert listed == sorted(
        [
            "@C/C.m",
            "@C/K.m",
            "@C/s.m",
            "@D/Other.m",
            "@D/f.m",
            "@E/E.m",
            "@E/g.m",
            "@F/h.m",
        ]
    )


def test_the_domain_attaches_methods_only_to_the_class_file(make_app, tmp_path):
    write(
        tmp_path,
        {
            "@C/C.m": "classdef C\nend\n",
            "@C/m.m": FUNCTION.format(name="m"),
            "@D/Other.m": "classdef Other\nend\n",
            "@D/f.m": FUNCTION.format(name="f"),
            "@E/E.m": FUNCTION.format(name="E"),
            "@E/g.m": FUNCTION.format(name="g"),
            "conf.py": 'extensions = ["sphinxcontrib.matlab"]\n'
            'matlab_src_code_project_root = "."\n',
            "index.rst": "Index\n=====\n",
        },
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    dom = app.env.get_domain("mat")
    cls = mat_types.resolve(dom, "@C/C.m")
    assert sorted(cls.methods) == ["m"]
    assert isinstance(mat_types.resolve(dom, "@C/m.m"), mat_types.MatMethod)
    other = mat_types.resolve(dom, "@D/Other.m")
    assert isinstance(other, mat_types.MatClass)
    assert other.methods == {}
    for ref in ("@D/f.m", "@E/E.m", "@E/g.m"):
        obj = mat_types.resolve(dom, ref)
        assert type(obj) is mat_types.MatFunction, ref


def test_a_folder_with_only_hidden_files_has_no_page(tmp_path):
    write(
        tmp_path, {"a/Contents.m": "% Contents\n", "b/c/f.m": FUNCTION.format(name="f")}
    )
    pages = pages_of(tmp_path)
    # No page for a folder without files of its own (b/).
    assert [p.docname for p in pages] == ["b/c/index", "index"]


def test_an_empty_root_gets_its_page_and_a_warning(tmp_path, caplog_sphinx):
    (page,) = pages_of(tmp_path)
    assert page.docname == "index"
    assert page.context["pages"] == []
    assert any("no documentable files" in m for _, m in caplog_sphinx)


def test_folder_pages_split_at_the_page_size(tmp_path):
    write(tmp_path, {f"a/f{i}.m": FUNCTION.format(name=f"f{i}") for i in range(5)})
    write(tmp_path, {"a/notes.md": "# Notes\n", "g.m": FUNCTION.format(name="g")})
    source_index = build_index(IndexSettings(str(tmp_path), sidecar_suffixes=(".md",)))
    options = ApidocOptions("out", group="folder", page_size=2)
    pages = {p.docname: p for p in build_pages(source_index, options)}
    assert pages["index"].context["pages"] == [
        "root",
        "a/index",
        "a/index-2",
        "a/index-3",
    ]
    third = pages["a/index-3"].context
    assert (third["title"], third["page"], third["pages"]) == (
        "folder a/ (5-6)",
        3,
        3,
    )
    assert [e["ref"] for _, es in third["sections"] for e in es] == ["a/f4.m"]
    assert [e["docname"] for e in third["sidecars"]] == ["notes-md"]
    assert pages["root"].context["title"] == "folder ./"
    text = render([pages["a/index-2"], pages["a/index"]])
    assert ".. mat:autofolder:: a/" in text["a/index"]
    assert "mat:autofolder" not in text["a/index-2"]


def test_root_folder_page_avoids_the_toc_file(tmp_path):
    write(tmp_path, {"g.m": FUNCTION.format(name="g")})
    pages = pages_of(tmp_path, tocfile="Root")
    assert sorted(p.docname for p in pages) == ["Root", "~72oot"]


def test_folders_of_one_namespace_are_titled_by_path(tmp_path):
    write(
        tmp_path,
        {
            "a/+ns/f.m": FUNCTION.format(name="f"),
            "b/+ns/g.m": FUNCTION.format(name="g"),
        },
    )
    pages = {p.docname: p.context for p in pages_of(tmp_path)}
    assert [(pages[d]["title"], pages[d]["kind"]) for d in pages["index"]["pages"]] == [
        ("folder a/+ns/", "namespace"),
        ("folder b/+ns/", "namespace"),
    ]


# --- namespace grouping -----------------------------------------------------

NAMESPACE_PAGE_KEYS = {
    "docname",
    "title",
    "namespace",
    "kind",
    "page",
    "pages",
    "first",
    "last",
    "sections",
    "sidecars",
    "separate",
    "maxdepth",
}


def namespace_pages(root, **options):
    return {p.docname: p for p in pages_of(root, group="namespace", **options)}


def listed_refs(page):
    return [e["ref"] for _, entries in page.context["sections"] for e in entries]


PRIVATE = {
    "private/nm_priv.m",
    "+nmpkg/private/pk_priv.m",
    "@ApCls/private/ap_cls_helper.m",
}


@pytest.mark.parametrize(
    ("group", "private", "listed"),
    [
        ("namespace", None, False),
        ("namespace", False, False),
        ("namespace", True, True),
        ("folder", None, False),
        ("folder", True, True),
        ("folder", False, False),
    ],
)
def test_private_files_setting(group, private, listed):
    # Not pages_of: it lists private files in folder grouping by default.
    if private is None:
        options = ApidocOptions("out", group=group)
    else:
        options = ApidocOptions("out", group=group, private=private)
    source_index = build_index(IndexSettings(str(ROOT)))
    pages = {p.docname: p for p in build_pages(source_index, options)}
    refs = {
        ref
        for page in pages.values()
        if "sections" in page.context
        for ref in listed_refs(page)
    }
    assert (refs & PRIVATE == PRIVATE) if listed else not refs & PRIVATE
    if group == "namespace" and listed:
        # With the folder above: a namespace, or Global.
        assert "+nmpkg/private/pk_priv.m" in listed_refs(pages["nmpkg"])
        assert "private/nm_priv.m" in listed_refs(pages["global"])
    if group == "folder":
        assert ("private/index" in pages) is listed


def test_namespace_pages_of_the_fixture(caplog_sphinx):
    pages = namespace_pages(ROOT)
    assert sorted(pages) == ["a", "a.b", "global", "index", "nmpkg"]
    root = pages["index"]
    assert root.template == "root.rst.jinja"
    assert root.context == {
        "docname": "index",
        "title": "API reference",
        "pages": ["global", "a", "a.b", "nmpkg"],
        "maxdepth": 4,
    }
    for name in ("a", "a.b", "global", "nmpkg"):
        assert set(pages[name].context) == NAMESPACE_PAGE_KEYS
        assert pages[name].template == "namespace.rst.jinja"
    nmpkg = pages["nmpkg"].context
    assert (nmpkg["title"], nmpkg["namespace"], nmpkg["kind"]) == (
        "namespace nmpkg",
        "nmpkg",
        "namespace",
    )
    assert (nmpkg["page"], nmpkg["pages"], nmpkg["first"], nmpkg["last"]) == (
        1,
        1,
        1,
        2,
    )
    # Functions first; private/ files and class folder methods left out.
    assert [t for t, _ in nmpkg["sections"]] == ["Functions", "Classes"]
    assert listed_refs(pages["nmpkg"]) == ["+nmpkg/nm_func.m", "+nmpkg/@NmCls/NmCls.m"]
    glob = pages["global"].context
    assert (glob["title"], glob["namespace"], glob["kind"]) == (
        "Global",
        None,
        "global",
    )
    assert [t for t, _ in glob["sections"]] == [
        "Functions",
        "Classes",
        "Scripts",
        "Apps",
    ]
    refs = listed_refs(pages["global"])
    assert "+for/nm_kw.m" in refs  # not a valid namespace: global, by path
    assert not any("private/" in ref for ref in refs)
    assert "@ApCls/ap_method.m" not in refs
    # Two global functions with one name are titled by path, with a warning.
    titles = {e["ref"]: e["title"] for _, es in glob["sections"] for e in es}
    assert titles["alpha/nm_shared.m"] == "alpha/nm_shared.m"
    assert titles["beta/nm_shared.m"] == "beta/nm_shared.m"
    assert any(
        s == "apidoc" and "nm_shared is defined by several files in Global" in m
        for s, m in caplog_sphinx
    )


def test_a_namespace_merges_its_folders_and_pages_are_split(tmp_path):
    write(
        tmp_path,
        {
            **{f"a/+ns/f{i}.m": FUNCTION.format(name=f"f{i}") for i in range(3)},
            **{f"b/+ns/g{i}.m": FUNCTION.format(name=f"g{i}") for i in range(2)},
            "b/+ns/C.m": "classdef C\nend\n",
            "b/+ns/+sub/h.m": FUNCTION.format(name="h"),
            "top.m": FUNCTION.format(name="top"),
        },
    )
    pages = namespace_pages(tmp_path, page_size=2)
    assert pages["index"].context["pages"] == [
        "global",
        "ns",
        "ns-2",
        "ns-3",
        "ns.sub",
    ]
    contexts = [pages[name].context for name in ("ns", "ns-2", "ns-3")]
    assert [c["title"] for c in contexts] == [
        "namespace ns (1-2)",
        "namespace ns (3-4)",
        "namespace ns (5-6)",
    ]
    assert [(c["page"], c["pages"], c["first"], c["last"]) for c in contexts] == [
        (1, 3, 1, 2),
        (2, 3, 3, 4),
        (3, 3, 5, 6),
    ]
    assert [listed_refs(pages[name]) for name in ("ns", "ns-2", "ns-3")] == [
        ["a/+ns/f0.m", "a/+ns/f1.m"],
        ["a/+ns/f2.m", "b/+ns/g0.m"],
        ["b/+ns/g1.m", "b/+ns/C.m"],
    ]
    assert pages["ns-3"].context["sections"][1][0] == "Classes"
    assert pages["global"].context["title"] == "Global"


def test_sidecar_docs_go_on_their_namespace_page(tmp_path):
    write(
        tmp_path,
        {
            "+ns/f.m": FUNCTION.format(name="f"),
            "+ns/README.md": "# Ns\n",
            "+ns/@C/C.m": "classdef C\nend\n",
            "+ns/@C/guide.md": "# Guide\n",
            "+ns/private/notes.md": "# Private notes\n",
            "lib/README.md": "# Library\n",
            "lib/g.m": FUNCTION.format(name="g"),
        },
    )
    settings = IndexSettings(str(tmp_path), sidecar_suffixes=(".md",))
    options = ApidocOptions("out", page_size=3)
    pages = {p.docname: p for p in build_pages(build_index(settings), options)}
    assert sorted(pages) == ["global", "index", "ns", "ns-2"]
    sidecars = {
        name: [s["ref"] for s in pages[name].context["sidecars"]]
        for name in ("global", "ns", "ns-2")
    }
    # Sidecar docs count as entries, after the files, sorted by name.
    assert sidecars == {
        "global": ["lib/README.md"],
        "ns": ["+ns/@C/guide.md"],
        "ns-2": ["+ns/private/notes.md", "+ns/README.md"],
    }
    assert pages["ns-2"].context["sections"] == []


def test_namespace_docnames_avoid_collisions(tmp_path):
    options = ApidocOptions("out")
    bases = _generate._namespace_docnames(
        [None, "Ab", "ab", "index", "x.m"], options, {"x.m"}
    )
    assert bases == {
        None: "global",
        "Ab": "~41b",
        "ab": "ab",
        "index": "~69ndex",
        "x.m": "~78.m",
    }
    write(
        tmp_path,
        {
            "+index/h.m": FUNCTION.format(name="h"),
            "+x/+m/k.m": FUNCTION.format(name="k"),
            "x.m": FUNCTION.format(name="x"),
        },
    )
    pages = namespace_pages(tmp_path)
    assert pages["index"].context["pages"] == ["global", "~69ndex", "x.m"]
    with_files = namespace_pages(tmp_path, separate=True)
    # The page of the file x.m takes the name; the namespace x.m is escaped.
    assert with_files["index"].context["pages"] == ["global", "~69ndex", "~78.m"]
    assert with_files["x.m"].template == "object.rst.jinja"


def test_namespace_grouping_of_an_empty_root(tmp_path, caplog_sphinx):
    (page,) = pages_of(tmp_path, group="namespace")
    assert (page.docname, page.context["pages"]) == ("index", [])
    assert any("no documentable files" in m for _, m in caplog_sphinx)


@pytest.fixture
def caplog_sphinx():
    """``(subtype, message)`` of the warnings on the ``sphinx`` loggers; Sphinx
    test apps leave handlers there that rewrite records.
    """
    import logging

    records = []

    class Collect(logging.Handler):
        def emit(self, record):
            records.append((getattr(record, "subtype", None), record.getMessage()))

    logger = logging.getLogger("sphinx")
    saved = logger.handlers[:], logger.propagate
    logger.handlers, logger.propagate = [Collect(logging.WARNING)], False
    yield records
    logger.handlers, logger.propagate = saved


# --- golden trees, rendering and writing ------------------------------------


@pytest.mark.parametrize(
    ("name", "conf"),
    [
        ("default", ""),
        ("separate", "matlab_apidoc_separate = True\n"),
        ("folder", FOLDER),
        ("folder-separate", f"{FOLDER}matlab_apidoc_separate = True\n"),
    ],
)
def test_golden_tree(tmp_path, name, conf):
    out = tmp_path / "out"
    assert main(["-q", "-c", conf_dir(tmp_path / "docs", out, conf)]) == 0
    assert tree(out) == tree(GOLDEN / name)


def test_files_are_utf8_with_lf_and_the_marker(tmp_path):
    run(ROOT, tmp_path)
    for path, data in tree(tmp_path).items():
        assert data.startswith(MARKER.encode() + b"\n\n"), path
        assert b"\r" not in data
        assert data.endswith(b"\n") and not data.endswith(b"\n\n")
        data.decode("utf-8")


def test_second_run_writes_nothing(tmp_path):
    first = run(ROOT, tmp_path)
    assert len(first.created) == len(FOLDER_PAGES)
    mtimes = {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*.rst")}
    for force in (False, True):
        again = run(ROOT, tmp_path, ("force", force))
        assert (again.created, again.updated, again.kept) == ([], [], [])
        assert len(again.unchanged) == len(FOLDER_PAGES)
    assert {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*.rst")} == mtimes


def test_marked_pages_are_rewritten_unmarked_kept_without_force(
    tmp_path, caplog_sphinx
):
    run(ROOT, tmp_path)
    golden = (GOLDEN / "folder" / "alpha" / "index.rst").read_bytes()
    page = tmp_path / "alpha" / "index.rst"
    page.write_text(f"{MARKER}\n\nStale\n=====\n")
    rewritten = run(ROOT, tmp_path)
    assert rewritten.updated == ["alpha/index.rst"]
    assert page.read_bytes() == golden
    page.write_text("Edited\n======\n")
    kept = run(ROOT, tmp_path)
    assert kept.kept == ["alpha/index.rst"]
    assert not kept.changed
    assert page.read_text() == "Edited\n======\n"
    assert any("has no marker line; it is kept" in m for _, m in caplog_sphinx)
    forced = run(ROOT, tmp_path, ("force", True))
    assert forced.updated == ["alpha/index.rst"]
    assert page.read_bytes() == golden


def test_dry_run_writes_nothing(tmp_path):
    out = tmp_path / "out"
    result = run(ROOT, out, ("dry_run", True), ("remove_old", True))
    assert len(result.created) == len(FOLDER_PAGES)
    assert not out.exists()


def test_remove_old_deletes_only_stale_marked_files(tmp_path):
    run(ROOT, tmp_path)
    write(
        tmp_path,
        {
            "old/deep/index.rst": f"{MARKER}\n\nOld\n===\n",
            "notes.rst": "Notes\n=====\n",
            "_static/x.rst": f"{MARKER}\n",
            "alpha/stale.txt": f"{MARKER}\n",
        },
    )
    dry = run(ROOT, tmp_path, ("remove_old", True), ("dry_run", True))
    assert dry.removed == ["old/deep/index.rst"]
    assert (tmp_path / "old" / "deep" / "index.rst").exists()
    result = run(ROOT, tmp_path, ("remove_old", True))
    assert result.removed == ["old/deep/index.rst"]
    assert not (tmp_path / "old").exists()
    for kept in ("notes.rst", "_static/x.rst", "alpha/stale.txt"):
        assert (tmp_path / kept).exists()
    assert len(result.unchanged) == len(FOLDER_PAGES)


def test_remove_old_keeps_a_dangling_link(tmp_path):
    run(ROOT, tmp_path)
    try:
        os.symlink(tmp_path / "missing.rst", tmp_path / "stale.rst")
    except OSError:
        pytest.skip("cannot create symbolic links")
    result = run(ROOT, tmp_path, ("remove_old", True))
    assert result.removed == []
    assert os.path.islink(tmp_path / "stale.rst")


def _case_insensitive(folder):
    probe = folder / "case_probe"
    probe.write_text("")
    try:
        return (folder / "CASE_PROBE").exists()
    finally:
        probe.unlink()


def test_case_only_renames_reach_the_output(tmp_path):
    # Pages of an earlier run, from sources whose names differed only by case.
    out = tmp_path / "out"
    run(ROOT, out, ("separate", True))
    (out / "alpha").rename(out / "ALPHA")
    (out / "ALPHA" / "nm_shared.m.rst").rename(out / "ALPHA" / "NM_shared.m.rst")
    result = run(ROOT, out, ("separate", True), ("force", True), ("remove_old", True))
    assert tree(out) == tree(GOLDEN / "folder-separate")
    if _case_insensitive(tmp_path):
        assert result.removed == []
    else:
        assert sorted(result.removed) == ["ALPHA/NM_shared.m.rst", "ALPHA/index.rst"]


def test_dry_run_does_not_rename(tmp_path):
    if not _case_insensitive(tmp_path):
        pytest.skip("needs a case-insensitive file system")
    out = tmp_path / "out"
    run(ROOT, out, ("separate", True))
    (out / "alpha").rename(out / "ALPHA")
    # alpha/ holds two pages: the folder is counted once.
    result = run(ROOT, out, ("separate", True), ("force", True), ("dry_run", True))
    assert "ALPHA" in os.listdir(out)
    assert result.renamed == ["alpha"]
    assert result.changed


def test_case_variant_without_the_marker_is_kept(tmp_path, caplog_sphinx):
    if not _case_insensitive(tmp_path):
        pytest.skip("needs a case-insensitive file system")
    out = tmp_path / "out"
    run(ROOT, out)
    (out / "beta" / "index.rst").unlink()
    (out / "beta" / "INDEX.rst").write_text("Hand-written\n============\n")
    result = run(ROOT, out)
    assert result.kept == ["beta/index.rst"]
    assert not result.changed
    assert os.listdir(out / "beta") == ["INDEX.rst"]
    assert (out / "beta" / "INDEX.rst").read_text() == "Hand-written\n============\n"
    assert any("only by case; it is kept" in m for _, m in caplog_sphinx)
    forced = run(ROOT, out, ("force", True))
    assert (forced.renamed, forced.updated) == (["beta/index.rst"], ["beta/index.rst"])
    assert os.listdir(out / "beta") == ["index.rst"]
    golden = GOLDEN / "folder" / "beta" / "index.rst"
    assert (out / "beta" / "index.rst").read_bytes() == golden.read_bytes()


def test_remove_old_after_files_are_excluded(tmp_path):
    out, docs = tmp_path / "out", tmp_path / "docs"
    assert main(["-q", "-c", conf_dir(docs, out, FOLDER)]) == 0
    conf_dir(docs, out, f'{FOLDER}matlab_src_exclude_patterns = ["alpha"]\n')
    assert main(["-q", "-c", str(docs)]) == 0
    assert not (out / "alpha").exists()
    assert (out / "beta" / "index.rst").exists()
    # The root page is generated, so it is rewritten without its link.
    assert b"alpha/index" not in (out / "index.rst").read_bytes()


def test_no_remove_old_keeps_stale_pages(tmp_path):
    run(ROOT, tmp_path)
    source_index = build_index(IndexSettings(str(ROOT), exclude=("alpha",)))
    options = ApidocOptions(str(tmp_path), remove_old=False, group="folder")
    result = generate(source_index, options)
    assert result.removed == []
    assert (tmp_path / "alpha" / "index.rst").exists()


def test_templatedir_replaces_a_template(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "folder.rst.jinja").write_text(
        "{{ kind }}|{{ ref }}|{{ docname }}|{{ is_root }}|{{ maxdepth }}|"
        "{{ separate }}|{{ page }}/{{ pages }}\n"
        "{% for title, entries in sections %}{{ title }}:"
        "{% for e in entries %}{{ e.ref }}={{ e.kind }},{{ e.directive }},"
        "{{ e.options | list | join(';') }},{{ e.title }},{{ e.display }},"
        "{{ e.matlab_name }},{{ e.callable }},{{ e.private }},{{ e.docname }} "
        "{% endfor %}\n{% endfor %}"
    )
    out = tmp_path / "out"
    options = ApidocOptions(
        str(out), separate=True, maxdepth=2, templatedir=str(templates), group="folder"
    )
    generate(build_index(IndexSettings(str(ROOT))), options)
    assert (out / "+nmpkg" / "index.rst").read_text() == (
        f"{MARKER}\n\n"
        "namespace|+nmpkg/|+nmpkg/index|False|2|True|1/1\n"
        "Classes:+nmpkg/@NmCls/NmCls.m=class,mat:autoclass,"
        "members;undoc-members;show-inheritance,nmpkg.NmCls,nmpkg.NmCls,"
        "nmpkg.NmCls,True,False,@NmCls/NmCls.m \n"
        "Functions:+nmpkg/nm_func.m=function,mat:autofunction,,nmpkg.nm_func,"
        "nmpkg.nm_func,nmpkg.nm_func,True,False,nm_func.m \n"
    )
    # object.rst.jinja falls back to the default.
    assert (out / "+nmpkg" / "nm_func.m.rst").read_bytes() == (
        GOLDEN / "folder-separate" / "+nmpkg" / "nm_func.m.rst"
    ).read_bytes()


def test_python_api_sets_what_the_command_line_fixes(tmp_path):
    options = ApidocOptions(str(tmp_path), maxdepth=1, tocfile="contents", suffix="txt")
    generate(build_index(IndexSettings(str(ROOT))), options)
    names = sorted(tree(tmp_path))
    assert "contents.txt" in names
    assert all(name.endswith(".txt") for name in names)
    assert "   :maxdepth: 1\n" in (tmp_path / "contents.txt").read_text()


def test_long_paths_warn_on_windows(tmp_path, monkeypatch, caplog_sphinx):
    monkeypatch.setattr(_generate, "_WINDOWS", True)
    monkeypatch.setattr(_generate, "too_long", lambda path: path.endswith(".rst"))
    run(ROOT, tmp_path)
    long = [m for s, m in caplog_sphinx if "unless long paths are enabled" in m]
    assert len(long) == len(FOLDER_PAGES)


# --- command line -----------------------------------------------------------


def test_output_must_be_a_folder(tmp_path, capsys):
    (tmp_path / "file").write_text("")
    assert main(["-c", conf_dir(tmp_path / "docs", tmp_path / "file")]) == 2
    err = capsys.readouterr().err
    assert "matlab_apidoc_output_dir '" in err
    assert "is not a folder" in err


@pytest.mark.parametrize(
    "argv",
    [
        ["--bogus"],
        ["-o", "out"],
        ["src"],
        ["-t", "templates"],
        ["-e"],
        ["--conf", "."],
        ["--dry"],
    ],
)
def test_usage_errors_exit_2(capsys, monkeypatch, argv):
    monkeypatch.setenv("PYTHON_COLORS", "0")  # argparse colors usage from Python 3.14
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2
    assert "usage: scmd apidoc" in capsys.readouterr().err


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.startswith("scmd apidoc ")


def test_version_without_package_metadata(capsys, monkeypatch):
    def missing(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", missing)
    with pytest.raises(SystemExit):
        main(["--version"])
    assert capsys.readouterr().out == "scmd apidoc 0.0.0\n"


def test_output_and_warnings(tmp_path, capsys):
    docs = conf_dir(tmp_path / "docs", tmp_path / "out", FOLDER)
    assert main(["-c", docs]) == 0
    captured = capsys.readouterr()
    assert captured.out.count("Creating file ") == len(FOLDER_PAGES)
    assert f"{len(FOLDER_PAGES)} pages: {len(FOLDER_PAGES)} created" in captured.out
    assert "27 files indexed, 4 warnings" in captured.out
    assert sorted(captured.err.splitlines()) == sorted(
        f"WARNING: [sphinxcontrib-matlabdomain] {ref} is not callable in MATLAB "
        f"R2026a ({reason}); it is documented by its path reference. "
        "[mat.not_callable]"
        for ref, reason in NOT_CALLABLE.items()
    )
    assert main(["-q", "-n", "-c", docs]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert len(captured.err.splitlines()) == 4


@pytest.mark.parametrize("suppress", ["mat", "mat.not_callable"])
def test_conf_suppress_warnings_is_honored(tmp_path, capsys, suppress):
    conf = f"{FOLDER}suppress_warnings = [{suppress!r}]\n"
    docs = conf_dir(tmp_path / "docs", tmp_path / "out", conf)
    assert main(["-n", "-c", docs]) == 0
    captured = capsys.readouterr()
    assert "27 files indexed, 0 warnings" in captured.out
    assert captured.err == ""


def test_conf_suppress_warnings_of_another_subtype(tmp_path, capsys):
    conf = f'{FOLDER}suppress_warnings = ("mat.encoding", "ref")\n'
    docs = conf_dir(tmp_path / "docs", tmp_path / "out", conf)
    assert main(["-q", "-n", "-c", docs]) == 0
    assert len(capsys.readouterr().err.splitlines()) == 4


@pytest.mark.parametrize("value", ['"mat"', "None"])
def test_conf_suppress_warnings_must_be_a_list(tmp_path, capsys, value):
    docs = conf_dir(
        tmp_path / "docs", tmp_path / "out", f"suppress_warnings = {value}\n"
    )
    assert main(["-q", "-c", docs]) == 2
    assert "error: suppress_warnings must be a list, not " in capsys.readouterr().err


def test_dry_run_lists_changes(tmp_path, capsys):
    assert (
        main(["-n", "-c", conf_dir(tmp_path / "docs", tmp_path / "out", FOLDER)]) == 0
    )
    out = capsys.readouterr().out
    assert out.count("Would create file ") == len(FOLDER_PAGES)
    assert out.splitlines()[-1].startswith(f"Dry run: {len(FOLDER_PAGES)} pages")


def test_check_summary(tmp_path, capsys):
    docs = conf_dir(tmp_path / "docs", tmp_path / "out", FOLDER)
    assert main(["-q", "-c", docs]) == 0
    assert main(["--check", "-c", docs]) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"Check: {len(FOLDER_PAGES)} pages: 0 created")
    assert "27 files indexed, 4 warnings, " in out


def test_summary_singular(tmp_path, capsys):
    source = tmp_path / "src"
    source.mkdir()
    (source / "f.m").write_text("function f\n% F does it.\nend\n")
    docs = conf_dir(tmp_path / "docs", tmp_path / "out", root=source)
    assert main(["-n", "-c", docs]) == 0
    assert "; 1 file indexed, 0 warnings, " in capsys.readouterr().out


def test_include_and_exclude(tmp_path):
    out = tmp_path / "out"
    conf = 'matlab_src_include_patterns = ["+nmpkg/**"]\n'
    conf += 'matlab_src_exclude_patterns = ["**/private"]\n'
    assert main(["-q", "-c", conf_dir(tmp_path / "docs", out, conf)]) == 0
    assert sorted(tree(out)) == ["index.rst", "nmpkg.rst"]


def test_matlab_version_changes_callability(tmp_path, capsys):
    out = tmp_path / "out"
    docs = conf_dir(tmp_path / "docs", out, 'matlab_version = "R2025b"\n')
    assert main(["-q", "-c", docs]) == 0
    assert "nm_legacy" not in capsys.readouterr().err
    page = (out / "global.rst").read_text()
    assert "\nnm\\_legacy\n" in page


def test_logging_is_restored(tmp_path):
    import logging

    logger = logging.getLogger("sphinx")
    before = logger.handlers[:], logger.propagate, logger.level
    main(["-q", "-c", conf_dir(tmp_path / "docs", tmp_path / "out")])
    assert (logger.handlers, logger.propagate, logger.level) == before


def test_command_in_a_subprocess(tmp_path):
    out = tmp_path / "out"
    # -c defaults to the working folder.
    proc = subprocess.run(
        [sys.executable, "-m", "sphinxcontrib.matlab_cli", "apidoc"],
        cwd=conf_dir(tmp_path / "docs", out),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    assert tree(out) == tree(GOLDEN / "default")


def test_check_exits_1_when_pages_would_change(tmp_path, capsys):
    out = tmp_path / "out"
    docs = conf_dir(tmp_path / "docs", out)
    assert main(["-q", "--check", "-c", docs]) == 1
    assert not out.exists()
    assert "are out of date" in capsys.readouterr().err
    assert main(["-q", "-c", docs]) == 0
    assert main(["-q", "--check", "-c", docs]) == 0
    (out / "nmpkg.rst").write_text(f"{MARKER}\n\nStale\n=====\n")
    assert main(["--check", "-c", docs]) == 1
    assert "Would update file" in capsys.readouterr().out
    # A hand-written page (no marker) is not a change.
    (out / "nmpkg.rst").write_text("Edited\n======\n")
    assert main(["-q", "--check", "-c", docs]) == 0


def test_check_counts_removals(tmp_path, capsys):
    out = tmp_path / "out"
    docs = conf_dir(tmp_path / "docs", out)
    assert main(["-q", "-c", docs]) == 0
    write(out, {"old/index.rst": f"{MARKER}\n\nOld\n===\n"})
    before = tree(out)
    assert main(["--check", "-c", docs]) == 1
    assert "Would remove file" in capsys.readouterr().out
    assert tree(out) == before
    # A script with remove_old=False keeps them.
    kept = generate(
        build_index(IndexSettings(str(ROOT))),
        ApidocOptions(str(out), dry_run=True, remove_old=False),
    )
    assert not kept.changed


def test_crlf_pages_are_unchanged(tmp_path):
    out = tmp_path / "out"
    docs = conf_dir(tmp_path / "docs", out)
    assert main(["-q", "-c", docs]) == 0
    for page in out.rglob("*.rst"):
        page.write_bytes(page.read_bytes().replace(b"\n", b"\r\n"))
    before = {p: p.read_bytes() for p in out.rglob("*.rst")}
    assert main(["-q", "--check", "-c", docs]) == 0
    assert main(["-q", "-c", docs]) == 0
    assert {p: p.read_bytes() for p in out.rglob("*.rst")} == before


def test_cli_reports_renames(tmp_path, capsys):
    if not _case_insensitive(tmp_path):
        pytest.skip("needs a case-insensitive file system")
    out = tmp_path / "out"
    docs = conf_dir(tmp_path / "docs", out, FOLDER)
    assert main(["-q", "-c", docs]) == 0
    (out / "alpha").rename(out / "ALPHA")
    assert main(["-c", docs]) == 0
    printed = capsys.readouterr().out
    assert f"Renaming {out / 'alpha'}." in printed
    assert ", 1 renamed," in printed


# --- settings from conf.py (-c) ---------------------------------------------

CONF = """\
matlab_src_include_patterns = ["+nmpkg/**", "alpha/*"]
matlab_src_exclude_patterns = ["**/private"]
matlab_version = "R2025b"
matlab_apidoc_output_dir = "api"
matlab_apidoc_separate = True
matlab_apidoc_maxdepth = 2
matlab_apidoc_tocfile = "contents"
"""


def conf_project(tmp_path, conf, root="../src"):
    """Return a Sphinx source folder ``docs/`` whose conf.py points to a copy
    of ROOT in ``src/``.
    """
    shutil.copytree(ROOT, tmp_path / "src", ignore=shutil.ignore_patterns("conf.py"))
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "conf.py").write_text(f"matlab_src_code_project_root = {root!r}\n{conf}")
    return docs


def test_conf_gives_the_pages_of_the_python_api(tmp_path):
    docs = conf_project(tmp_path, CONF)
    assert main(["-q", "-c", str(docs)]) == 0
    settings = IndexSettings(
        str(tmp_path / "src"),
        include=("+nmpkg/**", "alpha/*"),
        exclude=("**/private",),
        matlab_version="R2025b",
    )
    out = tmp_path / "script"
    options = ApidocOptions(str(out), separate=True, maxdepth=2, tocfile="contents")
    generate(build_index(settings), options)
    assert tree(docs / "api") == tree(out)
    assert "+nmpkg/@NmCls/NmCls.m.rst" in tree(out)
    assert "   :maxdepth: 2\n" in (out / "contents.rst").read_text()


def test_conf_remove_old_false_keeps_stale_pages(tmp_path):
    out = tmp_path / "out"
    docs = conf_dir(tmp_path / "docs", out, "matlab_apidoc_remove_old = False\n")
    assert main(["-q", "-c", docs]) == 0
    write(out, {"old/index.rst": f"{MARKER}\n\nOld\n===\n"})
    assert main(["-q", "--check", "-c", docs]) == 0
    assert main(["-q", "-c", docs]) == 0
    assert (out / "old" / "index.rst").exists()


def test_conf_paths_are_relative_to_the_conf_dir(tmp_path, monkeypatch):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "folder.rst.jinja").write_text("{{ ref }}\n")
    conf = 'matlab_apidoc_output_dir = "out/api"\n'
    conf += f'matlab_apidoc_templatedir = "../templates"\n{FOLDER}'
    docs = conf_project(tmp_path, conf)
    monkeypatch.chdir(tmp_path / "src")
    assert main(["-q", "-c", "../docs"]) == 0
    assert (docs / "out" / "api" / "root.rst").read_text() == f"{MARKER}\n\n./\n"


def test_conf_settings(tmp_path):
    conf = 'matlab_apidoc_output_dir = "api"\n'
    docs = conf_project(tmp_path, f'{conf}matlab_version = "R2026a"\n')
    args = _cli.get_parser().parse_args(["-c", str(docs)])
    settings, options, suppress = _cli._settings(args)
    assert suppress == []
    assert settings.matlab_version == "R2026a"
    assert (options.maxdepth, options.tocfile, options.suffix) == (4, "index", "rst")
    assert (options.group, options.page_size) == ("namespace", 100)
    assert options.private is False
    assert options.remove_old


@pytest.mark.parametrize(
    ("conf", "message"),
    [
        (
            'matlab_apidoc_separate = "yes"',
            "matlab_apidoc_separate must be bool, not 'yes'",
        ),
        (
            "matlab_apidoc_maxdepth = True",
            "matlab_apidoc_maxdepth must be int, not True",
        ),
        (
            "matlab_apidoc_remove_old = 0",
            "matlab_apidoc_remove_old must be bool, not 0",
        ),
        (
            'matlab_apidoc_tocfile = "a/b"',
            "matlab_apidoc_tocfile 'a/b' must be a file name",
        ),
        (
            'matlab_apidoc_suffix = "."',
            "matlab_apidoc_suffix is not a configuration value",
        ),
        (
            "matlab_apidoc_output_dir = 3",
            "matlab_apidoc_output_dir must be str or None",
        ),
        (
            'matlab_src_include_patterns = "*.m"',
            "matlab_src_include_patterns must be a list",
        ),
        (
            'matlab_src_include_patterns = ["/abs/*.m"]',
            "matlab_src_include_patterns: '/abs/*.m' must be relative",
        ),
        (
            'matlab_src_include_patterns = ["a\\\\b.m"]',
            "matlab_src_include_patterns: 'a\\\\b.m' must use '/'",
        ),
        (
            'matlab_src_include_patterns = ["**/../x"]',
            "leaves matlab_src_code_project_root",
        ),
        (
            'matlab_src_exclude_patterns = ["../x"]',
            "matlab_src_exclude_patterns: '../x' leaves",
        ),
        ('matlab_src_encoding = "rot13"', "matlab_src_encoding 'rot13' is not a known"),
        ('matlab_version = "R2020a"', "error: matlab_version R2020a"),
        ('matlab_version = "2026a"', "error: matlab_version must"),
        ("matlab_namelengthmax = 100", "matlab_namelengthmax"),
        (
            'matlab_apidoc_group = "package"',
            "matlab_apidoc_group must be 'namespace' or 'folder', not 'package'",
        ),
        (
            "matlab_apidoc_page_size = 0",
            "matlab_apidoc_page_size must be 1 or more, not 0",
        ),
        (
            "matlab_apidoc_page_size = 1.5",
            "matlab_apidoc_page_size must be int, not 1.5",
        ),
        (
            'matlab_apidoc_private = "yes"',
            "matlab_apidoc_private must be bool, not 'yes'",
        ),
        ('matlab_apidoc_templatedir = "missing"', "matlab_apidoc_templatedir '"),
        (
            "matlab_apidoc_seperate = True",
            "matlab_apidoc_seperate is not a configuration value (did you mean "
            "matlab_apidoc_separate?)",
        ),
        ("matlab_zzz = 1", "matlab_zzz is not a configuration value. Correct"),
        ('raise RuntimeError("boom")', "RuntimeError: boom"),
    ],
)
def test_conf_errors_name_the_config_value(tmp_path, capsys, conf, message):
    docs = conf_project(tmp_path, f'matlab_apidoc_output_dir = "api"\n{conf}\n')
    assert main(["-q", "-c", str(docs)]) == 2
    captured = capsys.readouterr()
    assert message in captured.err
    assert captured.out == ""
    assert not (docs / "api").exists()


def test_unknown_names_are_named_together(tmp_path, capsys):
    conf = 'matlab_apidoc_output_dir = "api"\nmatlab_aaa = 2\n'
    docs = conf_project(tmp_path, f"{conf}matlab_zzz = 'txt'\n")
    assert main(["-q", "-c", str(docs)]) == 2
    err = capsys.readouterr().err
    assert "matlab_aaa is not a configuration value" in err
    assert "; matlab_zzz is not a configuration value" in err


def test_build_only_values_are_accepted(tmp_path):
    conf = 'matlab_auto_link = "all"\n_matlab_helper = 1\n'
    docs = conf_dir(tmp_path / "docs", tmp_path / "out", conf)
    assert main(["-q", "-c", docs]) == 0


@pytest.mark.parametrize(
    ("conf", "root", "message"),
    [
        ("", "../src", "matlab_apidoc_output_dir is required in conf.py."),
        ('matlab_apidoc_output_dir = "api"\n', "../missing", "is not a folder"),
        (
            'matlab_apidoc_output_dir = "api"\n',
            3,
            "matlab_src_code_project_root must be a str or None, not 3.",
        ),
    ],
)
def test_conf_without_output_or_root(tmp_path, capsys, conf, root, message):
    docs = conf_project(tmp_path, conf, root=root)
    assert main(["-q", "-c", str(docs)]) == 2
    err = capsys.readouterr().err
    assert message in err
    assert "matlab_" in err


def test_conf_dir_needs_conf_py(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["-q"]) == 2
    assert "-c '.' has no conf.py" in capsys.readouterr().err
    (tmp_path / "conf.py").write_text("")
    assert main(["-q"]) == 2
    err = capsys.readouterr().err
    assert "matlab_src_code_project_root is required in conf.py." in err


def test_cli_defaults_match_the_build(make_app, project):
    def ours(options):
        return {
            name: (opt.default, opt.rebuild)
            for name, opt in options.items()
            if name.startswith("matlab_")
        }

    build = ours(make_app(srcdir=project).config._options)
    assert build == ours(_cli.read_conf(str(project))._options)
    assert set(build) == set(CONFIG)


# --- POSIX-only names -------------------------------------------------------


@pytest.mark.skipif(os.name == "nt", reason="needs device names")
def test_device_names_and_case_collisions(tmp_path, caplog_sphinx):
    if _case_insensitive(tmp_path):
        pytest.skip("needs a case-sensitive file system")
    write(
        tmp_path / "src",
        {
            "aux/f.m": FUNCTION.format(name="f"),
            "Utils/g.m": FUNCTION.format(name="g"),
            "utils/h.m": FUNCTION.format(name="h"),
        },
    )
    out = tmp_path / "out"
    run(tmp_path / "src", out)
    assert sorted(tree(out)) == [
        "index.rst",
        "utils/index.rst",
        "~55tils/index.rst",
        "~61ux/index.rst",
    ]
    assert any("differ only by case" in m for _, m in caplog_sphinx)


@pytest.mark.skipif(
    os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="needs POSIX permissions",
)
def test_unreadable_file_is_left_out(tmp_path, caplog_sphinx):
    write(tmp_path, {"ok.m": FUNCTION.format(name="ok"), "locked.m": "x\n"})
    (tmp_path / "locked.m").chmod(0)
    try:
        page = {p.docname: p for p in pages_of(tmp_path)}["root"]
    finally:
        (tmp_path / "locked.m").chmod(0o644)
    listed = [e["ref"] for _, entries in page.context["sections"] for e in entries]
    assert listed == ["ok.m"]
    assert any("locked.m could not be read" in m for _, m in caplog_sphinx)


class ComponentHandler(mat_handlers.Handler):
    """A file type without an autodoc directive."""

    extension = ".ssc"

    def classify(self, path, text=None):
        return "component"


def test_kind_without_a_directive_is_left_out(tmp_path, monkeypatch, caplog_sphinx):
    monkeypatch.setattr(mat_handlers, "_HANDLERS", dict(mat_handlers._HANDLERS))
    mat_handlers.register(ComponentHandler())
    write(tmp_path, {"ok.m": FUNCTION.format(name="ok"), "valve.ssc": "x\n"})
    page = {p.docname: p for p in pages_of(tmp_path)}["root"]
    listed = [e["ref"] for _, entries in page.context["sections"] for e in entries]
    assert listed == ["ok.m"]
    assert any("no directive documents a component" in m for _, m in caplog_sphinx)


# --- builds of the generated pages ------------------------------------------


def _inventory(app):
    with open(app.outdir / "objects.inv", "rb") as f:
        inventory = InventoryFile.load(cast(Any, f), "", posixpath_join)
    data = getattr(inventory, "data", inventory)
    names = [
        name
        for role, items in data.items()
        if role.startswith("mat:")
        for name in items
    ]
    return names


def posixpath_join(*parts):
    return "/".join(parts)


def expected_objects(root):
    """Inventory names of every indexed file except hidden and ``unknown`` ones:
    class folder methods under their class.
    """
    source_index = build_index(IndexSettings(str(root)))
    methods = _generate.class_folder_methods(source_index)
    out = []
    for record in source_index.index.values():
        ref = record["reference"]
        if is_hidden(ref) or record["type"] == "unknown":
            continue
        if ref in methods:
            folder, _, name = ref.rpartition("/")
            cls = mat_types.class_file_reference(f"{folder}/")
            out.append(f"{cls}.{name.rsplit('.', 1)[0]}")
        else:
            out.append(ref)
    return out


@pytest.mark.parametrize("group", ["namespace", "folder"])
@pytest.mark.parametrize("separate", [False, True])
def test_build_of_the_generated_pages(make_app, project, separate, group):
    with open(project / "conf.py", "a", encoding="utf-8") as conf:
        conf.write('matlab_apidoc_output_dir = "."\n')
        conf.write(f"matlab_apidoc_separate = {separate}\n")
        conf.write(f"matlab_apidoc_group = {group!r}\n")
    assert main(["-q", "-c", str(project)]) == 0
    app = make_app(
        srcdir=project, confoverrides={"suppress_warnings": ["mat.not_callable"]}
    )
    app.build(force_all=True)
    assert app.warning.getvalue() == ""
    names = _inventory(app)
    assert len(names) == len(set(names))
    expected = expected_objects(project)
    assert len(expected) == 25
    expected = [ref for ref in expected if "/private/" not in f"/{ref}"]
    assert len(expected) == 22
    assert set(expected) <= set(names)
    assert "@Bad/bad_fn.m" in names
    assert not any(name.startswith("@Bad/Other.m.") for name in names)

    # Idempotent: nothing is written, nothing is read again.
    assert main(["-q", "-f", "-c", str(project)]) == 0
    again = make_app(
        srcdir=project, confoverrides={"suppress_warnings": ["mat.not_callable"]}
    )
    again.build()
    assert list(again.env.get_domain("mat").read_docnames) == []


# --- worked example (examples/apidoc) ----------------------------------------


def test_example_is_up_to_date(tmp_path):
    dst = tmp_path / "example"
    shutil.copytree(EXAMPLE, dst, ignore=shutil.ignore_patterns("_build", "api"))
    assert main(["-q", "-c", str(dst / "docs")]) == 0
    assert tree(dst / "docs" / "api") == tree(EXAMPLE / "docs" / "api")
    # --check writes nothing, so it can run on the committed example.
    assert main(["-q", "--check", "-c", str(EXAMPLE / "docs")]) == 0


def test_example_script_writes_the_same_pages(tmp_path, monkeypatch, capsys):
    out = tmp_path / "api"
    monkeypatch.setattr(sys, "argv", ["make_api.py", str(out)])
    runpy.run_path(str(EXAMPLE / "make_api.py"), run_name="__main__")
    assert tree(out) == tree(EXAMPLE / "docs" / "api")
    assert capsys.readouterr().out.startswith(f"{len(tree(out))} pages: ")


def test_example_builds(make_app, tmp_path):
    # The example's Markdown sidecar doc needs myst-parser (not in the Sphinx dev job).
    pytest.importorskip("myst_parser")
    dst = tmp_path / "example"
    shutil.copytree(EXAMPLE, dst, ignore=shutil.ignore_patterns("_build"))
    app = make_app(srcdir=dst / "docs")
    app.build(force_all=True)
    assert app.warning.getvalue() == ""
    names = _inventory(app)
    assert "+demo/@Shape/Shape.m.area" in names
    # Namespace grouping leaves private/ out.
    assert "utils/private/check_range.m" not in names


def test_example_in_folder_grouping_builds(make_app, tmp_path):
    # Folder grouping, default templates: sidecar docs get pages of their
    # own, and +demo/README.md introduces the folder's page.
    pytest.importorskip("myst_parser")
    dst = tmp_path / "example"
    shutil.copytree(EXAMPLE, dst, ignore=shutil.ignore_patterns("_build", "api"))
    conf = dst / "docs" / "conf.py"
    text = conf.read_text(encoding="utf-8").replace(
        'matlab_apidoc_templatedir = "../templates"\n', FOLDER
    )
    conf.write_text(text, encoding="utf-8")
    assert main(["-q", "-c", str(dst / "docs")]) == 0
    pages = sorted(tree(dst / "docs" / "api"))
    assert "+demo/getting-started-md.rst" in pages
    assert "utils/private/index.rst" in pages
    demo = (dst / "docs" / "api" / "+demo" / "index.rst").read_text(encoding="utf-8")
    assert ".. mat:autosidecar:: +demo/README.md\n   :no-title:\n" in demo
    app = make_app(srcdir=dst / "docs")
    app.build(force_all=True)
    assert app.warning.getvalue() == ""
    assert "utils/private/check_range.m" in _inventory(app)


def test_example_api_check_reports(make_app, tmp_path):
    # docs/user-guide/api-check.rst shows these reports.
    pytest.importorskip("myst_parser")
    dst = tmp_path / "example"
    shutil.copytree(EXAMPLE, dst, ignore=shutil.ignore_patterns("_build"))
    app = make_app("matlab-api-check", srcdir=dst / "docs", freshenv=True)
    app.build()
    assert app.statuscode == 1
    out = Path(app.outdir)
    report = (out / "api-check.json").read_text(encoding="utf-8")
    assert report == (EXAMPLE / "api-check.json").read_text(encoding="utf-8")
    # Locations are absolute; the committed copy is relative to docs/.
    text = (out / "api-check.txt").read_text(encoding="utf-8")
    text = text.replace(str(dst / "src") + os.sep, "../src/").replace("\\", "/")
    assert text == (EXAMPLE / "api-check.txt").read_text(encoding="utf-8")
