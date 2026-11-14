"""Parse contract in a build: classify() types, divergence and empty-file warnings."""

import os
import time
from pathlib import Path

import pytest

from sphinxcontrib import mat_types

CONF = (
    'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "."\n'
)

# classdef without the end of its method (tests/test_data/ClassWithErrors.m):
# a class by its first line, a script for tree-sitter.
BROKEN_CLASS = """classdef PcBox
    % Class definition with missing end

    methods
        function obj = PcBox()
            obj.a = 10;
    end
end
"""

SOURCES = {
    "pc_function.m": "function pc_function\n% A function.\nend\n",
    "pc_local.m": "% A script with a local function.\nx = 1;\nfunction g\nend\n",
    "pc_empty.m": "",
    "pc_comment.m": "% Only a comment.\n",
    "pc_functions.m": "functions = 1;\n",
    "pc_bad.m": "function = 1;\n",
    "@PcBox/PcBox.m": BROKEN_CLASS,
}


def write_project(root, files, rst=""):
    for path, text in {**files, "conf.py": CONF, "index.rst": rst}.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)


def index_by_ref(app):
    return {e["reference"]: e for e in app.env.domaindata["mat"]["index"].values()}


def test_index_type_comes_from_classify(make_app, tmp_path):
    write_project(
        tmp_path,
        SOURCES,
        "Index\n=====\n\n.. mat:autoscript:: pc_local.m\n\n"
        ".. mat:autoscript:: @PcBox/PcBox.m\n",
    )
    app = make_app(srcdir=tmp_path)
    app.build()

    index = index_by_ref(app)
    assert {ref: e["type"] for ref, e in index.items()} == {
        "pc_function.m": "function",
        "pc_local.m": "script",
        "pc_empty.m": "script",
        "pc_comment.m": "script",
        "pc_functions.m": "script",
        "pc_bad.m": "function",
        "@PcBox/PcBox.m": "class",
    }
    # is_class comes from classify(): the broken class keeps its class name.
    assert index["@PcBox/PcBox.m"]["matlab_name"] == "PcBox"

    dom = app.env.get_domain("mat")
    table = {ref: mat_types.resolve(dom, ref) for ref in index}
    assert isinstance(table["pc_local.m"], mat_types.MatScript)
    assert isinstance(table["@PcBox/PcBox.m"], mat_types.MatScript)
    assert isinstance(table["pc_functions.m"], mat_types.MatScript)
    assert isinstance(table["pc_bad.m"], mat_types.MatScript)
    assert table["pc_comment.m"].docstring == "Only a comment."

    html = (app.outdir / "index.html").read_text()
    assert "A script with a local function." in html
    # Documented, not dropped (its comment is inside a tree-sitter ERROR node).
    assert 'id="mat-&#64;PcBox/PcBox.m"' in html


def test_help_file_beside_a_mex_file_is_a_function(make_app, tmp_path):
    write_project(
        tmp_path,
        {"pc_fast.m": "% PC_FAST Add numbers quickly.\n%   y = pc_fast(x)\n"},
        "Index\n=====\n\n.. mat:autofolder:: ./\n   :members:\n",
    )
    mex = tmp_path / "pc_fast.mexw64"

    def build():
        app = make_app(srcdir=tmp_path)
        app.build()
        obj = mat_types.resolve(app.env.get_domain("mat"), "pc_fast.m")
        html = (app.outdir / "index.html").read_text()
        assert "Add numbers quickly." in html
        assert "[mat." not in app.warning.getvalue()
        return index_by_ref(app)["pc_fast.m"]["type"], type(obj), html

    kind, cls, _ = build()
    assert (kind, cls) == ("script", mat_types.MatScript)

    # A MEX file added later makes it a function, help kept.
    mex.write_bytes(b"MZ")
    kind, cls, html = build()
    assert (kind, cls) == ("function", mat_types.MatFunction)
    assert '<dl class="mat function">' in html

    mex.unlink()
    kind, cls, html = build()
    assert (kind, cls) == ("script", mat_types.MatScript)
    assert '<dl class="mat function">' not in html


# Pages that use the divergent files (and a script that does not diverge).
USE_SOURCES = (
    "Index\n=====\n\n.. mat:autoscript:: pc_bad.m\n\n"
    ".. mat:autoscript:: @PcBox/PcBox.m\n\n.. mat:autoscript:: pc_functions.m\n"
)


