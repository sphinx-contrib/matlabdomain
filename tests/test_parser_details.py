"""Parser details: help placement of members, line endings, syntax errors."""

import pytest
from tree_sitter import Parser

from sphinxcontrib import mat_types
from sphinxcontrib.mat_classify import decode_source
from sphinxcontrib.mat_tree_sitter_parser import ML_LANG, first_error

ARGUMENTS = """\
function [o1, o2] = fargs(a, b, c, d, e, f, g, opts)
% FARGS HELP
arguments
    a double; % semicolon A
    % before B
    b double
    c double % inline C
    % below C, before D
    d double

    % before E, after a blank line
    e double
    f double;
    % below F

    g double;

    % after G and a blank line

    opts.Name double = 1 % name-value
end
arguments (Output)
    % before O1
    o1 double
    % below O1

    o2 double
end
arguments
end
end
"""

CLASS = """\
classdef (Sealed = false, Hidden) Members
properties (Hidden = false)
    p1 = 1; % semicolon P1
    % before P2
    p2
    p3 % inline P3
    % below P3, before P4
    p4

    % before P5, after a blank line
    p5
    p6@double vector
    p7
    % below P7

    p8
    p9 = 2;
    % below P9
end
properties
    % only a comment
end
enumeration
    % before E0
    E0
    E1 % inline E1
    % below E1, before E2
    E2
    E3
    % below E3

    E4
    E5
    % between E5 and E6
    E6

    % after E6 and a blank line

    E7
    E8 % inline E8
    E9
end
enumeration
    % only a comment
end
end
"""


def parse(tmp_path, name, text):
    path = tmp_path / f"{name}.m"
    path.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)
    return mat_types.MatObject.parse_mfile(str(path), name, "./")


def docstrings(members):
    return {name: member["docstring"] for name, member in members.items()}


def test_argument_help(tmp_path):
    obj = parse(tmp_path, "fargs", ARGUMENTS)
    assert docstrings(obj.args) == {
        "a": "semicolon A",
        "b": "before B",
        "c": "inline C",
        "d": "below C, before D",
        "e": "before E, after a blank line",
        "f": "below F",
        "g": None,
        "opts": "name-value",
    }
    # A comment before an argument wins over the one below the previous.
    assert docstrings(obj.retv) == {"o1": "before O1", "o2": None}
    assert obj.retv["o1"]["attrs"] == {"Output": None}


def test_property_and_enumeration_help(tmp_path):
    obj = parse(tmp_path, "Members", CLASS)
    assert obj.attrs == {"Sealed": False, "Hidden": True}
    assert docstrings(obj.properties) == {
        "p1": "semicolon P1",
        "p2": "before P2",
        "p3": "inline P3",
        "p4": "below P3, before P4",
        "p5": "before P5, after a blank line",
        "p6": None,
        "p7": "below P7",
        "p8": None,
        "p9": "below P9",
    }
    assert obj.properties["p1"]["attrs"] == {"Hidden": False}
    # old-style ``name@type size`` without a default lost its type and size
    p6 = obj.properties["p6"]
    assert (p6["type"], p6["size"]) == ("double", (":", "1"))
    assert docstrings(obj.enumerations) == {
        "E0": "before E0",
        "E1": "inline E1",
        "E2": "below E1, before E2",
        "E3": "below E3",
        "E4": None,
        "E5": "between E5 and E6",
        "E6": "between E5 and E6",
        "E7": None,
        "E8": "inline E8",
        "E9": None,
    }


def test_attribute_value_forms(tmp_path):
    # MATLAB R2026a and R2026b: ``~Name`` is ``Name = false``; a value is a
    # logical expression, so ``0``, ``1`` and ``~true`` are logical values.
    source = (
        "classdef (~Sealed, Abstract = 0) Forms\n"
        "properties (~Hidden, Constant = 1)\n    a\nend\n"
        "properties (Hidden = ~true, Transient = ~false)\n    b\nend\n"
        "properties (Hidden = 0x1, Access = ~private)\n    c\nend\n"
        "methods (~Static, Access = protected)\n"
        "    function m(obj)\n    end\n"
        "end\nend\n"
    )
    obj = parse(tmp_path, "Forms", source)
    assert obj.source_warnings == []
    assert obj.attrs == {"Sealed": False, "Abstract": False}
    assert obj.properties["a"]["attrs"] == {"Hidden": False, "Constant": True}
    assert obj.properties["b"]["attrs"] == {"Hidden": False, "Transient": True}
    # Other literals and expressions keep their text.
    assert obj.properties["c"]["attrs"] == {"Hidden": "0x1", "Access": "~private"}
    assert obj.methods["m"].attrs == {"Static": False, "Access": "protected"}


@pytest.mark.parametrize(
    ("source", "help"),
    [
        # MATLAB R2026a: a continued line joins the declaration, so a comment
        # on it is no help; the next block is (as on the declaration line).
        ("classdef C < handle ...\n\n% C HELP\nend\n", "C HELP"),
        ("classdef C < handle ... words\n% C HELP\nend\n", ""),
        ("classdef C < handle ...\n% C HELP\n\n% C SECOND\nend\n", "C SECOND"),
        ("classdef C ...\n\n% C HELP\nend\n", "C HELP"),
    ],
    ids=["blank", "comment", "next-block", "no-superclass"],
)
def test_continuation_after_class_header(tmp_path, source, help):
    obj = parse(tmp_path, "C", source)
    assert isinstance(obj, mat_types.MatClass)
    assert obj.docstring == help


