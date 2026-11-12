"""Fault tolerance: one bad file never breaks a build (plan.md Phase 5, 2.10).

Malformed fixtures are written to temporary projects, so the ``test_docs``
build that walks ``tests/`` never sees them.
"""

import codecs
import io
import os
import re
import sys
import zipfile
from typing import Any, cast
from unittest.mock import Mock

import pytest
from conftest import remove_build_tree
from sphinx.errors import ConfigError

from sphinxcontrib import mat_classify, mat_handlers, mat_types
from sphinxcontrib.mat_classify import decode_source

CONF = (
    'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "."\n'
    'primary_domain = "mat"\n'
)

WARNING_RE = re.compile(
    r"WARNING: \[sphinxcontrib-matlabdomain\] (\S+) .*\[mat\.(\w+)\]$", re.MULTILINE
)
COLOR_RE = re.compile(r"\x1b\[[0-9;]*m")

# vhlab-toolbox-matlab +vlt/+plot/hist2d.m, shortened
HIST2D = """%function mHist = hist2d ([vY, vX], vYEdge, vXEdge)
%2 Dimensional Histogram
%Counts number of points in the bins defined by vYEdge, vXEdge.
function mHist = ftpkg.ft_dotted (mX, vYEdge, vXEdge)
nCol = size(mX, 2);
mHist = zeros(nCol);
"""

FUNCTION = "function y = {name}(x)\n% {help}\ny = x;\nend\n"
FALLBACK_LABEL = "Windows ANSI" if sys.platform == "win32" else "ISO-8859-1"


def write(root, files):
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            content = content.encode("utf-8")
        target.write_bytes(content)


def warnings_of(app):
    """``[(subtype, reference)]`` of the domain's file warnings, sorted."""
    text = COLOR_RE.sub("", app.warning.getvalue())
    return sorted((sub, ref.rstrip(":")) for ref, sub in WARNING_RE.findall(text))