def test_divergence_and_empty_file_warnings(make_app, tmp_path, monkeypatch):
    write_project(tmp_path, SOURCES, USE_SOURCES)
    app = make_app(srcdir=tmp_path)
    app.build()

    warnings = app.warning.getvalue()
    assert warnings.count("may be invalid MATLAB") == 2
    assert (
        "@PcBox/PcBox.m: its first line of code makes it a class, but tree-sitter "
        "parsed a script; the file may be invalid MATLAB. [mat.invalid_matlab]"
    ) in warnings
    assert (
        "pc_bad.m: its first line of code makes it a function, but "
        "tree-sitter parsed a script"
    ) in warnings
    assert "pc_functions.m" not in warnings
    assert warnings.count(" is empty") == 1
    assert (
        "pc_empty.m is empty; it is documented as a script. [mat.empty_code_file]"
        in warnings
    )
    # A help file (comments only) is normal MATLAB.
    assert "pc_comment.m" not in warnings

    # Re-reading the page from the pickled environment reuses the parse and
    # warns again.
    def no_parse(*args, **kwargs):
        raise AssertionError("file parsed again")

    monkeypatch.setattr(mat_types.MatObject, "parse_mfile", staticmethod(no_parse))
    rst = tmp_path / "index.rst"
    now = time.time_ns()
    os.utime(rst, ns=(now, now))
    app2 = make_app(srcdir=tmp_path)
    app2.build()
    assert app2.warning.getvalue().count("may be invalid MATLAB") == 2
    assert app2.warning.getvalue().count(" is empty") == 1

    # Nothing re-read: index-stage warnings only.
    app3 = make_app(srcdir=tmp_path)
    app3.build()
    assert app3.warning.getvalue().count("may be invalid MATLAB") == 0
    assert app3.warning.getvalue().count(" is empty") == 1


def test_divergence_of_an_unused_file_is_not_reported(make_app, tmp_path):
    # Only a parse finds it, and nothing uses the files.
    write_project(tmp_path, SOURCES, "Index\n=====\n")
    app = make_app(srcdir=tmp_path)
    app.build()
    assert "may be invalid MATLAB" not in app.warning.getvalue()
    assert app.warning.getvalue().count(" is empty") == 1


@pytest.mark.parametrize("subtype", ["invalid_matlab", "empty_code_file"])
def test_warnings_are_suppressible(make_app, tmp_path, subtype):
    write_project(tmp_path, SOURCES, USE_SOURCES)
    app = make_app(
        srcdir=tmp_path, confoverrides={"suppress_warnings": [f"mat.{subtype}"]}
    )
    app.build()
    warnings = app.warning.getvalue()
    assert f"[mat.{subtype}]" not in warnings
    assert "[mat.invalid_matlab]" in warnings or "[mat.empty_code_file]" in warnings


@pytest.mark.parametrize("reverse", [False, True], ids=["sorted", "reversed"])
def test_hidden_file_stays_hidden_beside_same_named_folder(
    make_app, tmp_path, monkeypatch, reverse
):
    real_listdir = os.listdir
    monkeypatch.setattr(
        os, "listdir", lambda path: sorted(real_listdir(path), reverse=reverse)
    )
    files = {
        "Contents.m": "% HIDDEN_SENTINEL\n",
        "Contents/inner.m": "function inner\n% Inner help.\nend\n",
        "visible.m": "function visible\n% Visible help.\nend\n",
    }
    write_project(
        tmp_path,
        files,
        "Index\n=====\n\n.. mat:autofolder:: ./\n   :members:\n",
    )
    (tmp_path / "explicit.rst").write_text(
        ":orphan:\n\nExplicit\n========\n\n.. mat:autoscript:: Contents.m\n"
    )
    (tmp_path / "folder.rst").write_text(
        ":orphan:\n\nFolder\n======\n\n.. mat:autofolder:: Contents/\n"
        "   :members:\n\nSee :mat:folder:`Contents/`.\n"
    )
    app = make_app(srcdir=tmp_path)
    app.build()

    table = app.env.get_domain("mat").entities_table
    assert isinstance(table["Contents.m"], mat_types.MatScript)
    assert isinstance(table["Contents/"], mat_types.MatModule)

    # Automatic members: the visible file only; folders are never members.
    auto = (app.outdir / "index.html").read_text()
    assert "Visible help." in auto
    assert "HIDDEN_SENTINEL" not in auto
    assert 'id="mat-Contents.m"' not in auto

    # Naming the hidden file still documents it.
    explicit = (app.outdir / "explicit.html").read_text()
    assert "HIDDEN_SENTINEL" in explicit
    assert 'id="mat-Contents.m"' in explicit

    # The same-named folder keeps its own target, without the file's help.
    folder = (app.outdir / "folder.html").read_text()
    assert 'id="mat-Contents/"' in folder
    assert 'href="#mat-Contents/"' in folder
    assert "Inner help." in folder
    assert "HIDDEN_SENTINEL" not in folder
    assert "WARNING" not in app.warning.getvalue()


