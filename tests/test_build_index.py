"""The index stage without a Sphinx app: ``IndexSettings`` and ``build_index``
(plan.md Section 2.8, Phase 7).
"""

import dataclasses
import logging
import os
from typing import Any, cast

import pytest

from sphinxcontrib import mat_handlers
from sphinxcontrib.mat_types import (
    IndexSettings,
    SourceIndex,
    build_index,
    skipped_folder,
)

CONF = (
    'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "."\n'
    'primary_domain = "mat"\n'
)
FUNCTION = "function {name}\n% {help}\nend\n"
FILES = {
    "top.m": FUNCTION.format(name="top", help="TOP HELP"),
    "scr.m": "x = 1;\n",
    "+pkg/Cls.m": "classdef Cls\nend\n",
    "+pkg/@Box/Box.m": "classdef Box\nend\n",
    "+pkg/@Box/go.m": FUNCTION.format(name="go", help="GO HELP"),
    "+for/kw.m": FUNCTION.format(name="kw", help="KW HELP"),
    "private/helper.m": FUNCTION.format(name="helper", help="HELPER HELP"),
    "tests/test_x.m": FUNCTION.format(name="test_x", help="TEST HELP"),
}


def write(root, files, rst=None):
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content)
    if rst is not None:
        (root / "conf.py").write_text(CONF)
        (root / "index.rst").write_text(rst)


def refs(source_index):
    return sorted(r["reference"] for r in source_index.index.values())


@pytest.fixture
def warnings():
    """``(subtype, message)`` of the ``mat`` warnings logged meanwhile.

    The ``sphinx`` logger gets only this handler: Sphinx test apps leave
    theirs (which rewrite records) and turn off its propagation.
    """
    records = []

    class Collect(logging.Handler):
        def emit(self, record):
            if getattr(record, "type", None) == "mat":
                records.append((getattr(record, "subtype", None), record.getMessage()))

    logger = logging.getLogger("sphinx")
    saved = logger.handlers[:]
    logger.handlers = [Collect(logging.WARNING)]
    yield records
    logger.handlers = saved


def test_build_index_without_an_app(tmp_path):
    write(tmp_path, FILES)
    source_index = build_index(IndexSettings(str(tmp_path)))
    assert isinstance(source_index, SourceIndex)
    assert refs(source_index) == sorted(FILES)
    records = {r["reference"]: r for r in source_index.index.values()}
    assert {ref: r["type"] for ref, r in records.items()} == {
        "top.m": "function",
        "scr.m": "script",
        "+pkg/Cls.m": "class",
        "+pkg/@Box/Box.m": "class",
        "+pkg/@Box/go.m": "function",
        "+for/kw.m": "function",
        "private/helper.m": "function",
        "tests/test_x.m": "function",
    }
    assert records["+pkg/Cls.m"]["matlab_name"] == "pkg.Cls"
    assert records["+pkg/@Box/go.m"]["matlab_name"] == "pkg.Box.go"
    assert records["+for/kw.m"]["matlab_name"] is None
    assert records["private/helper.m"]["private"] is True
    assert records["top.m"]["scope"] == "./"
    assert sorted(source_index.entities) == [
        "+for/",
        "+pkg/",
        "+pkg/@Box/",
        "./",
        "private/",
        "tests/",
    ]
    pkg = source_index.entities["+pkg/"]
    assert pkg.matlab_name == "pkg"
    assert sorted(pkg.members) == [("@Box", "+pkg/@Box/"), ("Cls", "+pkg/Cls.m")]
    assert source_index.entities["+for/"].matlab_name is None
    assert source_index.matlab_names["pkg.Cls"] == ["+pkg/Cls.m"]
    assert source_index.matlab_names["pkg"] == ["+pkg/"]
    # The decoded text is kept for the parse.
    assert sorted(os.path.basename(k[0]) for k in source_index.text_cache) == sorted(
        os.path.basename(p) for p in FILES
    )


def test_settings_are_frozen(tmp_path):
    settings = IndexSettings(str(tmp_path))
    with pytest.raises(dataclasses.FrozenInstanceError):
        cast(Any, settings).root = "elsewhere"


def test_underscore_folders_and_sphinx_output(tmp_path):
    """Folders starting with ``_`` are searched (projects sort with them);
    hidden folders and Sphinx output, which copies MATLAB files, are not.
    """
    write(
        tmp_path,
        {
            "_01_intro/a.m": FUNCTION.format(name="a", help="A"),
            "+pkg/_util/b.m": FUNCTION.format(name="b", help="B"),
            ".hidden/c.m": FUNCTION.format(name="c", help="C"),
            "docs/_build/d.m": FUNCTION.format(name="d", help="D"),
            "docs/_static/e.m": FUNCTION.format(name="e", help="E"),
            "build/html/.buildinfo": "",
            "build/html/_downloads/f.m": FUNCTION.format(name="f", help="F"),
            "out/.doctrees/environment.pickle": b"",
            "out/g.m": FUNCTION.format(name="g", help="G"),
            "make/doctrees/environment.pickle": b"",
            "make/latex/h.m": FUNCTION.format(name="h", help="H"),
        },
    )
    settings = IndexSettings(str(tmp_path), source_dir=str(tmp_path / "docs"))
    source_index = build_index(settings)
    assert refs(source_index) == ["+pkg/_util/b.m", "_01_intro/a.m", "docs/_static/e.m"]
    assert "build/" in source_index.entities
    assert "build/html/" not in source_index.entities
    assert "out/" not in source_index.entities
    assert "make/" not in source_index.entities
    records = {r["reference"]: r for r in source_index.index.values()}
    assert records["_01_intro/a.m"]["matlab_name"] == "a"
    assert records["+pkg/_util/b.m"]["matlab_name"] == "b"


