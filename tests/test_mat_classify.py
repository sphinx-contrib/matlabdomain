"""Tests for ``classify()``.

``test_classify_reference_cases`` ports the 14 reference classifier tests (all
pass on MATLAB R2026a); their support files are copied unchanged to
``tests/_classify_cases`` (discovery skips ``_`` folders).
"""

import io
import os
from pathlib import Path

import pytest

from sphinxcontrib import mat_classify
from sphinxcontrib.mat_classify import classify, first_line_of_code, is_hidden

SUPPORT = Path(__file__).parent / "_classify_cases"


@pytest.mark.parametrize(
    ("name", "file", "expected"),
    [
        ("blank_file_no_extension", "blankFile", "script"),
        ("blank_file_with_extension", "blankFile.m", "script"),
        ("file_with_only_complete_block_comment", "blockCommentComplete.m", "script"),
        (
            "file_with_only_incomplete_block_comment",
            "blockCommentIncomplete.m",
            "script",
        ),
        ("file_with_only_one_comment", "commentFile", "script"),
        ("standard_class", "standardClass.m", "class"),
        (
            "standard_class_with_block_comment",
            "standardClassWithBlockComment.m",
            "class",
        ),
        (
            "standard_class_with_block_comment_blank_line",
            "standardClassWithBlockCommentBlankLine.m",
            "class",
        ),
        (
            "standard_class_with_comment_blank_line",
            "standardClassWithCommentBlankLine.m",
            "class",
        ),
        ("standard_class_with_tab_space", "standardClassWithTabSpace.m", "class"),
        ("standard_function", "standardFunction", "function"),
        ("standard_script", "standardScript", "script"),
        ("class_with_leading_utf8_bom", "standardClassWithBOM.m", "class"),
        ("function_with_leading_utf8_bom", "standardFunctionWithBOM.m", "function"),
    ],
)
def test_classify_reference_cases(name, file, expected):
    assert classify(SUPPORT / file) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("\tclassdef C\nend\n", "class"),
        ("% c\r\n\r\nfunction f\r\nend\r\n", "function"),
        ("% c\rfunction f\rend\r", "function"),
        ("x = 1;\n\ufeffclassdef C\n", "script"),
        ("% a\n\ufeff\nfunction f\n", "function"),
        # Block comments: exact %{ / %} lines only, not nested.
        ("  %{  \nfunction f\n  %}\nclassdef C\n", "class"),
        ("%{ not a block\nfunction f\n", "function"),
        ("%{\n%{\n%}\nfunction f\n%}\n", "function"),
        ("%%\nfunction f\n", "function"),
        # Whole keywords only (unlike the reference); MATLAB R2026a runs the
        # first three as scripts and the last two as a function and a class.
        ("functions = 1;\n", "script"),
        ("classdefault = 2;\n", "script"),
        ("function_x = 1;\n", "script"),
        ("function[y]=f(x)\n", "function"),
        ("classdef(Abstract) C\n", "class"),
        ("function = 1;\n", "function"),
        ("Function f\n", "script"),
        ("", "script"),
    ],
)
def test_classify_text(text, expected):
    assert classify("x.m", text) == expected


def test_classify_extensions(tmp_path):
    assert classify("app.mlapp", "function f") == "unknown"
    assert classify("x.txt", "function f") == "unknown"
    assert classify("X.M", "function f") == "function"
    assert classify("x", "classdef x") == "class"
    assert classify("a.b/c", "function f") == "function"
    assert classify(tmp_path / "missing.m") == "unknown"
    assert classify(tmp_path / "missing") == "unknown"
    assert classify(tmp_path / "x.txt") == "unknown"


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"function f\n", "function"),
        (b"\xef\xbb\xbf% \xff\nfunction f\n", "function"),  # BOM, invalid UTF-8
        (b"% c\r\n\r\nfunction f\r\n", "function"),
        (b"% c\rfunction f\r", "function"),
        (b"% \xe9\xff\nclassdef C\n", "class"),
        (b"x = 1;\n", "script"),
    ],
    ids=["plain", "bom_invalid_utf8", "crlf", "lone_cr", "latin1_bytes", "script"],
)
@pytest.mark.parametrize("name", ["f.m", "f"])
def test_classify_reads_file_with_replacement(tmp_path, name, data, expected):
    (tmp_path / "f.m").write_bytes(data)
    assert classify(tmp_path / name) == expected


def test_classify_opens_the_supplied_path(monkeypatch):
    # ``.m`` is appended only without an extension, even on a case-insensitive
    # file system where a wrong name would still open.
    opened = []

    def fake_open(file, *args, **kwargs):
        opened.append(file)
        return io.BytesIO(b"classdef X\n")

    monkeypatch.setattr(mat_classify, "open", fake_open, raising=False)
    paths = [
        os.path.join("dir", "X.M"),
        os.path.join("dir", "x.m"),
        os.path.join("dir", "x"),
        Path("dir") / "Y.M",
    ]
    assert [classify(path) for path in paths] == ["class"] * 4
    assert opened == [
        os.path.join("dir", "X.M"),
        os.path.join("dir", "x.m"),
        os.path.join("dir", "x.m"),
        os.path.join("dir", "Y.M"),
    ]
    opened.clear()
    assert classify(os.path.join("dir", "Z.txt")) == "unknown"
    assert opened == []


def test_classify_uppercase_extension_file(tmp_path):
    (tmp_path / "X.M").write_text("classdef X\n")
    assert classify(tmp_path / "X.M") == "class"


def test_first_line_of_code():
    assert first_line_of_code("% c\n\n  x = 1; % c\n") == "x = 1; % c"
    assert first_line_of_code("%{\nfunction f\n") == ""


def test_is_hidden():
    for name in (
        "Contents.m",
        "a/+p/contents.m",
        "slblocks.m",
        "SL_CUSTOMIZATION.m",
        "pathdef.m",
        "matlabrc.m",
        "rtwmakecfg.m",
    ):
        assert is_hidden(name)
    for name in (
        "startup.m",
        "finish.m",
        "userpath.m",
        "toolboxdir.m",
        "Contents.m/",
        "a/Contents.m.method",
        "MyContents.m",
    ):
        assert not is_hidden(name)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("% FAST Help.\n", True),
        ("\ufeff%{\nHelp.\n%}\n", True),
        ("", False),
        ("\ufeff \n\t\n", False),
        ("% Help.\nx = 1;\n", False),
        ("function f\n", False),
    ],
)
def test_is_help_only(text, expected):
    assert mat_classify.is_help_only(text) is expected


@pytest.mark.parametrize("ext", mat_classify.MEX_EXTENSIONS)
def test_help_file_beside_a_mex_file_is_a_function(tmp_path, ext):
    help_file = tmp_path / "fast.m"
    help_file.write_text("% FAST Add quickly.\n")
    (tmp_path / "code.m").write_text("x = 1;\n")
    (tmp_path / "blank.m").write_text("\n")
    assert classify(help_file) == "script"
    for stem in ("fast", "code", "blank"):
        (tmp_path / (stem + ext)).write_bytes(b"MEX")
    assert mat_classify.has_mex_file(help_file)
    assert classify(help_file) == "function"
    # Only a help file: code or nothing keeps it a script.
    assert classify(tmp_path / "code.m") == "script"
    assert classify(tmp_path / "blank.m") == "script"
    # A folder of that name is not a MEX file.
    (tmp_path / "other.m").write_text("% OTHER Help.\n")
    (tmp_path / ("other" + ext)).mkdir()
    assert classify(tmp_path / "other.m") == "script"