def test_special_files_are_indexed_but_hidden(make_app, tmp_path):
    files = {
        "Contents.m": "% Root Toolbox\n% Version 1.0\n",
        "+for/contents.m": "% Keyword namespace contents\n",
        "slblocks.m": "function b = slblocks\n% Library.\nb = 1;\nend\n",
        "sl_customization.m": "function sl_customization(cm)\nend\n",
        "pathdef.m": "function p = pathdef\np = '';\nend\n",
        "matlabrc.m": "% Startup.\nx = 1;\n",
        "rtwmakecfg.m": "function c = rtwmakecfg\nc = [];\nend\n",
        "startup.m": "% Start up.\nx = 1;\n",
    }
    write_project(
        tmp_path,
        files,
        "Index\n=====\n\n.. mat:autofolder:: ./\n   :members:\n\n"
        ".. mat:autoscript:: Contents.m\n",
    )
    app = make_app(srcdir=tmp_path)
    app.build()

    assert sorted(index_by_ref(app)) == sorted(files)
    html = (app.outdir / "index.html").read_text()
    assert "Start up." in html
    # Documented only when named explicitly.
    assert "Root Toolbox" in html
    for hidden in (
        "Library.",
        "Startup.",
        "mat-slblocks.m",
        "mat-pathdef.m",
        "mat-rtwmakecfg.m",
        "mat-sl_customization.m",
    ):
        assert hidden not in html
    # No mat.empty_code_file (Contents.m) or mat.not_callable (+for/contents.m).
    assert "WARNING" not in app.warning.getvalue()


# --- Docstring position -------------------------------------------------------