def test_unreadable_folder_is_searched(tmp_path):
    """A folder that cannot be listed is not taken for Sphinx output."""
    assert skipped_folder(str(tmp_path / "gone"), "gone") is False


@pytest.mark.parametrize(
    "confoverrides",
    [
        {},
        {"matlab_src_exclude_patterns": ["tests"]},
        {"matlab_src_include_patterns": ["+pkg/**", "src/../top.m"]},
        {"matlab_version": "R2025b"},
    ],
)
def test_build_index_matches_the_build(make_app, tmp_path, confoverrides):
    write(tmp_path, FILES, rst="Index\n=====\n")
    app = make_app(srcdir=tmp_path, confoverrides=confoverrides)
    app.build()
    dom = app.env.get_domain("mat")
    settings = IndexSettings.from_config(app.config, app.srcdir)
    assert settings is not None
    assert settings.root == os.path.normpath(str(tmp_path))
    source_index = build_index(settings)
    assert list(source_index.index.items()) == list(dom.data["index"].items())
    assert source_index.matlab_names == dom.data["matlab_names"]
    assert list(source_index.entities) == [
        r for r in dom.entities_table if r.endswith("/")
    ]
    for ref, entity in source_index.entities.items():
        built = dom.entities_table[ref]
        assert entity.members == built.members
        assert (entity.matlab_name, entity.private, entity.scope) == (
            built.matlab_name,
            built.private,
            built.scope,
        )


def test_from_config_without_a_project_root(make_app, tmp_path):
    write(tmp_path, FILES, rst="Index\n=====\n")
    (tmp_path / "conf.py").write_text(CONF.replace('"."', "None"))
    app = make_app(srcdir=tmp_path)
    assert IndexSettings.from_config(app.config, app.srcdir) is None


def test_build_index_patterns(tmp_path):
    write(tmp_path, FILES)
    settings = IndexSettings(
        str(tmp_path), include=("+pkg/**", "top.m"), exclude=("+pkg/@Box",)
    )
    source_index = build_index(settings)
    assert refs(source_index) == ["+pkg/Cls.m", "top.m"]
    # Folders outside the patterns are not walked.
    assert sorted(source_index.entities) == ["+pkg/", "./"]


def test_build_index_warnings(tmp_path, warnings):
    write(
        tmp_path,
        {
            "+for/kw.m": FUNCTION.format(name="kw", help="KW HELP"),
            "bad.m": b"x = 1; % caf\xe9\n",
            "empty.m": "",
            "Contents.m": "% Contents of the folder\n",
            # Hidden files never get the empty-file warning.
            "sub/Contents.m": "",
            "private/helper.m": FUNCTION.format(name="helper", help="H"),
        },
    )
    build_index(IndexSettings(str(tmp_path)))
    assert sorted(subtype for subtype, _ in warnings) == [
        "empty_code_file",
        "encoding",
        "not_callable",
    ]
    messages = dict(warnings)
    assert messages["encoding"].startswith("[sphinxcontrib-matlabdomain] bad.m ")
    assert messages["empty_code_file"].startswith(
        "[sphinxcontrib-matlabdomain] empty.m is empty"
    )
    assert "+for/kw.m is not callable in MATLAB R2026a" in messages["not_callable"]


def kinds(source_index):
    return {
        r["reference"]: (r["type"], r["help_only"]) for r in source_index.index.values()
    }


def test_help_files_and_mex_functions(tmp_path, warnings):
    write(
        tmp_path,
        {
            "readme.m": "% README Notes on this folder.\n",
            "fast.m": b"\xef\xbb\xbf% FAST Add numbers quickly.\n",
            "fast.mexw64": b"MZ",
            "blank.m": b"\xef\xbb\xbf\n  \n",
        },
    )
    settings = IndexSettings(str(tmp_path))
    first = build_index(settings)
    assert kinds(first) == {
        "blank.m": ("script", False),
        "fast.m": ("function", True),
        "readme.m": ("script", True),
    }
    # Comments only is a help file, not a problem; blank is.
    assert [subtype for subtype, _ in warnings] == ["empty_code_file"]
    assert "blank.m is empty" in warnings[0][1]

    # Reused records follow the MEX files.
    (tmp_path / "fast.mexw64").unlink()
    (tmp_path / "readme.mexa64").write_bytes(b"ELF")
    second = build_index(settings, first.index)
    assert kinds(second) == {
        "blank.m": ("script", False),
        "fast.m": ("script", True),
        "readme.m": ("function", True),
    }


def test_build_index_reuses_unchanged_records(tmp_path, monkeypatch):
    reads = []
    original = mat_handlers.MFileHandler.read

    def counting(self, path, encoding=None):
        reads.append(os.path.basename(path))
        return original(self, path, encoding)

    monkeypatch.setattr(mat_handlers.MFileHandler, "read", counting)
    write(tmp_path, FILES)
    settings = IndexSettings(str(tmp_path))
    first = build_index(settings)
    assert len(reads) == len(FILES)
    reads.clear()
    second = build_index(settings, first.index)
    assert reads == []
    assert second.index == first.index
    assert second.text_cache == {}
    (tmp_path / "top.m").write_text(FUNCTION.format(name="top", help="CHANGED"))
    third = build_index(settings, second.index)
    assert reads == ["top.m"]
    assert len(third.text_cache) == 1


def test_build_index_of_a_missing_root(tmp_path):
    source_index = build_index(IndexSettings(str(tmp_path / "missing")))
    assert source_index.index == {}
    assert source_index.entities == {}
    assert source_index.matlab_names == {}
