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
    assert MATLABDomain.data_version == 29
    assert set(MATLABDomain.initial_data) == {
        "objects",
        "folders",
        "doc_sources",
        "sidecar_docs",
        "sidecar_issues",
        "xref_docs",
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

    warnings_before = app.warning.getvalue()
    dom.note_object("some/Thing.m", "function", "Thing")
    assert app.warning.getvalue() == warnings_before

    dom.note_object("some/Thing.m", "class", "Thing", location=("index_first", 3))
    warning = app.warning.getvalue()
    assert "duplicate object description of some/Thing.m" in warning
    assert "[mat.duplicate]" in warning
    assert dom.data["objects"]["some/Thing.m"] == ("index_first", "class", "Thing")


def _worker(docname, objects=(), folders=()):
    """Domain data of a parallel-read worker that read ``docname``."""
    data = {name: {} for name in MATLABDomain.initial_data}
    data["objects"] = {ref: (docname, *entry) for ref, *entry in objects}
    data["folders"] = {ref: (docname, *entry) for ref, *entry in folders}
    return data


def _merge_in_order(make_app, srcdir, workers, order):
    """Merge ``workers`` (docname -> data) in ``order``, after a build that
    read them in name order, as Sphinx does after clearing them.
    """
    app = build(make_app, srcdir)
    dom = app.env.get_domain("mat")
    dom.read_docnames = [*dom.read_docnames, *sorted(workers)]
    app.warning.truncate(0)
    app.warning.seek(0)
    for docname in order:
        dom.merge_domaindata({docname}, workers[docname])
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
        f"<SRC>/{later}.rst: WARNING: [sphinxcontrib-matlabdomain] duplicate "
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