# name: (file lines, {object: MATLAB R2026a ``help`` text or None}). Verified
# with ``help`` on these exact files; before the parser followed ``help``, it
# matched 12 of 29.
HELP_CASES = {
    "fBefore": (
        ["% fBefore LEAD", "% second line", "function fBefore", "x = 1;", "end"],
        {"": "fBefore LEAD\nsecond line"},
    ),
    "fAfter": (
        ["function fAfter", "% fAfter TRAIL", "% second line", "x = 1;", "end"],
        {"": "fAfter TRAIL\nsecond line"},
    ),
    "fBoth": (
        ["% fBoth LEAD", "function fBoth", "% fBoth TRAIL", "end"],
        {"": "fBoth LEAD"},
    ),
    "fBlankLead": (
        ["% fBlankLead LEAD", "", "function fBlankLead", "end"],
        {"": "fBlankLead LEAD"},
    ),
    "fBlankBoth": (
        ["% fBlankBoth LEAD", "", "function fBlankBoth", "% fBlankBoth TRAIL", "end"],
        {"": "fBlankBoth LEAD"},
    ),
    "fBlankAfter": (
        ["function fBlankAfter", "", "% fBlankAfter TRAIL", "x = 1;", "end"],
        {"": "fBlankAfter TRAIL"},
    ),
    "fBothBlankAfter": (
        ["% fBBA LEAD", "function fBothBlankAfter", "", "% fBBA TRAIL", "end"],
        {"": "fBBA LEAD"},
    ),
    "fTwoLead": (
        ["% fTwoLead FIRST", "", "% fTwoLead SECOND", "function fTwoLead", "end"],
        {"": "fTwoLead FIRST"},
    ),
    "fCopyright": (
        ["% fCopy LEAD", "function fCopyright", "% fCopy TRAIL", "", "% (c)", "end"],
        {"": "fCopy LEAD"},
    ),
    "fCodeFirst": (
        ["function fCodeFirst", "x = 1;", "% fCodeFirst LATE", "end"],
        {"": None},
    ),
    "fBlankLines": (
        ["", "", "% fBlankLines LEAD", "", "", "function fBlankLines", "end"],
        {"": "fBlankLines LEAD"},
    ),
    "fArgsAfter": (
        ["function fArgsAfter(x)", "arguments", "x double", "end", "% AFTER", "end"],
        {"": "AFTER"},
    ),
    "fArgsBefore": (
        ["function fArgsBefore(x)", "% BEFORE", "arguments", "x double", "end", "end"],
        {"": "BEFORE"},
    ),
    "fLeadArgs": (
        ["% LEAD", "function fLeadArgs(x)", "% TRAIL", "arguments", "x", "end", "end"],
        {"": "LEAD"},
    ),
    "fCont": (
        ["function y = fCont(a, ...", "    b)", "% fCont TRAIL", "y = a;", "end"],
        {"": "fCont TRAIL"},
    ),
    "fNoEnd": (
        ["% fNoEnd LEAD", "function fNoEnd", "% fNoEnd TRAIL", "x = 1;"],
        {"": "fNoEnd LEAD"},
    ),
    "fInline": (
        ["function fInline % INLINE", "% fInline NEXT", "end"],
        {"": "fInline NEXT"},
    ),
    "fLeadInline": (
        ["% fLeadInline LEAD", "function fLeadInline % INLINE", "end"],
        {"": "fLeadInline LEAD"},
    ),
    "fInlineBlank": (
        ["function fInlineBlank % INLINE", "", "% fInlineBlank HELP", "end"],
        {"": "fInlineBlank HELP"},
    ),
    "CInlineBlank": (
        ["classdef CInlineBlank % INLINE", "", "% CInlineBlank HELP", "end"],
        {"": "CInlineBlank HELP"},
    ),
    "CBefore": (["% CBefore LEAD", "classdef CBefore", "end"], {"": "CBefore LEAD"}),
    "CAfter": (["classdef CAfter", "% CAfter TRAIL", "end"], {"": "CAfter TRAIL"}),
    "CBoth": (
        ["% CBoth LEAD", "classdef CBoth", "% CBoth TRAIL", "end"],
        {"": "CBoth LEAD"},
    ),
    "CBlankBoth": (
        [
            "% CBlankBoth LEAD", "", "classdef CBlankBoth", "",
            "% CBlankBoth TRAIL", "end",
        ],
        {"": "CBlankBoth LEAD"},
    ),
    "CAfterBlank": (
        [
            "classdef CAfterBlank", "", "% CAfterBlank TRAIL", "methods",
            "function mAfterBlank(~)", "", "% mAfterBlank TRAIL", "end",
            "end", "end",
        ],
        {"": "CAfterBlank TRAIL", "mAfterBlank": "mAfterBlank TRAIL"},
    ),
    "CMeth": (
        [
            "classdef CMeth", "% CMeth TRAIL", "methods",
            "% mBefore LEAD", "function mBefore(~)", "end",
            "function mAfter(~)", "% mAfter TRAIL", "end",
            "% mBoth LEAD", "function mBoth(~)", "% mBoth TRAIL", "end",
            "% mBlank LEAD", "", "function mBlank(~)", "% mBlank TRAIL", "end",
            "end", "end",
        ],
        {
            "": "CMeth TRAIL",
            "mBefore": None,
            "mAfter": "mAfter TRAIL",
            "mBoth": "mBoth TRAIL",
            "mBlank": "mBlank TRAIL",
        },
    ),
}  # fmt: skip

