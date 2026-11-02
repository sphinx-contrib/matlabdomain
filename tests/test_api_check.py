"""The matlab-api-check builder (plan.md Section 2.9, Phase 9)."""

import json
import shutil
import zipfile
from pathlib import Path

import pytest
from sphinx.errors import ConfigError

from sphinxcontrib import mat_api_check
from sphinxcontrib.mat_types import MatObject

ROOT = Path(__file__).parent / "roots" / "test_api_check"
BUILDER = "matlab-api-check"
ALL_RULES = mat_api_check.RULES

# (reference, rule) of every finding in the test root.
EXPECTED = {
    ("+pkg/Widget.m.undocumented", "method-description"),
    ("+pkg/Widget.m.noOutputs", "outputs"),
    ("+pkg/Widget.m.make", "inputs"),
    ("+pkg/Widget.m.make", "outputs"),
    ("@Shape/Shape.m.Shape", "method-description"),
    ("@Shape/area.m", "outputs"),
    ("bad-name.m", "description"),
    ("blankH1.m", "description"),
    ("noHelp.m", "description"),
    ("noHelp.m", "inputs"),
    ("noHelp.m", "outputs"),
    ("nvMissing.m", "name-value"),
    ("partialComments.m", "inputs"),
    ("private/helper.m", "description"),
    ("scriptNoHelp.m", "description"),
    ("varargs.m", "inputs"),
    ("varargs.m", "outputs"),
}


@pytest.fixture
def root(tmp_path):
    shutil.copytree(ROOT, tmp_path / "root")
    return tmp_path / "root"


def build(make_app, srcdir, **overrides):
    app = make_app(BUILDER, srcdir=srcdir, confoverrides=overrides, freshenv=True)
    app.build()
    return app


def report(app):
    return json.loads((app.outdir / "api-check.json").read_text(encoding="utf-8"))


def findings(app):
    return {(f["reference"], f["rule"]) for f in report(app)["findings"]}