@pytest.mark.parametrize(
    "source",
    [
        b"function y = f(x)\n% F HELP\ny = x",
        b"classdef C\n properties\n  a double {}\n end\nend\n",
        b"classdef E\n enumeration\n  Positive ()\n end\nend\n",
        b"y = x .';\n",
        b"% one\r\n% two\r\nx = 1;\r\n",
    ],
    ids=[
        "eof-without-newline",
        "empty-validators",
        "empty-enum-args",
        "spaced-transpose",
        "crlf-comments",
    ],
)
def test_grammar_fixes_of_1_3_3(source):
    # tree-sitter-matlab 1.3.2 wheels shipped a stale parser.c (upstream #176).
    root = Parser(ML_LANG).parse(source).root_node
    assert first_error(root) is None
    assert not root.has_error


def test_empty_validators_and_enum_args(tmp_path):
    # 1.3.2 parsed ``{}`` and ``()`` as errors: validators and args ``['']``.
    cls = parse(tmp_path, "C", "classdef C\n properties\n  a double {}\n end\nend\n")
    assert cls.properties["a"]["validators"] is None
    enum = parse(tmp_path, "E", "classdef E\n enumeration\n  Positive ()\n end\nend\n")
    assert enum.enumerations["Positive"]["args"] is None
    assert cls.source_warnings == enum.source_warnings == []


def test_section_percent_signs(tmp_path):
    # MATLAB R2026a and R2026b ``help`` drops ``%%`` (a section start) or one
    # ``%``, so separator lines of ``%`` keep all but two.
    lines = ["% first", "%%", "%% two", "%%x", "%%%", "%%% three", "  %% indented"]
    lines += ["%%%%", "%  keep", "%%  dbl", "%%\ttab"]
    obj = parse(tmp_path, "pct", "function pct\n" + "\n".join(lines) + "\nend\n")
    assert obj.docstring == (
        "first\n\ntwo\nx\n%\n% three\nindented\n%%\n keep\n dbl\n\ttab"
    )


def test_cr_only_line_endings(tmp_path):
    # MATLAB R2026a ends lines at a lone CR (help shows both lines).
    obj = parse(
        tmp_path, "cr", b"function y = cr(x)\r% CR HELP\r% second\ry = x;\rend\r"
    )
    assert obj.docstring == "CR HELP\nsecond"
    assert obj.args == {"x": {}}
    _, problem = decode_source(b"x = 1;\r% caf\xe9\r")
    assert problem is not None
    assert problem[1] == 1
    _, problem = decode_source(b"x = 1;\r\n% caf\xe9\r\n")
    assert problem is not None
    assert problem[1] == 1


def test_leading_line_continuation(tmp_path):
    obj = parse(tmp_path, "lc", "...\nfunction lc\n% LC HELP\nend\n")
    assert isinstance(obj, mat_types.MatFunction)
    assert obj.docstring == "LC HELP"


def test_class_without_a_name_is_a_placeholder(tmp_path):
    obj = parse(tmp_path, "C1", "classdef 1A\n% HELP\nend\n")
    assert isinstance(obj, mat_types.MatClass)
    assert obj.docstring is None
    assert obj.source_warnings == [
        (
            "parse_error",
            "cannot be parsed (ValueError: tree-sitter found no class name); it is "
            "documented without content. First syntax error: line 1, column 10.",
            0,
        )
    ]


def test_file_wrapped_in_an_error_is_a_script(tmp_path):
    obj = parse(tmp_path, "wrapped", "if x\n y = 1;\n")
    assert isinstance(obj, mat_types.MatScript)
    assert obj.docstring is None


NESTED = """\
function out = outer(x, opts)
% OUTER HELP
arguments
    x
    opts.First = 1 % first
    opts.Second = 2 % second
    opts.Third = 3 % third
end

% Copyright notice.

%%%%%%%%%%%%%%%%%%%%
% DEVELOPER NOTE
%%%%%%%%%%%%%%%%%%%%
y = inner(x);
    function z = inner(w, v)
    % INNER HELP
    arguments
        w double % W
        v = 1
    end
    z = w;
    end
end
"""


def test_function_help_and_signature_are_its_own(tmp_path):
    # tree-sitter returns the comment and argument captures in no fixed
    # order (a later block came back about every other parse), and used to
    # include the nested function's. Parse several times.
    method = NESTED.replace("\n", "\n    ").replace("outer", "m")
    source = f"classdef K\n  methods\n    {method}\n  end\nend\n"
    for _ in range(8):
        obj = parse(tmp_path, "outer", NESTED)
        assert obj.docstring == "OUTER HELP"
        assert list(obj.retv) == ["out"]
        assert list(obj.args) == ["x", "opts"]
        # one entry for all name-value arguments: the last one's help
        assert obj.args["opts"]["docstring"] == "third"
        cls = parse(tmp_path, "K", source)
        m = cls.methods["m"]
        assert m.docstring == "OUTER HELP"
        assert (list(m.retv), list(m.args)) == (["out"], ["x", "opts"])


def tree(source):
    return Parser(ML_LANG).parse(source.encode()).root_node


@pytest.mark.parametrize(
    ("source", "error"),
    [
        ("x = 1;\n", None),
        ("function f(x\nend\n", (0, 12)),  # MISSING ")"
        ("x = 1;\ny = 2;\nfunction (\n", (2, 0)),
        # an ERROR around the class, with the real problem nested in it
        ("% c\nclassdef A\n methods\n  function f(\n end\nend\n", (3, 12)),
        # an ERROR wrapping the file, nothing nested: unknown location
        (
            "classdef B\n methods\n  function f(o)\n   x = [1 2;\n  end\n end\nend\n",
            None,
        ),
        ("% c\ny = (1 + 2\n", None),
    ],
    ids=["valid", "missing", "error", "nested", "root", "wrapped"],
)
def test_first_error(source, error):
    assert first_error(tree(source)) == error