# MATLAB ``help`` takes the first run of ``%`` lines, so a ``%{ ... %}`` block
# gives "{" (R2026a Update 5, same procedure as above).
_B = ["%{", "block", "%}"]
BLOCK_HELP_CASES = {
    "fBlkLead": ([*_B, "function fBlkLead", "end"], {"": "{"}),
    "fBlkTrail": (["function fBlkTrail", *_B, "end"], {"": "{"}),
    "fBlkLeadBlank": ([*_B, "", "function fBlkLeadBlank", "end"], {"": "{"}),
    "fBlkTrailBlank": (["function fBlkTrailBlank", "", *_B, "end"], {"": "{"}),
    "fBlkLeadTrailLine": (
        [*_B, "function fBlkLeadTrailLine", "% TRAIL", "end"],
        {"": "{"},
    ),
    "fLineLeadTrailBlk": (
        ["% LEAD", "function fLineLeadTrailBlk", *_B, "end"],
        {"": "LEAD"},
    ),
    "fLineThenBlkLead": (
        ["% LINE", *_B, "function fLineThenBlkLead", "end"],
        {"": "LINE\n{"},
    ),
    "fBlkThenLineLead": (
        [*_B, "% LINE", "function fBlkThenLineLead", "end"],
        {"": "{"},
    ),
    "fLineBlankBlkLead": (
        ["% LINE", "", *_B, "function fLineBlankBlkLead", "end"],
        {"": "LINE"},
    ),
    "fBlkBlankLineLead": (
        [*_B, "", "% LINE", "function fBlkBlankLineLead", "end"],
        {"": "{"},
    ),
    "fLineThenBlkTrail": (
        ["function fLineThenBlkTrail", "% LINE", *_B, "end"],
        {"": "LINE\n{"},
    ),
    "fBlkThenLineTrail": (
        ["function fBlkThenLineTrail", *_B, "% LINE", "end"],
        {"": "{"},
    ),
    "fBlkEmptyLead": (["%{", "%}", "function fBlkEmptyLead", "end"], {"": "{\n}"}),
    "fBlkEmptyTrail": (["function fBlkEmptyTrail", "%{", "%}", "end"], {"": "{\n}"}),
    "fBlkInlineTrail": (["function fBlkInlineTrail % INLINE", *_B, "end"], {"": "{"}),
    "fBlkIndentedLead": (
        ["  %{", "  block", "  %}", "function fBlkIndentedLead", "end"],
        {"": "{"},
    ),
    "fBlkOpenText": (["%{ text", "function fBlkOpenText", "end"], {"": "{ text"}),
    "fBlkTwoLines": (
        ["%{", "block one", "block two", "%}", "function fBlkTwoLines", "end"],
        {"": "{"},
    ),
    "CBlkLead": ([*_B, "classdef CBlkLead", "end"], {"": "{"}),
    "CBlkTrail": (["classdef CBlkTrail", *_B, "end"], {"": "{"}),
    "CBlkTrailBlank": (["classdef CBlkTrailBlank", "", *_B, "end"], {"": "{"}),
    "CBlkLeadTrailLine": (
        [*_B, "classdef CBlkLeadTrailLine", "% TRAIL", "end"],
        {"": "{"},
    ),
    "CLineThenBlkLead": (
        ["% LINE", *_B, "classdef CLineThenBlkLead", "end"],
        {"": "LINE\n{"},
    ),
    "CBlkThenLineLead": (
        [*_B, "% LINE", "classdef CBlkThenLineLead", "end"],
        {"": "{"},
    ),
    "CLineThenBlkTrail": (
        ["classdef CLineThenBlkTrail", "% LINE", *_B, "end"],
        {"": "LINE\n{"},
    ),
    "CBlkInlineTrail": (["classdef CBlkInlineTrail % INLINE", *_B, "end"], {"": "{"}),
    "CBlkMeth": (
        [
            "classdef CBlkMeth", "% CBlkMeth TRAIL", "methods",
            "function mBlkTrail(~)", *_B, "end",
            "function mLineThenBlk(~)", "% LINE", *_B, "end",
            "function mBlkThenLine(~)", *_B, "% LINE", "end",
            "function mBlkTrailBlank(~)", "", *_B, "end",
            "function mBlkInline(~) % INLINE", *_B, "end",
            *_B, "function mBlkLead(~)", "end",
            "end", "end",
        ],
        {
            "": "CBlkMeth TRAIL",
            "mBlkTrail": "{",
            "mLineThenBlk": "LINE\n{",
            "mBlkThenLine": "{",
            "mBlkTrailBlank": "{",
            "mBlkInline": "{",
            "mBlkLead": None,
        },
    ),
}  # fmt: skip


def _help(docstring):
    return (docstring or "").strip() or None


@pytest.mark.parametrize("name", [*HELP_CASES, *BLOCK_HELP_CASES])
def test_docstring_matches_matlab_help(tmp_path, name):
    lines, expected = {**HELP_CASES, **BLOCK_HELP_CASES}[name]
    mfile = tmp_path / f"{name}.m"
    mfile.write_text("\n".join(lines) + "\n")
    obj = mat_types.MatObject.parse_mfile(mfile, name, "./")
    got = {"": _help(obj.docstring)}
    for meth in expected.keys() - {""}:
        got[meth] = _help(obj.methods[meth].docstring)
    assert got == expected