def test_root_findings(make_app, root):
    app = build(make_app, root)
    assert app.statuscode == 1
    data = report(app)
    assert {(f["reference"], f["rule"]) for f in data["findings"]} == EXPECTED
    assert {f["severity"] for f in data["findings"]} == {"error"}
    by_key = {(f["reference"], f["rule"]): f for f in data["findings"]}
    assert by_key["+pkg/Widget.m.make", "inputs"] == {
        "reference": "+pkg/Widget.m.make",
        "name": "pkg.Widget.make",
        "kind": "method",
        "rule": "inputs",
        "severity": "error",
        "line": 33,
        "message": 'has no inputs section in its help (such as "Inputs:"), and '
        "these inputs have no arguments-block comment: n",
    }
    assert by_key["bad-name.m", "description"]["name"] is None
    assert by_key["scriptNoHelp.m", "description"]["line"] == 1
    assert by_key["partialComments.m", "inputs"]["message"].endswith(": b")
    assert by_key["nvMissing.m", "name-value"]["message"].endswith(
        "name-value arguments have no arguments-block comment: opts.Mode, opts.Tol"
    )
    summary = data["summary"]
    assert summary["checked"] == {
        "function": 11,
        "class": 2,
        "method": 8,
        "script": 2,
        "application": 0,
        "sidecar": 0,
    }
    assert summary["not_checked"] == {
        "ignored": 2,
        "hidden": 1,
        "unreadable": 0,
        "not_parsed": 0,
    }
    assert summary["rules"] == dict.fromkeys(ALL_RULES, "error")
    assert (summary["errors"], summary["warnings"]) == (17, 0)
    assert summary["findings"]["outputs"] == {"error": 5, "warning": 0}

    warnings = app.warning.getvalue()
    assert warnings.count("[mat.api_check]") == 17
    assert (
        f"{root / 'src' / 'noHelp.m'}:1: ERROR: [sphinxcontrib-matlabdomain] noHelp.m "
        "(noHelp): has no description: its help is empty or starts with a blank "
        "line [description]"
    ) in warnings

    text = (app.outdir / "api-check.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0].startswith(f"{root / 'src' / '+pkg' / 'Widget.m'}:20: error: ")
    assert lines[0].endswith("[method-description]")
    assert lines[18:21] == [
        "Checked: 11 functions, 2 classes, 8 methods, 2 scripts, 0 apps, 0 sidecars",
        "Not checked: 2 ignored, 1 hidden, 0 unreadable, 0 not parsed",
        "Findings: 17 errors, 0 warnings",
    ]
    assert lines[-3:] == [
        "  name-value (error): 1 errors, 0 warnings",
        "  sidecar-documented (error): 0 errors, 0 warnings",
        "  sidecar-links (error): 0 errors, 0 warnings",
    ]


@pytest.mark.parametrize(
    ("rules", "status", "expected"),
    [
        (dict.fromkeys(ALL_RULES, "warning"), 0, EXPECTED),
        (
            {**dict.fromkeys(ALL_RULES, "ignore"), "description": "error"},
            1,
            {f for f in EXPECTED if f[1] == "description"},
        ),
        ({"inputs": "warning", "outputs": "ignore"}, 1, None),
        (dict.fromkeys(ALL_RULES, "ignore"), 0, set()),
    ],
    ids=["warning", "only-description", "partial", "ignore"],
)
def test_severities(make_app, root, rules, status, expected):
    app = build(make_app, root, matlab_api_check_rules=rules)
    assert app.statuscode == status
    severities = {**dict.fromkeys(ALL_RULES, "error"), **rules}
    if expected is None:
        expected = {f for f in EXPECTED if severities[f[1]] != "ignore"}
    assert findings(app) == expected
    data = report(app)
    assert data["summary"]["rules"] == severities
    for finding in data["findings"]:
        assert finding["severity"] == severities[finding["rule"]]
    warnings = app.warning.getvalue()
    for severity, level in (("error", "ERROR"), ("warning", "WARNING")):
        count = sum(1 for f in data["findings"] if f["severity"] == severity)
        logged = warnings.count(f"{level}: [sphinxcontrib-matlabdomain]")
        if level == "WARNING":
            logged -= 1  # mat.not_callable of bad-name.m
        assert logged == count


def test_disabled(make_app, root):
    app = build(make_app, root, matlab_api_check_enabled=False)
    assert app.statuscode == 0
    data = report(app)
    assert data["findings"] == []
    assert data["summary"]["enabled"] is False
    assert data["summary"]["checked"] == dict.fromkeys(mat_api_check.KINDS, 0)
    assert "api_check" not in app.warning.getvalue()
    text = (app.outdir / "api-check.txt").read_text(encoding="utf-8")
    assert text.splitlines()[:2] == [
        "matlab_api_check_enabled is False: nothing was checked.",
        "Checked: 0 functions, 0 classes, 0 methods, 0 scripts, 0 apps, 0 sidecars",
    ]


@pytest.mark.parametrize(
    ("setting", "match"),
    [
        ('matlab_api_check_rules = ["inputs"]', "must be a dict"),
        ('matlab_api_check_rules = {"input": "error"}', "unknown rule 'input'"),
        ('matlab_api_check_rules = {"inputs": "fatal"}', "severity of 'inputs'"),
        ('matlab_api_check_ignore_patterns = "tests/**"', "must be a list"),
        ('matlab_api_check_ignore_patterns = ["/abs/**"]', "must be relative"),
        (r'matlab_api_check_ignore_patterns = ["a\\b.m"]', "must use '/'"),
    ],
    ids=[
        "not-dict",
        "unknown-rule",
        "severity",
        "patterns-str",
        "absolute",
        "backslash",
    ],
)
def test_config_errors(make_app, root, setting, match):
    conf = root / "conf.py"
    conf.write_text(f"{conf.read_text()}{setting}\n")
    with pytest.raises(ConfigError, match=match):
        make_app(BUILDER, srcdir=root)


def test_options_do_not_reread_pages(make_app, root):
    build(make_app, root)
    app = make_app(
        BUILDER,
        srcdir=root,
        confoverrides={
            "matlab_api_check_rules": {"description": "warning"},
            "matlab_api_check_ignore_patterns": ["**"],
        },
    )
    app.build()
    assert "0 added, 0 changed, 0 removed" in app.status.getvalue()
    assert findings(app) == set()
    assert report(app)["summary"]["not_checked"]["ignored"] == 17


def test_html_build_is_unchanged(make_app, root):
    app = make_app("html", srcdir=root, freshenv=True)
    app.build()
    assert app.statuscode == 0
    assert "api_check" not in app.warning.getvalue()
    assert not (app.outdir / "api-check.json").exists()


def has(rule, help_text, names=()):
    return mat_api_check.has_section(rule, help_text, names)


@pytest.mark.parametrize(
    "line",
    [
        "Inputs:",
        "  INPUT",
        "Input Arguments",
        "input(s): x - data",
        "Arguments",
        "Parameters",
        "params:",
        "Required inputs:",
        "Optional parameters:",
        "Input Arguments (Name-Value Arguments):",
        "Inputs (all optional except H, C, A and L):",
        "Parameters and their meaning:",
        "Inputs :",
        "Inputs : S, the spectra",
        "Inputs:ROIS3D1, ROIS3D2 are indexes",
    ],
)
def test_input_headers(line):
    assert has("inputs", f"F Help.\n\n{line}\n")


@pytest.mark.parametrize(
    "line",
    [
        "Outputs:",
        "OUTPUT",
        "Output(s):",
        "Output Arguments:",
        "Returns",
        "Return values:",
        "Return arguments:",
        "Outputs (all optional):",
    ],
)
def test_output_headers(line):
    assert has("outputs", f"F Help.\n\n{line}\n")


@pytest.mark.parametrize(
    "line",
    [
        "Name-Value Arguments:",
        "name value pairs",
        "Name/Value Pair Arguments:",
        "Optional Name-Value Pairs:",
        "Name-Value Options:",
        "OPTIONS - Name-value arguments:",
        "Options::",
        "OPTIONS",
        "Optional inputs:",
        "Input Arguments (Name-Value Arguments):",
    ],
)
def test_name_value_headers(line):
    assert has("name-value", f"F Help.\n\n{line}\n")


@pytest.mark.parametrize(
    "text",
    [
        "Y = F(X) returns the inputs doubled.",
        "The inputs are scalars.",
        "Outputs are cached",
        "Returns the sum.",
        "See also options, inputs",
        "Inputs, see below:",
        # a wrapped prose word
        "It supports the following\noptions\n  cfg.a = 1",
    ],
)
def test_prose_is_no_header(text):
    help_text = f"F Help.\n{text}\n"
    assert not any(has(rule, help_text) for rule in mat_api_check.SECTIONS)


@pytest.mark.parametrize(
    "help_text",
    [
        "Input\nF Help.",
        "F Help.\nWrapped prose\nParameters\n----------\nx : data",
        "F Help.\nx : data\nOUTPUT\n  y : result",
        "F Help.\nsome text\noutputs\n-------",
    ],
    ids=["first-line", "underlined", "capitalized", "lowercase-underlined"],
)
def test_label_alone(help_text):
    assert has("inputs", help_text) or has("outputs", help_text)


def test_argument_named_like_a_label():
    # function data = zlibencode(input): "input: ..." is an entry
    help_text = "F Help.\n\ninput: the original data\nOutput:\n  data"
    assert not has("inputs", help_text, {"input", "data"})
    assert has("outputs", help_text, {"input", "data"})
    assert has("inputs", help_text)
    # numpy style: function obj = f(output)
    assert not has("outputs", "F Help.\n\noutput : the result", {"output", "obj"})
    # function y = f(inputs): "INPUTS:" ends its line, so it is a header
    assert has("inputs", "F Help.\nINPUTS:\n  inputs: levels", {"inputs", "y"})


@pytest.mark.parametrize(
    ("docstring", "expected"),
    [(None, False), ("", False), ("\nBody", False), ("  \nBody", False), ("H1", True)],
)
def test_has_description(docstring, expected):
    assert mat_api_check.has_description(docstring) is expected


def test_unreadable_record_is_not_checked():
    checker = mat_api_check._Checker(None, mat_api_check.DEFAULT_RULES, [])
    checker.check("x.m", {"reference": "x.m", "unreadable": True})
    assert checker.not_checked["unreadable"] == 1
    assert checker.findings == []


def mlapp(path, description):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "metadata/coreProperties.xml",
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/'
            '2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f"<dc:description>{description}</dc:description></cp:coreProperties>",
        )
        z.writestr(
            "metadata/appMetadata.xml",
            '<n:AppMetadata xmlns:n="http://schemas.mathworks.com/appDesigner/app/'
            '2017/appMetadata"/>',
        )