def zip_bytes(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in members.items():
            z.writestr(name, text)
    return buf.getvalue()


# --- decoding (MATLAB R2026a on Linux, plan.md Section 2.10) ---------------


def test_decode_utf8_and_latin1_fallback():
    assert decode_source("café €".encode()) == ("café €", None)
    text, problem = decode_source("x\n% café £".encode("latin-1"))
    assert text == "x\n% café £"
    assert problem == (
        "is not valid UTF-8 (line 2: invalid continuation byte); decoded as "
        f"{FALLBACK_LABEL} like MATLAB.",
        1,
    )
    text, problem = decode_source("café\n".encode() + b"\x80\xff")
    fallback = "mbcs" if sys.platform == "win32" else "latin-1"
    assert text == ("café\n".encode() + b"\x80\xff").decode(fallback, errors="replace")
    assert problem is not None
    assert problem[1] == 1


@pytest.mark.parametrize(
    ("fallback", "expected"),
    [(("latin-1", "ISO-8859-1"), 128), (("cp1252", "Windows ANSI"), 8364)],
)
def test_decode_platform_fallback(monkeypatch, fallback, expected):
    monkeypatch.setattr(mat_classify, "_FALLBACK", fallback)
    text, problem = decode_source("café\n".encode() + b"\x80\xff")
    assert [ord(char) for char in text if ord(char) > 127] == [195, 169, expected, 255]
    assert problem == (
        "is not valid UTF-8 (line 2: invalid start byte); decoded as "
        f"{fallback[1]} like MATLAB.",
        1,
    )


@pytest.mark.parametrize("winerror", [32, 33])
def test_build_cleanup_retries_sharing_violation(monkeypatch, tmp_path, winerror):
    error = PermissionError("locked")
    cast(Any, error).winerror = winerror
    remove = Mock(side_effect=[error, None])
    pause = Mock()
    monkeypatch.setattr("conftest.shutil.rmtree", remove)
    monkeypatch.setattr("conftest.time.sleep", pause)
    remove_build_tree(tmp_path)
    assert remove.call_count == 2
    pause.assert_called_once_with(0.05)


@pytest.mark.parametrize(("winerror", "attempts"), [(5, 1), (32, 5)])
def test_build_cleanup_propagates_errors(monkeypatch, tmp_path, winerror, attempts):
    error = PermissionError("locked")
    cast(Any, error).winerror = winerror
    remove = Mock(side_effect=error)
    pause = Mock()
    monkeypatch.setattr("conftest.shutil.rmtree", remove)
    monkeypatch.setattr("conftest.time.sleep", pause)
    with pytest.raises(PermissionError) as raised:
        remove_build_tree(tmp_path)
    assert raised.value is error
    assert remove.call_count == attempts
    assert pause.call_count == attempts - 1


@pytest.mark.parametrize(
    "bom, codec",
    [
        (codecs.BOM_UTF8, "utf-8"),
        (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"),
        (codecs.BOM_UTF32_LE, "utf-32-le"),
        (codecs.BOM_UTF32_BE, "utf-32-be"),
    ],
)
def test_decode_byte_order_marks(bom, codec):
    assert decode_source(bom + "% café".encode(codec)) == ("% café", None)


def test_utf16_without_bom_is_not_guessed():
    text, problem = decode_source("% a".encode("utf-16-le"))
    assert text == "%\x00 \x00a\x00"
    assert problem is None


def test_decode_explicit_encoding():
    assert decode_source(b"% \x80", "cp1252") == ("% €", None)
    # A byte-order mark wins over the configured encoding.
    assert decode_source(codecs.BOM_UTF8 + "% é".encode(), "cp1252") == ("% é", None)
    assert decode_source(codecs.BOM_UTF16_LE + "% é".encode("utf-16-le"), "utf-8") == (
        "% é",
        None,
    )
    text, problem = decode_source(b"x\n% \xff", "ascii")
    assert text == "x\n% \ufffd"
    assert problem == (
        "is not valid ascii (line 2: ordinal not in range(128)); undecodable "
        "bytes are shown as U+FFFD.",
        1,
    )


def test_byte_order_mark_with_invalid_bytes_is_not_latin1():
    # MATLAB R2026a: "not a valid MATLAB file"; here U+FFFD and a warning.
    text, problem = decode_source(codecs.BOM_UTF8 + b"% \xc3\xa9\n% \x80")
    assert text == "% é\n% \ufffd"
    assert problem is not None
    assert problem[0].startswith("is not valid utf-8 (line 2: invalid start byte)")


# --- parsing --------------------------------------------------------------


def parse(tmp_path, name, content, encoding=None):
    write(tmp_path, {name: content})
    stem = os.path.splitext(os.path.basename(name))[0]
    return mat_types.MatObject.parse_mfile(str(tmp_path / name), stem, "./", encoding)


def test_latin1_file_uses_one_decoded_text(tmp_path):
    obj = parse(
        tmp_path,
        "lat.m",
        "% LEAD café\nfunction y = lat(x)\ny = x;\nend\n".encode("latin-1"),
    )
    assert isinstance(obj, mat_types.MatFunction)
    assert obj.source_type == obj.parsed_type == "function"
    assert obj.docstring == "LEAD café"
    assert obj.args == {"x": {}}
    assert [w[0] for w in obj.source_warnings] == ["encoding"]
    assert obj.source_warnings[0][2] == 0


def test_utf16_file_is_parsed(tmp_path):
    obj = parse(
        tmp_path,
        "u16.m",
        codecs.BOM_UTF16_BE
        + FUNCTION.format(name="u16", help="U16 café").encode("utf-16-be"),
    )
    assert isinstance(obj, mat_types.MatFunction)
    assert obj.docstring == "U16 café"
    assert obj.source_warnings == []


def test_explicit_encoding_is_applied(tmp_path):
    obj = parse(tmp_path, "cp.m", b"function cp\n% COST \x80 5\nend\n", "cp1252")
    assert obj.docstring == "COST € 5"
    assert obj.source_warnings == []


def test_dotted_function_name_is_named_by_file(tmp_path):
    obj = parse(tmp_path, "+ftpkg/ft_dotted.m", HIST2D)
    assert isinstance(obj, mat_types.MatFunction)
    assert obj.name == "ft_dotted"
    assert obj.retv == {"mHist": {}}
    assert obj.args == {"mX": {}, "vYEdge": {}, "vXEdge": {}}
    assert obj.docstring is not None
    assert obj.docstring.startswith("function mHist = hist2d")
    ((subtype, message, row),) = obj.source_warnings
    assert subtype == "invalid_matlab"
    assert row == 3
    assert "dotted function name ftpkg.ft_dotted" in message


@pytest.mark.parametrize(
    ("file", "text"),
    [
        ("ft_case.m", "classdef ft_Case\nend\n"),
        ("ft_lead.m", "% help\n\nclassdef (Abstract) ft_other < handle\nend\n"),
    ],
)
def test_classdef_named_unlike_its_file_warns(tmp_path, file, text):
    # MATLAB refuses the file; the exact (case-sensitive) file name wins.
    obj = parse(tmp_path, file, text)
    assert isinstance(obj, mat_types.MatClass)
    assert obj.name == file[:-2]
    ((subtype, message, row),) = obj.source_warnings
    assert subtype == "invalid_matlab"
    assert row == text.count("\n", 0, text.index("classdef"))
    assert f"but its file is {file};" in message
    assert "It is documented under its file name." in message


def test_function_named_unlike_its_file_is_valid(tmp_path):
    obj = parse(tmp_path, "ft_main.m", FUNCTION.format(name="other", help="H"))
    assert isinstance(obj, mat_types.MatFunction)
    assert obj.source_warnings == []


@pytest.mark.parametrize(
    "header",
    [
        "classdef ...\n    (Abstract) Cont < handle",
        "classdef (Abstract) ...\n    Cont < handle",
        "classdef (Abstract) Cont ...\n    < handle",
        "classdef ...\n    (Abstract) ...\n    Cont ...\n    < handle",
    ],
)
def test_class_header_line_continuations(tmp_path, header):
    obj = parse(tmp_path, "Cont.m", f"{header}\n% CONT HELP\nend\n")
    assert (obj.bases, obj.attrs, obj.docstring) == (
        ["handle"],
        {"Abstract": True},
        "CONT HELP",
    )


def test_class_parts_survive_line_continuations(tmp_path):
    obj = parse(
        tmp_path,
        "Cont.m",
        "classdef (Abstract) ...\n    Cont < handle\n% CONT HELP\n"
        "methods\nfunction obj = pkg.Other(obj)\nend\n"
        "function r = run(obj, ~, x)\narguments\n    obj\n    ~\n    x double\nend\n"
        "r = x;\nend\nend\nend\n",
    )
    assert isinstance(obj, mat_types.MatClass)
    assert obj.bases == ["handle"]
    assert obj.docstring == "CONT HELP"
    # The dotted converter method is skipped like set./get. methods; ``~`` in
    # an arguments block is not an argument.
    assert sorted(obj.methods) == ["run"]
    assert obj.source_warnings == []


def test_parser_exception_gives_placeholder(tmp_path, monkeypatch):
    def boom(*args):
        raise IndexError("list index out of range")

    monkeypatch.setattr(mat_types, "MatClassParser", boom)
    # tree-sitter still parses a class: an ERROR node inside a method body
    obj = parse(
        tmp_path,
        "Boom.m",
        "classdef Boom\n% BOOM\nmethods\nfunction f(o)\ny = 1 +* 2;\nend\nend\nend\n",
    )
    assert isinstance(obj, mat_types.MatClass)
    assert (obj.docstring, obj.properties, obj.methods) == (None, {}, {})
    assert obj.source_type == "class"
    assert obj.parsed_type is None  # no second (divergence) warning
    assert obj.source_warnings == [
        (
            "parse_error",
            "cannot be parsed (IndexError: list index out of range); it is "
            "documented without content. First syntax error: line 5, column 7.",
            4,
        )
    ]


def test_parser_exception_without_syntax_error_has_no_location(tmp_path, monkeypatch):
    def boom(*args):
        raise AttributeError("'NoneType' object has no attribute 'text'")

    monkeypatch.setattr(mat_types, "MatFunctionParser", boom)
    obj = parse(tmp_path, "fine.m", FUNCTION.format(name="fine", help="FINE"))
    assert isinstance(obj, mat_types.MatFunction)
    assert (obj.docstring, obj.retv, obj.args) == (None, {}, {})
    assert obj.source_warnings == [
        (
            "parse_error",
            "cannot be parsed (AttributeError: 'NoneType' object has no attribute "
            "'text'); it is documented without content.",
            None,
        )
    ]


# --- build ----------------------------------------------------------------

VALID = {
    "ft_ok_function.m": FUNCTION.format(name="ft_ok_function", help="OK FUNCTION HELP"),
    "+ftpkg/FtOkClass.m": (
        "classdef FtOkClass\n% OK CLASS HELP\nmethods\nfunction r = go(o)\n"
        "% OK METHOD HELP\nr = 1;\nend\nend\nend\n"
    ),
    "ft_ok_script.m": "% OK SCRIPT HELP\nx = 1;\n",
    "ft_utf16.m": codecs.BOM_UTF16_LE
    + FUNCTION.format(name="ft_utf16", help="UTF16 HELP café").encode("utf-16-le"),
    "ft_unclosed_block.m": (
        "function y = ft_unclosed_block(x)\n% UNCLOSED HELP\n%{\nstuff\ny = x;\nend\n"
    ),
}
MALFORMED = {
    "ft_trunc_class.m": (
        "classdef ft_trunc_class\n% TRUNC HELP\n    properties\n        x\n"
    ),
    "ft_latin1.m": FUNCTION.format(name="ft_latin1", help="LATIN1 HELP café").encode(
        "latin-1"
    ),
    "ft_empty.m": "",
    "ft_binary.m": bytes(range(256)) * 4,
    "ft_corrupt.mlapp": b"this is not a zip file",
    "ft_nometa.mlapp": zip_bytes({"foo.txt": "x"}),
    "+ftpkg/ft_dotted.m": HIST2D,
    "ft_misnamed.m": "% MISNAMED HELP\nclassdef FtOther\nend\n",
}
EXPECTED = [
    ("encoding", "ft_binary.m"),
    ("encoding", "ft_latin1.m"),
    ("invalid_matlab", "+ftpkg/ft_dotted.m"),
    ("invalid_matlab", "ft_binary.m"),
    ("invalid_matlab", "ft_misnamed.m"),
    ("invalid_matlab", "ft_trunc_class.m"),
    ("empty_code_file", "ft_empty.m"),
    ("parse_error", "ft_corrupt.mlapp"),
]
RST = """Index
=====

.. mat:autofunction:: ft_ok_function

.. mat:autoclass:: ftpkg.FtOkClass
   :members:

.. mat:autoscript:: ft_ok_script

.. mat:autofunction:: ft_utf16

.. mat:autofunction:: ft_unclosed_block

.. mat:autofunction:: ft_latin1

.. mat:autofunction:: +ftpkg/ft_dotted.m

.. mat:autoapplication:: ft_corrupt.mlapp

.. mat:autoscript:: ft_binary.m

.. mat:autoscript:: ft_trunc_class.m

.. mat:autoscript:: ft_empty.m

.. mat:autoclass:: ft_misnamed

See :mat:app:`ft_nometa.mlapp`.
"""

# chmod 000 does not stop root, and Windows has no such permission.
CAN_MAKE_UNREADABLE = sys.platform != "win32" and os.geteuid() != 0


@pytest.fixture
def malformed(tmp_path):
    write(tmp_path, {**VALID, **MALFORMED, "conf.py": CONF, "index.rst": RST})
    expected = list(EXPECTED)
    if CAN_MAKE_UNREADABLE:
        write(tmp_path, {"ft_unreadable.m": "function ft_unreadable\nend\n"})
        os.chmod(tmp_path / "ft_unreadable.m", 0)
        expected.append(("parse_error", "ft_unreadable.m"))
    yield tmp_path, sorted(expected)
    if CAN_MAKE_UNREADABLE:
        os.chmod(tmp_path / "ft_unreadable.m", 0o644)


@pytest.fixture
def parsed(monkeypatch):
    """Record every file the handlers parse."""
    calls = []
    for name in ("parse_mfile", "parse_mlappfile"):
        original = getattr(mat_types.MatObject, name)

        def counting(path, *args, _original=original, **kwargs):
            calls.append(path)
            return _original(path, *args, **kwargs)

        monkeypatch.setattr(mat_types.MatObject, name, staticmethod(counting))
    return calls


def test_malformed_files_warn_and_the_build_completes(make_app, malformed, parsed):
    srcdir, expected = malformed
    app = make_app(srcdir=srcdir)
    app.build()
    assert app.statuscode == 0
    assert warnings_of(app) == expected
    # Nothing else warns, e.g. an unresolved reference to a placeholder.
    assert app.warning.getvalue().count("WARNING") == len(expected)

    warnings = app.warning.getvalue()
    latin1 = srcdir / "ft_latin1.m"
    assert (
        f"{latin1}:2: WARNING: [sphinxcontrib-matlabdomain] ft_latin1.m is not "
        f"valid UTF-8 (line 2: invalid continuation byte); decoded as {FALLBACK_LABEL} "
        "like MATLAB. [mat.encoding]"
    ) in warnings
    dotted = srcdir / "+ftpkg" / "ft_dotted.m"
    assert (
        f"{dotted}:4: WARNING: [sphinxcontrib-matlabdomain] +ftpkg/ft_dotted.m "
        "declares the dotted function name ftpkg.ft_dotted"
    ) in warnings
    assert (
        "ft_corrupt.mlapp cannot be parsed (BadZipFile: File is not a zip file); "
        "it is documented without content. [mat.parse_error]"
    ) in warnings
    binary = srcdir / "ft_binary.m"
    assert (
        f"{binary}:1: WARNING: [sphinxcontrib-matlabdomain] ft_binary.m contains "
        "NUL bytes; it may be a binary file, not MATLAB code. [mat.invalid_matlab]"
    ) in warnings
    misnamed = srcdir / "ft_misnamed.m"
    assert (
        f"{misnamed}:2: WARNING: [sphinxcontrib-matlabdomain] ft_misnamed.m declares "
        "the class FtOther, but its file is ft_misnamed.m; MATLAB requires a "
        "classdef file to be named after its class. It is documented under its "
        "file name. [mat.invalid_matlab]"
    ) in warnings
    if CAN_MAKE_UNREADABLE:
        assert (
            "ft_unreadable.m cannot be read (Permission denied); it is documented "
            "without content. [mat.parse_error]"
        ) in warnings

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    for text in (
        "OK FUNCTION HELP",
        "OK CLASS HELP",
        "OK METHOD HELP",
        "OK SCRIPT HELP",
        "UTF16 HELP café",
        "UNCLOSED HELP",
        "LATIN1 HELP café",
        "2 Dimensional Histogram",
        "MISNAMED HELP",
    ):
        assert text in html
    # Failed files are placeholders: documented and referenceable.
    assert 'id="mat-ft_corrupt.mlapp"' in html
    assert 'href="#mat-ft_nometa.mlapp"' not in html  # not documented on a page
    index = {e["reference"]: e for e in app.env.domaindata["mat"]["index"].values()}
    assert index["ft_corrupt.mlapp"]["type"] == "application"
    assert index["+ftpkg/ft_dotted.m"]["matlab_name"] == "ftpkg.ft_dotted"
    if CAN_MAKE_UNREADABLE:
        assert index["ft_unreadable.m"]["type"] == "unknown"

    # Only the files the page uses are parsed: ft_nometa.mlapp is just linked
    # (no parse, no parse-stage warning) and the index stage reported the
    # unreadable file.
    unused = {"ft_nometa.mlapp", "ft_unreadable.m"}
    assert sorted(parsed) == sorted(
        str(srcdir.joinpath(*ref.split("/"))) for ref in index if ref not in unused
    )

    # A rebuild that re-reads the page reuses every parse and warns again; the
    # index stage reads the unreadable file again.
    parsed.clear()
    rst = srcdir / "index.rst"
    future = os.stat(rst).st_mtime_ns + 10**10
    os.utime(rst, ns=(future, future))
    app2 = make_app(srcdir=srcdir)
    app2.build()
    assert parsed == []
    assert warnings_of(app2) == expected
    assert (
        f"{latin1}:2: WARNING: [sphinxcontrib-matlabdomain] ft_latin1.m is not "
        "valid UTF-8"
    ) in app2.warning.getvalue()


def test_reference_to_placeholder_resolves(make_app, malformed):
    srcdir, _ = malformed
    (srcdir / "index.rst").write_text(
        RST + "\n.. mat:autoapplication:: ft_nometa.mlapp\n"
    )
    app = make_app(srcdir=srcdir)
    app.build()
    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert 'href="#mat-ft_nometa.mlapp"' in html


def test_file_warnings_are_suppressible(make_app, malformed):
    srcdir, _ = malformed
    app = make_app(
        srcdir=srcdir,
        confoverrides={"suppress_warnings": ["mat.parse_error", "mat.encoding"]},
    )
    app.build()
    assert {sub for sub, _ in warnings_of(app)} == {"invalid_matlab", "empty_code_file"}


def test_misnamed_classdef_warning_is_suppressible(make_app, malformed):
    srcdir, _ = malformed
    app = make_app(
        srcdir=srcdir, confoverrides={"suppress_warnings": ["mat.invalid_matlab"]}
    )
    app.build()
    assert "ft_misnamed.m" not in app.warning.getvalue()
    assert "MISNAMED HELP" in (app.outdir / "index.html").read_text(encoding="utf-8")


def test_configured_encoding_is_applied(make_app, tmp_path):
    write(
        tmp_path,
        {
            "conf.py": CONF + 'matlab_src_encoding = "cp1252"\n',
            "index.rst": "Index\n=====\n\n.. mat:autofunction:: ft_cp\n",
            "ft_cp.m": b"function ft_cp\n% COST \x80 5\nend\n",
        },
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    assert "COST € 5" in (app.outdir / "index.html").read_text(encoding="utf-8")
    assert "WARNING" not in app.warning.getvalue()


def test_unknown_encoding_is_a_config_error(make_app, tmp_path):
    write(tmp_path, {"conf.py": CONF, "index.rst": "Index\n=====\n"})
    for codec in ("no-such-codec", "rot13", "base64"):
        with pytest.raises(ConfigError, match=f"'{codec}' is not a known text"):
            make_app(srcdir=tmp_path, confoverrides={"matlab_src_encoding": codec})


@pytest.mark.skipif(not CAN_MAKE_UNREADABLE, reason="needs POSIX permissions")
def test_unreadable_folder_warns(make_app, tmp_path):
    write(
        tmp_path,
        {
            "conf.py": CONF,
            "index.rst": (
                "Index\n=====\n\n.. mat:autofunction:: ft_ok_function\n\n"
                ".. mat:autofolder:: locked/\n   :members:\n"
            ),
            "ft_ok_function.m": VALID["ft_ok_function.m"],
            "locked/inner.m": "function inner\nend\n",
        },
    )
    os.chmod(tmp_path / "locked", 0)
    try:
        app = make_app(srcdir=tmp_path)
        app.build()
    finally:
        os.chmod(tmp_path / "locked", 0o755)
    # Listed once: autofolder :members: does not list (and warn) again.
    assert warnings_of(app) == [("parse_error", "locked/")]
    assert "OK FUNCTION HELP" in (app.outdir / "index.html").read_text(encoding="utf-8")


LOCKED = {
    "conf.py": CONF,
    "index.rst": (
        "Index\n=====\n\n.. mat:autofunction:: ft_ok_function\n\n"
        ".. mat:autofolder:: locked/\n   :members:\n"
    ),
    "ft_ok_function.m": VALID["ft_ok_function.m"],
    "locked/inner.m": "function inner\nend\n",
    "locked/deeper/deep.m": "function deep\nend\n",
    # not counted: such folders are skipped anyway
    "locked/.cache/hidden.m": "function hidden\nend\n",
}


def assert_locked_warns(app):
    assert warnings_of(app) == [("parse_error", "locked/")]
    assert (
        "locked/: 2 entries cannot be accessed (Permission denied); they are not "
        "documented. [mat.parse_error]"
    ) in COLOR_RE.sub("", app.warning.getvalue())
    assert "OK FUNCTION HELP" in (app.outdir / "index.html").read_text(encoding="utf-8")
    index = app.env.get_domain("mat").data["index"]
    assert [r["reference"] for r in index.values()] == ["ft_ok_function.m"]


def test_inaccessible_entries_warn(make_app, tmp_path, monkeypatch):
    write(tmp_path, LOCKED)
    locked = str(tmp_path / "locked")
    stat = os.stat

    def denied(path, *args, **kwargs):
        if os.path.dirname(os.fspath(path)) == locked:
            raise PermissionError(13, "Permission denied", path)
        return stat(path, *args, **kwargs)

    monkeypatch.setattr(mat_types.os, "stat", denied)
    app = make_app(srcdir=tmp_path)
    app.build()
    assert_locked_warns(app)


@pytest.mark.skipif(not CAN_MAKE_UNREADABLE, reason="needs POSIX permissions")
def test_folder_listed_but_not_entered_warns(make_app, tmp_path):
    write(tmp_path, LOCKED)
    os.chmod(tmp_path / "locked", 0o444)
    try:
        app = make_app(srcdir=tmp_path)
        app.build()
    finally:
        os.chmod(tmp_path / "locked", 0o755)
    assert_locked_warns(app)


ONE_FUNCTION = {
    "conf.py": CONF,
    "index.rst": "Index\n=====\n\n.. mat:autofunction:: ft_ok_function\n",
    "ft_ok_function.m": VALID["ft_ok_function.m"],
}


def test_broken_link_is_skipped(make_app, tmp_path):
    write(tmp_path, ONE_FUNCTION)
    try:
        os.symlink(tmp_path / "gone.m", tmp_path / "dangling.m")
    except OSError:
        pytest.skip("cannot create symbolic links")
    app = make_app(srcdir=tmp_path)
    app.build()
    assert "WARNING" not in app.warning.getvalue()
    index = app.env.get_domain("mat").data["index"]
    assert [r["reference"] for r in index.values()] == ["ft_ok_function.m"]


def test_class_unreadable_at_indexing_renders(make_app, tmp_path, monkeypatch):
    # Portable twin of test_unreadable_class_and_function_render: the
    # placeholder of an unreadable file is not a class, yet autoclass shows it.
    write(
        tmp_path,
        {
            "conf.py": CONF,
            "index.rst": "Index\n=====\n\n.. mat:autoclass:: FtLocked\n   :members:\n",
            "FtLocked.m": "classdef FtLocked < handle\nend\n",
        },
    )
    read = mat_handlers.MFileHandler.read

    def locked(self, path, *args, **kwargs):
        if path.endswith("FtLocked.m"):
            raise PermissionError(13, "Permission denied")
        return read(self, path, *args, **kwargs)

    monkeypatch.setattr(mat_handlers.MFileHandler, "read", locked)
    app = make_app(srcdir=tmp_path)
    app.build()
    assert warnings_of(app) == [("parse_error", "FtLocked.m")]
    assert app.warning.getvalue().count("WARNING") == 1


def test_read_failure_while_parsing_is_not_cached(make_app, tmp_path, monkeypatch):
    write(tmp_path, ONE_FUNCTION)

    def locked(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(mat_handlers.MFileHandler, "parse", locked)
    app = make_app(srcdir=tmp_path)
    app.build()
    assert warnings_of(app) == [("parse_error", "ft_ok_function.m")]
    assert app.env.get_domain("mat").data["parse_cache"] == {}

    monkeypatch.undo()
    app2 = make_app(srcdir=tmp_path)
    app2.build()
    # The page that used the unreadable file is read again.
    assert app2.env.get_domain("mat").read_docnames == ["index"]
    html = (app2.outdir / "index.html").read_text(encoding="utf-8")
    assert "OK FUNCTION HELP" in html


@pytest.mark.skipif(not CAN_MAKE_UNREADABLE, reason="needs POSIX permissions")
def test_unreadable_class_and_function_render(make_app, tmp_path, parsed):
    write(
        tmp_path,
        {
            "conf.py": CONF,
            "index.rst": (
                "Index\n=====\n\n.. mat:autoclass:: FtLocked\n   :members:\n"
                "   :show-inheritance:\n\n.. mat:autofunction:: ft_locked\n\n"
                ".. mat:autoclass:: ft_trunc_class\n   :show-inheritance:\n"
            ),
            "FtLocked.m": "classdef FtLocked < handle\nend\n",
            "ft_locked.m": "function ft_locked(x)\nend\n",
            "ft_trunc_class.m": MALFORMED["ft_trunc_class.m"],
        },
    )
    locked = [tmp_path / "FtLocked.m", tmp_path / "ft_locked.m"]
    for path in locked:
        os.chmod(path, 0)
    try:
        app = make_app(srcdir=tmp_path)
        app.build()
        # A read failure is not cached: the index stage reads the file again
        # and the page is read again; nothing can be parsed.
        parsed.clear()
        app2 = make_app(srcdir=tmp_path)
        app2.build()
        assert parsed == []
        assert app2.env.get_domain("mat").read_docnames == ["index"]
    finally:
        for path in locked:
            os.chmod(path, 0o644)
    expected = [
        ("invalid_matlab", "ft_trunc_class.m"),
        ("parse_error", "FtLocked.m"),
        ("parse_error", "ft_locked.m"),
    ]
    assert warnings_of(app) == warnings_of(app2) == expected
    # Only the file warnings: the documenters accept the placeholders.
    assert app.warning.getvalue().count("WARNING") == len(expected)

    # Readable again, unchanged key: parsed and documented, no warning.
    parsed.clear()
    app3 = make_app(srcdir=tmp_path)
    app3.build()
    assert sorted(parsed) == sorted(str(p) for p in locked)
    assert warnings_of(app3) == [("invalid_matlab", "ft_trunc_class.m")]


@pytest.mark.skipif(sys.platform != "linux", reason="needs non-UTF-8 file names")
def test_undecodable_file_name_warns(make_app, tmp_path):
    write(
        tmp_path,
        {
            "conf.py": CONF,
            "index.rst": "Index\n=====\n\n.. mat:autofunction:: ft_ok_function\n",
            "ft_ok_function.m": VALID["ft_ok_function.m"],
        },
    )
    with open(os.path.join(os.fsencode(tmp_path), b"ft_caf\xe9.m"), "wb") as f:
        f.write(b"function y = f(x)\ny = x;\nend\n")
    app = make_app(srcdir=tmp_path)
    app.build()
    assert app.statuscode == 0
    assert warnings_of(app) == [("parse_error", "./")]
    assert "./: the name b'ft_caf\\xe9.m' is not valid UTF-8" in app.warning.getvalue()
    assert "OK FUNCTION HELP" in (app.outdir / "index.html").read_text(encoding="utf-8")