@pytest.mark.parametrize(
    "fixture",
    ["standardClassWithBlockComment.m", "standardClassWithBlockCommentBlankLine.m"],
)
def test_block_comment_fixtures_match_matlab_help(fixture):
    # R2026a help returns "{" for both (checked on these exact files).
    mfile = Path(__file__).parent / "_classify_cases" / fixture
    obj = mat_types.MatObject.parse_mfile(mfile, mfile.stem, "./")
    assert _help(obj.docstring) == "{"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("% fCrlf LEAD\r\n% second\r\nfunction fCrlf\r\nend\r\n", "fCrlf LEAD\nsecond"),
        ("function f\r\n% f TRAIL\r\n% second\r\nend\r\n", "f TRAIL\nsecond"),
    ],
)
def test_crlf_docstring_keeps_all_lines(tmp_path, text, expected):
    # R2026a help shows both lines (tree-sitter-matlab 1.3.2 split the block).
    mfile = tmp_path / "f.m"
    mfile.write_bytes(text.encode())
    assert mat_types.MatObject.parse_mfile(mfile, "f", "./").docstring == expected


def test_script_docstring_is_its_first_comment(tmp_path):
    # The script query captures every top-level comment, not in document
    # order; taking the first capture made the docstring a later block
    # (a live script's %[appendix], ...) that also varied between builds.
    blocks = "".join(f"x{i} = {i};\n% block {i}\n" for i in range(10))
    mfile = tmp_path / "s.m"
    mfile.write_text(f"% S HELP\n{blocks}")
    obj = mat_types.MatObject.parse_mfile(mfile, "s", "./")
    assert isinstance(obj, mat_types.MatScript)
    assert obj.docstring == "S HELP"


def test_application_type_and_m_before_mlapp(make_app, rootdir, tmp_path):
    app_file = (rootdir / "test_data" / "Application.mlapp").read_bytes()
    (tmp_path / "Application.mlapp").write_bytes(app_file)
    (tmp_path / "both.mlapp").write_bytes(app_file)
    write_project(
        tmp_path,
        {"both.m": "function both\n% The .m file.\nend\n"},
        "Index\n=====\n\n.. mat:autofunction:: both.m\n",
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    assert {ref: e["type"] for ref, e in index_by_ref(app).items()} == {
        "Application.mlapp": "application",
        "both.mlapp": "application",
        "both.m": "function",
    }
    # A name without extension tries .m before .mlapp.
    assert isinstance(mat_types.MatObject.matlabify("both"), mat_types.MatFunction)
    assert "The .m file." in (app.outdir / "index.html").read_text()


def test_docstring_positions_render(make_app, tmp_path):
    files = {
        "dp_before.m": "% dp_before LEAD\nfunction dp_before\nend\n",
        "dp_after.m": "function dp_after\n\n% dp_after TRAIL\nend\n",
        "dp_both.m": "% dp_both LEAD\n\nfunction dp_both\n% dp_both TRAIL\nend\n",
        "DpClass.m": "\n".join(HELP_CASES["CMeth"][0]).replace("CMeth", "DpClass"),
        "DpLead.m": "% DpLead LEAD\nclassdef DpLead\n% DpLead TRAIL\nend\n",
    }
    write_project(
        tmp_path,
        files,
        "Index\n=====\n\n"
        + "".join(f".. mat:autofunction:: dp_{k}\n\n" for k in ("before", "after"))
        + ".. mat:autofunction:: dp_both\n\n"
        + ".. mat:autoclass:: DpClass\n   :members:\n   :undoc-members:\n\n"
        + ".. mat:autoclass:: DpLead\n",
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    html = (app.outdir / "index.html").read_text()
    for shown in (
        "dp_before LEAD",
        "dp_after TRAIL",
        "dp_both LEAD",
        "DpLead LEAD",
        "DpClass TRAIL",
        "mAfter TRAIL",
        "mBoth TRAIL",
        "mBlank TRAIL",
    ):
        assert shown in html
    for hidden in (
        "dp_both TRAIL",
        "DpLead TRAIL",
        "mBefore LEAD",
        "mBoth LEAD",
        "mBlank LEAD",
    ):
        assert hidden not in html
    assert 'id="mat-DpClass.m.mBefore"' in html
    assert "WARNING" not in app.warning.getvalue()
