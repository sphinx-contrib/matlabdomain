"""test_domain_lifecycle.py.

Test that MATLAB domain state is env-owned and follows the Sphinx lifecycle:
environment pickling, cache reuse on rebuild, clear_doc and merge_domaindata.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import io
import itertools
import os
import pickle
import shutil
import time
from typing import Any, cast

import pytest
import sphinx.util.parallel
from sphinx.environment import CONFIG_OK
from sphinx.util import console
from tree_sitter import Node, Parser, Tree

from sphinxcontrib import mat_types
from sphinxcontrib.matlab import MATLABDomain

strip_escape_sequences = cast(Any, console).strip_escape_sequences


@pytest.fixture
def srcdir(rootdir, tmp_path):
    # Copy so tests can edit sources and reuse the pickled environment.
    dst = tmp_path / "test_classfolder"
    shutil.copytree(
        rootdir / "roots" / "test_classfolder",
        dst,
        ignore=shutil.ignore_patterns("_build"),
    )
    return dst


@pytest.fixture
def parsed(monkeypatch):
    """Record every .m file actually parsed with tree-sitter."""
    calls = []
    original = mat_types.MatObject.parse_mfile

    def counting_parse_mfile(mfile, *args, **kwargs):
        calls.append(mfile)
        return original(mfile, *args, **kwargs)

    monkeypatch.setattr(
        mat_types.MatObject, "parse_mfile", staticmethod(counting_parse_mfile)
    )
    return calls


def build(make_app, srcdir, **confoverrides):
    app = make_app(srcdir=srcdir, confoverrides=confoverrides)
    app.build()
    return app


def find_class(table, name):
    (cls,) = {
        id(o): o
        for o in table.values()
        if isinstance(o, mat_types.MatClass) and o.name == name
    }.values()
    return cls


def doctree_text(app, docname):
    return pickle.loads((app.doctreedir / f"{docname}.doctree").read_bytes()).astext()


def read_docs(app):
    return sorted(app.env.get_domain("mat").read_docnames)


# The files the three pages use: each class folder, as a unit.
USED = [
    "@First/First.m",
    "@First/method_in_folder.m",
    "src/+pkg/@Third/Third.m",
    "src/+pkg/@Third/method_in_folder.m",
    "src/@Second/Second.m",
    "src/@Second/method_in_folder.m",
]


def used_paths(srcdir, refs=USED):
    return sorted(str(srcdir.joinpath(*ref.split("/"))) for ref in refs)


def test_initial_data_layout():
    assert MATLABDomain.data_version == 30
    assert set(MATLABDomain.initial_data) == {
        "objects",
        "folders",
        "doc_sources",
        "sidecar_docs",
        "sidecar_issues",
        "xref_docs",
        "described",
        "index",
        "sidecars",
        "simulink_docs",
        "parse_cache",
        "parse_warnings",
        "entities_table",
        "matlab_names",
        "in_step",
        "api_pages",
    }


def test_source_state_is_env_owned(make_app, srcdir):
    app = build(make_app, srcdir)
    data = app.env.domaindata["mat"]
    dom = app.env.get_domain("mat")

    assert dom.entities_table is data["entities_table"]

    # Every file is indexed; only the files the pages use are parsed.
    m_files = sorted(str(p) for p in srcdir.rglob("*.m"))
    assert sorted(data["index"]) == m_files
    assert sorted(key[0] for key in data["parse_cache"]) == used_paths(srcdir)
    for path, entry in data["index"].items():
        st = os.stat(path)
        assert (entry["mtime"], entry["size"]) == (st.st_mtime_ns, st.st_size)
        if path in used_paths(srcdir):
            assert data["parse_cache"][path, st.st_mtime_ns, st.st_size] is not None
    second = srcdir / "src" / "@Second" / "Second.m"
    assert data["index"][str(second)] == {
        "reference": "src/@Second/Second.m",
        "type": "class",
        "mtime": os.stat(second).st_mtime_ns,
        "size": os.stat(second).st_size,
        "warnings": [],
        "unreadable": False,
        "help_only": False,
        "matlab_name": "Second",
        "private": False,
        "scope": "src/",
    }
    method_file = str(srcdir / "src" / "@Second" / "method_in_folder.m")
    assert data["index"][method_file]["type"] == "function"
    assert data["doc_sources"]["index_second"] == {
        path: (data["index"][path]["mtime"], data["index"][path]["size"])
        for path in used_paths(srcdir, USED[4:])
    }


def test_lazy_build_parses_only_used_files(make_app, srcdir, parsed):
    build(make_app, srcdir)
    assert sorted(parsed) == used_paths(srcdir)


def test_env_pickle_has_no_tree_sitter_objects(make_app, srcdir):
    app = build(make_app, srcdir)

    seen = []

    class CheckingPickler(pickle.Pickler):
        def reducer_override(self, obj):
            if isinstance(obj, (Node, Tree, Parser)):
                seen.append(obj)
            return NotImplemented

    CheckingPickler(io.BytesIO()).dump(app.env)
    assert seen == []

    data = pickle.loads(pickle.dumps(app.env)).domaindata["mat"]
    second = find_class(data["entities_table"], "Second")
    assert sorted(second.methods) == [
        "Second",
        "method_in_folder",
        "method_inside_classdef",
    ]
    assert second.methods["method_in_folder"].cls is second
    assert (
        second.docstring
        == find_class(app.env.get_domain("mat").entities_table, "Second").docstring
    )


def test_rebuild_without_changes_does_not_reparse(make_app, srcdir, parsed):
    app1 = build(make_app, srcdir)
    assert sorted(parsed) == used_paths(srcdir)
    first_text = doctree_text(app1, "index_second")
    first_index = dict(app1.env.domaindata["mat"]["index"])

    # Unchanged sources: no page is read again.
    parsed.clear()
    app2 = build(make_app, srcdir)
    assert read_docs(app2) == []
    assert parsed == []

    # Touch only the .rst so Sphinx re-reads it with the reloaded environment.
    rst = srcdir / "index_second.rst"
    now = time.time_ns()
    os.utime(rst, ns=(now, now))

    app3 = build(make_app, srcdir)
    assert read_docs(app3) == ["index_second"]
    assert parsed == []
    assert app3.env.config_status == CONFIG_OK  # reloaded from pickle
    dom3 = app3.env.get_domain("mat")
    assert app3.env.domaindata["mat"]["index"] == first_index
    assert doctree_text(app3, "index_second") == first_text
    assert sorted(find_class(dom3.entities_table, "Second").methods) == [
        "Second",
        "method_in_folder",
        "method_inside_classdef",
    ]


def test_size_change_with_preserved_mtime_reparses(make_app, srcdir, parsed):
    build(make_app, srcdir)
    mfile = srcdir / "src" / "@Second" / "Second.m"
    st = os.stat(mfile)
    mfile.write_text(
        mfile.read_text().replace("% The second class", "% The changed second class")
    )
    os.utime(mfile, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert os.stat(mfile).st_mtime_ns == st.st_mtime_ns
    assert os.stat(mfile).st_size != st.st_size

    parsed.clear()
    app2 = build(make_app, srcdir)
    # Only the page that uses the file is read again; only the file is parsed.
    assert read_docs(app2) == ["index_second"]
    assert parsed == [str(mfile)]
    assert "The changed second class" in doctree_text(app2, "index_second")
    second = find_class(app2.env.get_domain("mat").entities_table, "Second")
    assert "The changed second class" in second.docstring
    # The class was reparsed; folder methods are re-attached exactly once.
    assert sorted(second.methods) == [
        "Second",
        "method_in_folder",
        "method_inside_classdef",
    ]


def test_editing_an_unused_file_reads_nothing(make_app, srcdir, parsed):
    build(make_app, srcdir)
    unused = srcdir / "@First" / "private" / "method_in_private.m"
    unused.write_text(unused.read_text() + "\n% edited\n")

    parsed.clear()
    app2 = build(make_app, srcdir)
    assert read_docs(app2) == []
    assert parsed == []


def test_added_file_rereads_pages_without_parsing(make_app, srcdir, parsed):
    build(make_app, srcdir)
    (srcdir / "src" / "added.m").write_text("function added\nend\n")

    parsed.clear()
    app2 = build(make_app, srcdir)
    # New names may change what the pages resolve: every page is read again,
    # with the parsed files reused.
    assert read_docs(app2) == ["index_first", "index_second", "index_third"]
    assert parsed == []


def test_removed_folder_method_not_kept_on_reused_class(make_app, srcdir, parsed):
    build(make_app, srcdir)
    (srcdir / "src" / "@Second" / "method_in_folder.m").unlink()

    parsed.clear()
    app2 = build(make_app, srcdir)
    assert parsed == []
    assert "index_second" in read_docs(app2)
    second = find_class(app2.env.get_domain("mat").entities_table, "Second")
    assert sorted(second.methods) == ["Second", "method_inside_classdef"]


def test_removed_class_file_turns_folder_methods_into_functions(
    make_app, srcdir, parsed
):
    app = build(make_app, srcdir)
    method = "src/@Second/method_in_folder.m"
    assert type(app.env.get_domain("mat").entities_table[method]) is mat_types.MatMethod
    (srcdir / "src" / "@Second" / "Second.m").unlink()

    parsed.clear()
    app2 = build(make_app, srcdir)
    dom = app2.env.get_domain("mat")
    # Reused from the parse cache, and no longer a method of the class.
    assert type(mat_types.resolve(dom, method)) is mat_types.MatFunction
    assert parsed == []


def test_config_change_invalidates_parse_cache(make_app, srcdir, parsed):
    build(make_app, srcdir)
    parsed.clear()
    build(make_app, srcdir, matlab_show_property_default_value=False)
    assert sorted(parsed) == used_paths(srcdir)


# data_version of the commits that cached block-comment docstrings (59016b1).
DOCSTRING_CACHE_VERSION_BEFORE_HELP_FIX = 5


@pytest.mark.parametrize("older", [True, False], ids=["older_version", "same_version"])
def test_older_domain_data_version_drops_cached_docstrings(
    make_app, tmp_path, parsed, older
):
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "."\n'
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n.. mat:autofunction:: up_blk\n"
    )
    (tmp_path / "up_blk.m").write_text("%{\nBLOCK BODY\n%}\nfunction up_blk\nend\n")
    app1 = build(make_app, tmp_path)
    assert "BLOCK BODY" not in (app1.outdir / "index.html").read_text()

    # Leave the pickled environment as an earlier release would have: a
    # cached object with an outdated docstring, under the previous version.
    data = app1.env.domaindata["mat"]
    (cached,) = (o for o in data["parse_cache"].values() if o.name == "up_blk")
    cached.docstring = "STALE DOCSTRING"
    if older:
        data["version"] = DOCSTRING_CACHE_VERSION_BEFORE_HELP_FIX
    with open(app1.doctreedir / "environment.pickle", "wb") as f:
        pickle.dump(app1.env, f, pickle.HIGHEST_PROTOCOL)
    rst = tmp_path / "index.rst"
    future = os.stat(rst).st_mtime_ns + 10**10
    os.utime(rst, ns=(future, future))

    parsed.clear()
    app2 = build(make_app, tmp_path)
    html = (app2.outdir / "index.html").read_text()
    if older:
        assert "STALE DOCSTRING" not in html
        assert parsed == [str(tmp_path / "up_blk.m")]
        (fresh,) = (
            o
            for o in app2.env.domaindata["mat"]["parse_cache"].values()
            if o.name == "up_blk"
        )
        assert fresh.docstring.strip() == "{"
    else:
        # Same version: the cache is trusted, so the control shows the test can
        # see stale data.
        assert "STALE DOCSTRING" in html
        assert parsed == []


# data_version before matlab_src_encoding and the ISO-8859-1 fallback (836e94e).
CACHE_VERSION_BEFORE_ENCODING = 6


@pytest.mark.parametrize(
    "version", [CACHE_VERSION_BEFORE_ENCODING, 7, MATLABDomain.data_version]
)
def test_older_domain_data_version_drops_misdecoded_docstrings(
    make_app, tmp_path, parsed, version
):
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "."\n'
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n.. mat:autofunction:: up_lat\n"
    )
    mfile = tmp_path / "up_lat.m"
    mfile.write_bytes("function up_lat\n% LATIN café\nend\n".encode("latin-1"))
    app1 = build(make_app, tmp_path)
    assert "LATIN café" in (app1.outdir / "index.html").read_text(encoding="utf-8")

    # Leave the cached object as 836e94e left it: a misdecoded docstring
    # (there: backslash escapes), no recorded warnings.
    data = app1.env.domaindata["mat"]
    (cached,) = (o for o in data["parse_cache"].values() if o.name == "up_lat")
    cached.docstring = "LATIN MISDECODED"
    del cached.source_warnings
    data["index"][str(mfile)]["warnings"] = []
    data["version"] = version
    with open(app1.doctreedir / "environment.pickle", "wb") as f:
        pickle.dump(app1.env, f, pickle.HIGHEST_PROTOCOL)
    rst = tmp_path / "index.rst"
    future = os.stat(rst).st_mtime_ns + 10**10
    os.utime(rst, ns=(future, future))

    parsed.clear()
    app2 = build(make_app, tmp_path)
    html = (app2.outdir / "index.html").read_text(encoding="utf-8")
    if version < MATLABDomain.data_version:
        assert parsed == [str(mfile)]
        assert "LATIN café" in html
        assert "[mat.encoding]" in app2.warning.getvalue()
    else:
        # Same version: the cache is trusted (the control).
        assert parsed == []
        assert "LATIN MISDECODED" in html
        assert "[mat.encoding]" not in app2.warning.getvalue()


SOURCE_STATE = (
    "index",
    "sidecars",
    "simulink_docs",
    "parse_cache",
    "parse_warnings",
    "entities_table",
    "matlab_names",
)


def test_clear_doc_only_removes_that_doc(make_app, srcdir):
    app = build(make_app, srcdir)
    dom = app.env.get_domain("mat")
    data = dom.data
    source_state = {k: dict(data[k]) for k in SOURCE_STATE}
    docs = {fn for fn, _, _ in data["objects"].values()}
    assert {"index_first", "index_second", "index_third"} <= docs
    kept = {k: v for k, v in data["objects"].items() if v[0] != "index_second"}
    kept_sources = {k: v for k, v in data["doc_sources"].items() if k != "index_second"}
    assert set(kept_sources) == {"index_first", "index_third"}

    dom.clear_doc("index_second")

    assert data["objects"] == kept
    assert data["doc_sources"] == kept_sources
    assert all(fn != "index_second" for fn, _, _, _ in data["folders"].values())
    for k, v in source_state.items():
        assert data[k] == v


def test_merge_domaindata_filters_by_docnames(make_app, srcdir):
    app = build(make_app, srcdir)
    dom = app.env.get_domain("mat")
    data = dom.data
    unchanged = {
        k: dict(data[k])
        for k in ("index", "sidecars", "entities_table", "matlab_names")
    }
    before = dict(data["objects"])
    ours = dict(data["parse_cache"])
    current, stale, unused = (
        str(srcdir.joinpath(*ref.split("/")))
        for ref in (
            "src/@Second/Second.m",
            "@First/First.m",
            "@First/dlls/mexfunction.m",
        )
    )
    key = {
        p: (p, data["index"][p]["mtime"], data["index"][p]["size"])
        for p in (current, stale, unused)
    }
    worker_object, warning = object(), [("invalid_matlab", "x", None)]
    otherdata = {
        "objects": {
            "a/Obj.m": ("doc_a", "class", "Obj"),
            "b/Obj.m": ("doc_b", "class", "Obj"),
        },
        "folders": {
            "a/": ("doc_a", "", "", False),
            "b/": ("doc_b", "", "", False),
        },
        "doc_sources": {"doc_a": {unused: key[unused][1:]}, "doc_b": {}},
        "sidecar_docs": {"doc_a": {"a/guide.md": "A"}, "doc_b": {"b/guide.md": "B"}},
        "sidecar_issues": {"doc_a": [], "doc_b": [("b/guide.md", "link", "x", 1)]},
        "xref_docs": {"doc_a": True, "doc_b": True},
        "described": {
            "doc_a": {"a/Obj.m": (3, "class", "Obj", None)},
            "doc_b": {"b/Obj.m": (5, "class", "Obj", None)},
        },
        "index": {"/elsewhere/x.m": {}},
        "sidecars": {"/elsewhere/guide.md": {}},
        "parse_cache": {
            key[current]: worker_object,  # we have it already
            (stale, 0, 0): worker_object,  # not the current file
            key[unused]: worker_object,  # new
            ("/elsewhere/x.m", 0, 0): worker_object,  # not indexed
        },
        "parse_warnings": {key[unused]: warning, (stale, 0, 0): warning},
        "entities_table": {"x.m": object()},
        "matlab_names": {"x": ["x.m"]},
    }

    dom.merge_domaindata({"doc_a"}, otherdata)

    assert data["objects"] == {**before, "a/Obj.m": ("doc_a", "class", "Obj")}
    assert data["folders"]["a/"] == ("doc_a", "", "", False)
    assert "b/" not in data["folders"]
    assert data["doc_sources"]["doc_a"] == {unused: key[unused][1:]}
    assert "doc_b" not in data["doc_sources"]
    assert data["sidecar_docs"] == {"doc_a": {"a/guide.md": "A"}}
    assert data["sidecar_issues"] == {"doc_a": []}
    assert "doc_a" in data["xref_docs"]
    assert "doc_b" not in data["xref_docs"]
    assert data["described"]["doc_a"] == {"a/Obj.m": (3, "class", "Obj", None)}
    assert "doc_b" not in data["described"]
    assert dom.sidecar_doc("a/guide.md") == "doc_a"
    assert dom.sidecar_doc("b/guide.md") is None
    # Parses of current files that we lack are adopted; ours are kept.
    assert data["parse_cache"] == {**ours, key[unused]: worker_object}
    assert data["parse_warnings"][key[unused]] == warning
    assert (stale, 0, 0) not in data["parse_warnings"]
    for k, v in unchanged.items():
        assert data[k] == v


def test_note_object(make_app, srcdir):
    app = build(make_app, srcdir)
    dom = app.env.get_domain("mat")
    app.env.temp_data["docname"] = "index_first"

    dom.note_object("some/Thing.m", "class", "Thing")
    assert dom.data["objects"]["some/Thing.m"] == ("index_first", "class", "Thing")
    # Without a location (a folder) it is noted without a line: never warned
    # about by check_consistency or reconcile.
    entry = dom.data["described"]["index_first"]["some/Thing.m"]
    assert entry == (None, "class", "Thing", None)

    warnings_before = app.warning.getvalue()
    dom.note_object("some/Thing.m", "function", "Thing")
    dom.note_object("some/Thing.m", "class", "Thing", location=("index_first", 3))
    assert app.warning.getvalue() == warnings_before  # the same page
    entry = dom.data["described"]["index_first"]["some/Thing.m"]
    assert entry == (3, "class", "Thing", None)

    # index_first sorts first and was read by this process: a later page warns.
    app.env.temp_data["docname"] = "zz_page"
    dom.note_object("some/Thing.m", "class", "Thing", location=("zz_page", 5))
    warning = app.warning.getvalue()
    assert "duplicate object description of some/Thing.m" in warning
    assert "[mat.duplicate]" in warning
    assert dom.data["objects"]["some/Thing.m"] == ("zz_page", "class", "Thing")


def _worker(docname, objects=(), folders=(), line=7):
    """Domain data of a parallel-read worker that read ``docname``; its object
    descriptions are at ``line`` (folders: None).
    """
    data = {name: {} for name in MATLABDomain.initial_data}
    data["objects"] = {ref: (docname, *entry) for ref, *entry in objects}
    data["folders"] = {ref: (docname, *entry) for ref, *entry in folders}
    folder_data = {ref: tuple(entry) for ref, *entry in folders}
    data["described"] = {
        docname: {
            ref: (
                None if ref in folder_data else line,
                objtype,
                display,
                folder_data.get(ref),
            )
            for ref, objtype, display in objects
        }
    }
    return data


def _merge_in_order(make_app, srcdir, workers, order):
    """Merge ``workers`` (docname -> data) in ``order``, each as one chunk,
    after a build that read them in name order, as Sphinx does after clearing
    them.
    """
    app = build(make_app, srcdir)
    dom = app.env.get_domain("mat")
    dom.read_docnames = [*dom.read_docnames, *sorted(workers)]
    app.warning.truncate(0)
    app.warning.seek(0)
    for docname in order:
        dom.merge_domaindata({docname}, workers[docname])
    dom.reconcile()  # env-updated
    dom.check_consistency()
    # "<SRC>/doc.rst" on every OS (Windows writes the paths with "\").
    warnings = [
        line.replace(str(srcdir), "<SRC>").replace("<SRC>\\", "<SRC>/")
        for line in strip_escape_sequences(app.warning.getvalue()).splitlines()
        if "[mat.duplicate]" in line
    ]
    return dom, sorted(warnings)


def test_merge_duplicate_object_like_serial(make_app, srcdir):
    # A serial build reads doc_a, doc_b, doc_c in this order: the last one
    # wins and each later description warns about the one before it.
    workers = {
        doc: _worker(doc, [("x/Obj.m", "class", "Obj")])
        for doc in ("doc_a", "doc_b", "doc_c")
    }
    expected = [
        f"<SRC>/{later}.rst:7: WARNING: [sphinxcontrib-matlabdomain] duplicate "
        f"object description of x/Obj.m, other instance in <SRC>/{earlier}.rst, "
        "use :no-index: for one of them [mat.duplicate]"
        for earlier, later in (("doc_a", "doc_b"), ("doc_b", "doc_c"))
    ]
    for order in itertools.permutations(workers):
        dom, warnings = _merge_in_order(make_app, srcdir, workers, order)
        assert dom.data["objects"]["x/Obj.m"] == ("doc_c", "class", "Obj"), order
        assert warnings == expected, order


def test_merge_duplicate_folder_like_serial(make_app, srcdir):
    # A folder may be described twice without a warning; the last one wins.
    workers = {
        doc: _worker(
            doc,
            [("x/", "folder", "x/")],
            [("x/", f"from {doc}", "", False)],
        )
        for doc in ("doc_a", "doc_b")
    }
    for order in itertools.permutations(workers):
        dom, warnings = _merge_in_order(make_app, srcdir, workers, order)
        assert dom.data["objects"]["x/"] == ("doc_b", "folder", "x/"), order
        assert dom.data["folders"]["x/"] == ("doc_b", "from doc_b", "", False)
        assert warnings == [], order


def test_merge_order_does_not_change_matches(make_app, srcdir):
    # ``:any:`dup``` takes its role (a CSS class of a chooser link) from the
    # first match.
    workers = {
        "doc_a": _worker("doc_a", [("a/dup.m", "function", "dup")]),
        "doc_b": _worker("doc_b", [("b/dup.m", "class", "dup")]),
    }
    for order in itertools.permutations(workers):
        dom, _ = _merge_in_order(make_app, srcdir, workers, order)
        matches = dom.find_obj(None, None, "dup", None)
        assert [ref for ref, _ in matches] == ["a/dup.m", "b/dup.m"], order


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__)])


# --- duplicate warnings of real serial and -j builds ---------------------------

DUPLICATE_CONF = (
    'extensions = ["sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "src"\n'
    'project = "dup"\n'
)
DUPLICATE_SOURCES = {
    "src/f.m": "function y = f(x)\n% F help\ny = x;\nend\n",
    "src/h.m": "function y = h(x)\n% H help\ny = x;\nend\n",
    "src/K.m": "classdef K\n% K help\nmethods\nfunction m(o)\n% M help\nend\n"
    "end\nend\n",
}
# Sorted, as Sphinx reads them: -j 2 reads a1-a6, then b1-b5 and index, then
# zz (13 documents, more than the 5 below which Sphinx 8.0 reads serially).
# Two processes read three chunks: the third is forked after one of the
# others was merged, so its copy of the domain data holds that chunk.
DUPLICATE_PAGES = {
    # (1) a hand-written directive in both chunks
    "a1.rst": "A1\n==\n\n.. mat:function:: g(x)\n\n   G.\n",
    "b1.rst": "B1\n==\n\nText.\n\n.. mat:function:: g(x)\n\n   G again.\n",
    # (2) an auto directive in both chunks
    "a2.rst": "A2\n==\n\n.. mat:autofunction:: f\n",
    "b2.rst": "B2\n==\n\nSome text.\n\nMore text.\n\n.. mat:autofunction:: f\n",
    # (3) three descriptions, two of them in one chunk
    "a3.rst": "A3\n==\n\n.. mat:autofunction:: h\n",
    "b3.rst": "B3\n==\n\nText.\n\n.. mat:autofunction:: h\n",
    "b4.rst": "B4\n==\n\nOne.\n\nTwo.\n\n.. mat:function:: h(x)\n\n   H again.\n",
    # (4) a class with its members in both chunks
    "a4.rst": "A4\n==\n\n.. mat:autoclass:: K\n   :members:\n",
    "b5.rst": "B5\n==\n\nText.\n\n.. mat:autoclass:: K\n   :members:\n",
    # (5) its third description, in the third chunk
    "zz.rst": "ZZ\n==\n\nOne.\n\nTwo.\n\n.. mat:autoclass:: K\n   :members:\n",
    "a5.rst": "A5\n==\n\nText.\n",
    "a6.rst": "A6\n==\n\nText.\n",
    "index.rst": "Index\n=====\n\n.. toctree::\n\n"
    + "".join(f"   {doc}\n" for doc in ("a1", "a2", "a3", "a4", "a5", "a6"))
    + "".join(f"   {doc}\n" for doc in ("b1", "b2", "b3", "b4", "b5", "zz")),
}
CHUNKS = [
    ["a1", "a2", "a3", "a4", "a5", "a6"],
    ["b1", "b2", "b3", "b4", "b5", "index"],
    ["zz"],
]


def test_worker_leaves_pages_of_other_processes_to_check_consistency(make_app, srcdir):
    # A worker forked after another chunk was merged sees that chunk's
    # objects: it warns neither about them (check_consistency does) nor less
    # about its own pages and unchanged pages of an earlier build.
    app = build(make_app, srcdir)
    dom = app.env.get_domain("mat")
    old = "aa_old"  # not read again
    dom.read_docnames = ["doc_a", "doc_b", "doc_c"]
    dom.described_here = set()
    described = dom.data["described"]
    described["doc_a"] = {"x/Obj.m": (2, "class", "Obj", None)}  # merged chunk
    described[old] = {"x/Old.m": (2, "class", "Old", None)}
    dom._pages_of = None
    app.env.temp_data["docname"] = "doc_b"
    app.warning.truncate(0)
    app.warning.seek(0)

    dom.note_object("x/Obj.m", "class", "Obj", location=("doc_b", 4))
    assert "[mat.duplicate]" not in app.warning.getvalue()
    assert dom.data["objects"]["x/Obj.m"] == ("doc_b", "class", "Obj")

    dom.note_object("x/Old.m", "class", "Old", location=("doc_b", 6))
    assert "of x/Old.m, other instance in" in app.warning.getvalue()

    app.env.temp_data["docname"] = "doc_c"
    dom.note_object("x/Obj.m", "class", "Obj", location=("doc_c", 8))
    assert "of x/Obj.m, other instance in" in app.warning.getvalue()


def _duplicate_warnings(app, root):
    text = strip_escape_sequences(app.warning.getvalue())
    return sorted(
        line.replace(str(root), "<SRC>").replace("<SRC>\\", "<SRC>/")
        for line in text.splitlines()
        if "[mat.duplicate]" in line
    )


def _dup(later, line, ref, earlier):
    return (
        f"<SRC>/{later}.rst:{line}: WARNING: [sphinxcontrib-matlabdomain] duplicate "
        f"object description of {ref}, other instance in <SRC>/{earlier}.rst, use "
        ":no-index: for one of them [mat.duplicate]"
    )


def test_duplicate_warnings_of_parallel_build_equal_serial(
    make_app, tmp_path, monkeypatch
):
    roots = {}
    for name in ("serial", "parallel"):
        root = roots[name] = tmp_path / name
        for path, text in {
            "conf.py": DUPLICATE_CONF,
            **DUPLICATE_SOURCES,
            **DUPLICATE_PAGES,
        }.items():
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(text, encoding="utf-8")

    serial = make_app(srcdir=roots["serial"])
    serial.build()
    expected = sorted(
        [
            _dup("b1", 6, "g", "a1"),
            # an auto directive: the line of the directive on the page
            _dup("b2", 8, "f.m", "a2"),
            _dup("b3", 6, "h.m", "a3"),
            _dup("b4", 8, "h.m", "b3"),
            # the members of an autoclass: the line of the autoclass
            _dup("b5", 6, "K.m", "a4"),
            _dup("b5", 6, "K.m.m", "a4"),
            _dup("zz", 8, "K.m", "b5"),
            _dup("zz", 8, "K.m.m", "b5"),
        ]
    )
    assert _duplicate_warnings(serial, roots["serial"]) == expected

    merged = []
    original = MATLABDomain.merge_domaindata

    def recording(self, docnames, otherdata):
        merged.append(sorted(docnames))
        return original(self, docnames, otherdata)

    monkeypatch.setattr(MATLABDomain, "merge_domaindata", recording)
    parallel = make_app(srcdir=roots["parallel"], parallel=2)
    parallel.build()
    if sphinx.util.parallel.parallel_available:
        assert len(merged) == 3
        assert sorted(merged) == CHUNKS
    assert _duplicate_warnings(parallel, roots["parallel"]) == expected


def test_removed_duplicate_gives_no_warning_in_the_next_build(make_app, tmp_path):
    # b no longer describes g, and a is read again in the same build: a is
    # read first and must not warn about the description b had before.
    for path, text in {
        "conf.py": DUPLICATE_CONF,
        "src/f.m": DUPLICATE_SOURCES["src/f.m"],
        "index.rst": "Index\n=====\n\n.. toctree::\n\n   a\n   b\n",
        "a.rst": "A\n=\n\n.. mat:function:: g(x)\n\n   G.\n",
        "b.rst": "B\n=\n\n.. mat:function:: g(x)\n\n   G again.\n",
    }.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")
    first = make_app(srcdir=tmp_path)
    first.build()
    assert _duplicate_warnings(first, tmp_path) == [_dup("b", 4, "g", "a")]

    (tmp_path / "b.rst").write_text("B\n=\n\nNothing.\n", encoding="utf-8")
    later = time.time_ns() + 2_000_000_000
    for name in ("a.rst", "b.rst"):
        os.utime(tmp_path / name, ns=(later, later))
    second = make_app(srcdir=tmp_path)
    second.build()
    assert sorted(second.env.get_domain("mat").read_docnames) == ["a", "b"]
    assert _duplicate_warnings(second, tmp_path) == []


# --- incremental builds of objects described on several pages -----------------

WINNER_SOURCES = {
    "conf.py": DUPLICATE_CONF,
    "src/f.m": DUPLICATE_SOURCES["src/f.m"],
    "src/lib/u.m": DUPLICATE_SOURCES["src/h.m"],
}
WINNER_INDEX = "Index\n=====\n\nSee :mat:func:`g`.\n\n.. toctree::\n\n"
G_PAGE = "{title}\n=\n\n.. mat:function:: g(x)\n\n   G.\n"
LIB_PAGE = "{title}\n=\n\n.. mat:folder:: lib\n\nText.\n"


def _write_pages(root, pages):
    for path, text in pages.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")


def _touch(root, *names):
    later = time.time_ns() + 2_000_000_000
    for name in names:
        os.utime(root / name, ns=(later, later))


def _incremental(make_app, tmp_path, first, second, read, parallel=0):
    """Build ``first``, then the changed pages ``second`` (None deletes one)
    in the same folder, which reads exactly the documents ``read``; compare
    with a fresh build of the final sources. Return the incremental build and
    its folder.
    """
    root = tmp_path / "incremental"
    _write_pages(root, {**WINNER_SOURCES, **first})
    make_app(srcdir=root).build()
    for name, text in second.items():
        if text is None:
            (root / name).unlink()
        else:
            (root / name).write_text(text, encoding="utf-8")
    _touch(root, *(name for name, text in second.items() if text is not None))
    app = make_app(srcdir=root, parallel=parallel)
    app.build()
    assert sorted(app.env.get_domain("mat").read_docnames) == read
    fresh_root = tmp_path / "fresh"
    final = {**first, **second}
    _write_pages(
        fresh_root,
        {**WINNER_SOURCES, **{k: v for k, v in final.items() if v is not None}},
    )
    fresh = make_app(srcdir=fresh_root)
    fresh.build()
    for name in ("objects", "folders"):
        assert app.env.domaindata["mat"][name] == fresh.env.domaindata["mat"][name]
    assert _duplicate_warnings(app, root) == _duplicate_warnings(fresh, fresh_root)
    return app, root


def test_winner_page_drops_its_description(make_app, tmp_path):
    app, root = _incremental(
        make_app,
        tmp_path,
        {
            "index.rst": WINNER_INDEX + "   a\n   b\n",
            "a.rst": G_PAGE.format(title="A"),
            "b.rst": G_PAGE.format(title="B"),
        },
        {"b.rst": "B\n=\n\nNothing.\n"},
        ["b"],
    )
    assert app.env.domaindata["mat"]["objects"]["g"] == ("a", "function", "g")
    warnings = app.warning.getvalue()
    assert "target not found" not in warnings
    assert _duplicate_warnings(app, root) == []
    assert 'href="a.html#mat-g"' in (app.outdir / "index.html").read_text("utf-8")


def test_winner_page_is_deleted(make_app, tmp_path):
    app, root = _incremental(
        make_app,
        tmp_path,
        {
            "index.rst": WINNER_INDEX + "   a\n   b\n",
            "a.rst": G_PAGE.format(title="A"),
            "b.rst": G_PAGE.format(title="B"),
        },
        {"index.rst": WINNER_INDEX + "   a\n", "b.rst": None},
        ["index"],
    )
    assert app.env.domaindata["mat"]["objects"]["g"] == ("a", "function", "g")
    assert "target not found" not in app.warning.getvalue()
    assert _duplicate_warnings(app, root) == []
    assert 'href="a.html#mat-g"' in (app.outdir / "index.html").read_text("utf-8")


def test_winner_page_changes_and_keeps_its_description(make_app, tmp_path):
    app, root = _incremental(
        make_app,
        tmp_path,
        {
            "index.rst": WINNER_INDEX + "   a\n   b\n",
            "a.rst": G_PAGE.format(title="A"),
            "b.rst": G_PAGE.format(title="B"),
        },
        {"b.rst": "B\n=\n\nNew text.\n\n.. mat:function:: g(x)\n\n   G.\n"},
        ["b"],
    )
    assert app.env.domaindata["mat"]["objects"]["g"] == ("b", "function", "g")
    assert _duplicate_warnings(app, root) == [_dup("b", 6, "g", "a")]


def test_winner_page_drops_its_folder_description(make_app, tmp_path):
    app, root = _incremental(
        make_app,
        tmp_path,
        {
            "index.rst": WINNER_INDEX + "   a\n   b\n",
            "a.rst": LIB_PAGE.format(title="A"),
            "b.rst": LIB_PAGE.format(title="B"),
        },
        {"b.rst": "B\n=\n\nNothing.\n"},
        ["b"],
    )
    data = app.env.domaindata["mat"]
    assert data["folders"]["lib/"][0] == "a"
    assert data["objects"]["lib/"][0] == "a"
    assert _duplicate_warnings(app, root) == []


def test_without_shared_descriptions_only_changed_pages_are_read(make_app, tmp_path):
    _incremental(
        make_app,
        tmp_path,
        {
            "index.rst": WINNER_INDEX + "   a\n   b\n",
            "a.rst": G_PAGE.format(title="A"),
            "b.rst": "B\n=\n\n.. mat:autofunction:: f\n\n.. mat:folder:: lib\n",
        },
        {"b.rst": "B\n=\n\nMore.\n\n.. mat:autofunction:: f\n\n.. mat:folder:: lib\n"},
        ["b"],
    )


def test_earlier_page_changes_and_keeps_its_description(make_app, tmp_path):
    # Reading only a would make it the winner and warn about b.
    app, root = _incremental(
        make_app,
        tmp_path,
        {
            "index.rst": WINNER_INDEX + "   a\n   b\n",
            "a.rst": G_PAGE.format(title="A"),
            "b.rst": G_PAGE.format(title="B"),
        },
        {"a.rst": "A\n=\n\nNew text.\n\n.. mat:function:: g(x)\n\n   G.\n"},
        ["a"],
    )
    assert app.env.domaindata["mat"]["objects"]["g"] == ("b", "function", "g")
    assert _duplicate_warnings(app, root) == [_dup("b", 4, "g", "a")]


def test_page_adds_a_description_an_unchanged_later_page_has(make_app, tmp_path):
    # A fresh build reads a first: b wins and warns about a.
    app, root = _incremental(
        make_app,
        tmp_path,
        {
            "index.rst": WINNER_INDEX + "   a\n   b\n",
            "a.rst": "A\n=\n\nText.\n",
            "b.rst": "B\n=\n\nText.\n\n.. mat:function:: g(x)\n\n   G.\n",
        },
        {"a.rst": G_PAGE.format(title="A")},
        ["a"],
    )
    assert app.env.domaindata["mat"]["objects"]["g"] == ("b", "function", "g")
    assert _duplicate_warnings(app, root) == [_dup("b", 6, "g", "a")]


def test_winner_page_drops_its_description_in_a_parallel_read(
    make_app, tmp_path, monkeypatch
):
    # Seven documents read again (more than the 5 below which Sphinx 8.0
    # reads serially): the winner z and six others; a is not read.
    merged = []
    original = MATLABDomain.merge_domaindata

    def recording(self, docnames, otherdata):
        merged.append(sorted(docnames))
        return original(self, docnames, otherdata)

    monkeypatch.setattr(MATLABDomain, "merge_domaindata", recording)
    others = [f"c{i}" for i in range(1, 7)]
    first = {
        "index.rst": WINNER_INDEX + "".join(f"   {d}\n" for d in ["a", *others, "z"]),
        "a.rst": G_PAGE.format(title="A"),
        "z.rst": G_PAGE.format(title="Z"),
        **{f"{d}.rst": f"{d}\n==\n\nText.\n" for d in others},
    }
    second = {
        "z.rst": "Z\n=\n\nNothing.\n",
        **{f"{d}.rst": f"{d}\n==\n\nOther text.\n" for d in others},
    }
    app, root = _incremental(
        make_app, tmp_path, first, second, sorted([*others, "z"]), parallel=2
    )
    if sphinx.util.parallel.parallel_available:
        assert len(merged) > 1
    assert app.env.domaindata["mat"]["objects"]["g"] == ("a", "function", "g")
    assert "target not found" not in app.warning.getvalue()
    assert _duplicate_warnings(app, root) == []
    assert 'href="a.html#mat-g"' in (app.outdir / "index.html").read_text("utf-8")


def test_shared_folder_description_reads_only_the_changed_page(make_app, tmp_path):
    # The 0.x habit ``.. module:: pkg`` on every page, migrated.
    pages = [f"p{i}" for i in range(1, 6)]
    sources = {
        **WINNER_SOURCES,
        "index.rst": WINNER_INDEX + "".join(f"   {d}\n" for d in pages),
        **{f"{d}.rst": LIB_PAGE.format(title=d) + "\n" for d in pages},
    }
    fresh_root = tmp_path / "fresh"
    _write_pages(fresh_root, sources)
    fresh = make_app(srcdir=fresh_root)
    fresh.build()
    expected = {
        name: fresh.env.domaindata["mat"][name] for name in ("objects", "folders")
    }
    assert expected["folders"]["lib/"][0] == "p5"
    root = tmp_path / "incremental"
    _write_pages(root, sources)
    make_app(srcdir=root).build()
    for page in ("p3", "p5"):
        # now, not later: p3 must not stay newer than its next reading
        os.utime(root / f"{page}.rst")
        app = make_app(srcdir=root)
        app.build()
        assert list(app.env.get_domain("mat").read_docnames) == [page]
        for name in ("objects", "folders"):
            assert app.env.domaindata["mat"][name] == expected[name], page
        assert _duplicate_warnings(app, root) == []


def test_nested_auto_directive_reports_the_line_of_the_outer_one(make_app, tmp_path):
    # The help of f holds an auto directive of its own: what that describes
    # is on the page at the line of the directive written there.
    for path, text in {
        "conf.py": DUPLICATE_CONF,
        "src/f.m": "function y = f(x)\n% F help\n%\n% .. mat:autofunction:: h\n"
        "y = x;\nend\n",
        "src/h.m": DUPLICATE_SOURCES["src/h.m"],
        "index.rst": "Index\n=====\n\n.. toctree::\n\n   a\n   b\n",
        "a.rst": "A\n=\n\n.. mat:autofunction:: h\n",
        "b.rst": "B\n=\n\nText.\n\nMore.\n\n.. mat:autofunction:: f\n",
    }.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")
    app = make_app(srcdir=tmp_path)
    app.build()
    assert _duplicate_warnings(app, tmp_path) == [_dup("b", 8, "h.m", "a")]
    assert app.env.get_domain("mat").data["objects"]["h.m"][0] == "b"