CONF = (
    'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "."\n'
)
# A class by its first line, a script for tree-sitter (mat.invalid_matlab).
BROKEN = "classdef {name}\n% {name} HELP\nmethods\nfunction obj = {name}()\nend\n"


def test_apps_failed_parses_and_parse_warnings(make_app, tmp_path):
    (tmp_path / "conf.py").write_text(CONF)
    (tmp_path / "index.rst").write_text("Index\n=====\n\n.. mat:autoscript:: Used.m\n")
    (tmp_path / "Used.m").write_text(BROKEN.format(name="Used"))
    (tmp_path / "Unused.m").write_text(BROKEN.format(name="Unused"))
    (tmp_path / "corrupt.mlapp").write_bytes(b"not a zip file")
    mlapp(tmp_path / "Described.mlapp", "An app.")
    mlapp(tmp_path / "Bare.mlapp", "")
    app = build(make_app, tmp_path)
    # The invalid classes are what tree-sitter parsed: scripts without help.
    expected = {(name, "description") for name in ("Bare.mlapp", "Used.m", "Unused.m")}
    assert findings(app) == expected
    data = report(app)
    assert data["findings"][0]["kind"] == "application"
    assert data["findings"][0]["line"] is None
    assert data["summary"]["checked"]["application"] == 2
    assert data["summary"]["checked"]["script"] == 2
    assert data["summary"]["not_checked"]["not_parsed"] == 1
    warnings = app.warning.getvalue()
    # No location for an app: the message starts the line.
    assert "ERROR: [sphinxcontrib-matlabdomain] Bare.mlapp (Bare): has no" in warnings
    # Parse warnings: once each, also for files no page uses.
    assert warnings.count("Used.m: its first line of code makes it a class") == 1
    assert warnings.count("Unused.m: its first line of code makes it a class") == 1
    assert warnings.count("corrupt.mlapp cannot be parsed") == 1

    # A second build reads no page and checks everything again.
    app = make_app(BUILDER, srcdir=tmp_path)
    app.build()
    assert "0 added, 0 changed, 0 removed" in app.status.getvalue()
    assert findings(app) == expected
    warnings = app.warning.getvalue()
    assert warnings.count("Used.m: its first line of code makes it a class") == 1
    assert warnings.count("Unused.m: its first line of code makes it a class") == 1


def test_no_project_root(make_app, tmp_path):
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
    )
    (tmp_path / "index.rst").write_text("Index\n=====\n")
    app = build(make_app, tmp_path)
    assert app.statuscode == 0
    assert report(app)["findings"] == []
    # Sphinx 8.0 resolves and "writes" each page; nothing is written.
    assert app.builder.get_target_uri("index") == ""
    app.builder.write_doc("index", None)
    assert sorted(p.name for p in app.outdir.iterdir()) == [
        "api-check.json",
        "api-check.txt",
    ]


def test_parser_records_name_value_and_lines():
    path = ROOT / "src"
    func = MatObject.parse_mfile(str(path / "argComments.m"), "argComments", "./")
    assert func.line == 1
    assert func.name_value == {"opts.Tol": "the tolerance"}
    assert func.args["x"]["docstring"] == "the data"
    assert func.retv["y"]["docstring"] == "the result"
    cls = MatObject.parse_mfile(str(path / "+pkg" / "Widget.m"), "Widget", "+pkg/")
    assert cls.line == 1
    assert cls.methods["make"].line == 33
    assert cls.methods["documented"].name_value == {}
