"""The matlab-api-check builder (plan.md Section 2.9, Phase 9)."""

import json
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from sphinx.cmd.build import build_main
from sphinx.errors import ConfigError

from sphinxcontrib import mat_api_check
from sphinxcontrib.mat_types import MatObject

ROOT = Path(__file__).parent / "roots" / "test_api_check"
SIMULINK = Path(__file__).parent / "simulink" / "fixtures" / "R2026b" / "slx"
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
# The findings of the rules that warn by default: no help has an example.
WARNED = {
    *(
        (ref, "example")
        for ref in (
            "+pkg/Widget.m",
            "@Shape/Shape.m",
            "argComments.m",
            "bad-name.m",
            "blankH1.m",
            "good.m",
            "ignoredInput.m",
            "noHelp.m",
            "numpyStyle.m",
            "nvMissing.m",
            "partialComments.m",
            "private/helper.m",
            "scriptNoHelp.m",
            "scriptWithHelp.m",
            "varargs.m",
        )
    ),
    *(
        (ref, "method-example")
        for ref in (
            "+pkg/Widget.m.documented",
            "+pkg/Widget.m.undocumented",
            "+pkg/Widget.m.noOutputs",
            "+pkg/Widget.m.make",
            "+pkg/Widget.m.explicit",
            "@Shape/area.m",
        )
    ),
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
    assert {(f["reference"], f["rule"]) for f in data["findings"]} == EXPECTED | WARNED
    severity = {(f["reference"], f["rule"]): f["severity"] for f in data["findings"]}
    assert {key for key, s in severity.items() if s == "error"} == EXPECTED
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
        "property": 1,
        "event": 0,
        "script": 2,
        "application": 0,
        "sidecar": 0,
    }
    assert summary["not_checked"] == {
        "ignored": 2,
        "hidden": 1,
        "unreadable": 0,
        "not_parsed": 0,
        "simulink_files": 0,
    }
    assert summary["rules"] == mat_api_check.DEFAULT_RULES
    assert "selection" not in summary
    assert (summary["errors"], summary["warnings"]) == (17, 21)
    assert summary["findings"]["outputs"] == {"error": 5, "warning": 0}

    warnings = app.warning.getvalue()
    assert warnings.count("[mat.api_check]") == 38
    assert (
        f"{root / 'src' / 'noHelp.m'}:1: ERROR: [sphinxcontrib-matlabdomain] noHelp.m "
        "(noHelp): has no description: its help is empty or starts with a blank "
        "line [description]"
    ) in warnings

    text = (app.outdir / "api-check.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0].startswith(f"{root / 'src' / '+pkg' / 'Widget.m'}:1: warning: ")
    assert lines[0].endswith("[example]")
    assert lines[39:42] == [
        "Checked: 11 functions, 2 classes, 8 methods, 1 properties, 0 events, "
        "2 scripts, 0 apps, 0 sidecars",
        "Not checked: 2 ignored, 1 hidden, 0 unreadable, 0 not parsed, "
        "0 simulink files",
        "Findings: 17 errors, 21 warnings",
    ]
    assert lines[-5:] == [
        "  name-value (error): 1 errors, 0 warnings",
        "  example (warning): 0 errors, 15 warnings",
        "  method-example (warning): 0 errors, 6 warnings",
        "  sidecar-documented (error): 0 errors, 0 warnings",
        "  sidecar-links (error): 0 errors, 0 warnings",
    ]


@pytest.mark.parametrize(
    ("rules", "status", "expected"),
    [
        (dict.fromkeys(ALL_RULES, "warning"), 0, EXPECTED | WARNED),
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
    severities = {**mat_api_check.DEFAULT_RULES, **rules}
    if expected is None:
        expected = {f for f in EXPECTED | WARNED if severities[f[1]] != "ignore"}
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


@pytest.mark.parametrize(
    ("setting", "match"),
    [
        ('matlab_api_check_rules = ["inputs"]', "must be a dict"),
        ('matlab_api_check_rules = {"input": "error"}', "unknown rule 'input'"),
        ('matlab_api_check_rules = {"inputs": "fatal"}', "severity of 'inputs'"),
        ('matlab_api_check_ignore_patterns = "tests/**"', "must be a list"),
        ('matlab_api_check_ignore_patterns = ["/abs/**"]', "must be relative"),
        (r'matlab_api_check_ignore_patterns = ["a\\b.m"]', "must use '/'"),
        ("matlab_api_check_files = 3", "must be None, a list"),
        ('matlab_api_check_files = ["/abs.m"]', "must be relative"),
        ('matlab_api_check_files = ["../x.m"]', "leaves matlab_src_code_project_root"),
        (r'matlab_api_check_files = ["a\\b.m"]', "must use '/'"),
        ('matlab_api_check_files = ["good.m", ""]', "is not a glob pattern"),
    ],
    ids=[
        "not-dict",
        "unknown-rule",
        "severity",
        "patterns-str",
        "absolute",
        "backslash",
        "files-type",
        "files-absolute",
        "files-outside",
        "files-backslash",
        "files-empty-entry",
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


@pytest.mark.parametrize(
    "text",
    [
        "Example:",
        "Examples:",
        "EXAMPLES",
        "Example(s):",
        "Example 1:",
        "Example: y = f(2)",
        "Examples::",
        "Usage:",
        "Example usage:",
        "Usage examples:",
        "Example of use:",
        "Examples\n--------\n>>> f(1)",
        ".. rubric:: Examples",
        ".. rubric:: Usage",
    ],
)
def test_example_headers(text):
    assert mat_api_check.has_example(f"F Help.\n\n{text}\n")


@pytest.mark.parametrize(
    "text",
    [
        None,
        "F Help.",
        "F Help. For example, f(2) is 4.",
        "F Help.\nIts typical\nusage\nis short.",
        "F Help.\n.. rubric:: Notes",
    ],
)
def test_no_example(text):
    assert not mat_api_check.has_example(text)


RULES_SRC = {
    "withExample.m": "function withExample\n% WITHEXAMPLE Help.\n%\n% Example:\n"
    "%   withExample\nend\n",
    "noExample.m": "function noExample\n% NOEXAMPLE Help.\nend\n",
    "scriptUsage.m": "% SCRIPTUSAGE Help.\n%\n% Usage:\n%   scriptUsage\nx = 1;\n",
    "Thing.m": """classdef Thing < handle
% THING Help.
%
% Examples
% --------
%   t = Thing();
    properties
        Documented % a comment
        Undocumented

        % a comment above
        Above
        Skipped
    end
    properties (Constant)
        LIMIT = 3
    end
    properties (Access = private)
        Secret
    end
    properties (GetAccess = protected)
        Guarded
    end
    properties (Hidden)
        Tag
    end
    methods
        function obj = Thing()
            % THING Constructor, no example needed.
        end
        function run(obj)
            % RUN Run it.
            %
            % .. rubric:: Example
            %
            %    t.run()
        end
        function stop(obj)
            % STOP Stop it.
        end
    end
end
""",
}


def test_example_and_property_rules(make_app, tmp_path):
    for name, text in RULES_SRC.items():
        (tmp_path / name).write_text(text)
    (tmp_path / "conf.py").write_text(
        f"{CONF}matlab_api_check_ignore_patterns = ['Thing.m.Skipped']\n"
    )
    (tmp_path / "index.rst").write_text("Index\n=====\n")
    app = build(make_app, tmp_path)
    assert app.statuscode == 0
    assert findings(app) == {
        ("noExample.m", "example"),
        ("Thing.m.stop", "method-example"),
        ("Thing.m.Undocumented", "property-description"),
        ("Thing.m.LIMIT", "property-description"),
    }
    data = report(app)
    by_ref = {f["reference"]: f for f in data["findings"]}
    assert by_ref["Thing.m.Undocumented"] == {
        "reference": "Thing.m.Undocumented",
        "name": "Thing.Undocumented",
        "kind": "property",
        "rule": "property-description",
        "severity": "warning",
        "line": 9,
        "message": "has no description: no comment above, after or below it",
    }
    assert by_ref["noExample.m"]["message"] == (
        'has no example section in its help (such as "Example:")'
    )
    summary = data["summary"]
    assert summary["checked"]["property"] == 4
    assert summary["not_checked"]["ignored"] == 1
    assert (summary["errors"], summary["warnings"]) == (0, 4)

    app = build(
        make_app,
        tmp_path,
        matlab_api_check_rules={"example": "error", "property-description": "ignore"},
    )
    assert app.statuscode == 1
    assert findings(app) == {
        ("noExample.m", "example"),
        ("Thing.m.stop", "method-example"),
    }


def test_unreadable_record_is_not_checked():
    checker = mat_api_check._Checker(None, mat_api_check.DEFAULT_RULES, [])
    checker.check("x.m", {"reference": "x.m", "unreadable": True})
    assert checker.not_checked["unreadable"] == 1
    assert checker.findings == []


def test_hidden_class_is_not_checked(make_app, tmp_path):
    sources = {
        "Shown.m": "classdef Shown\n% SHOWN Help.\n%\n% Example:\n%   Shown\nend\n",
        "Secret.m": "classdef (Hidden) Secret\nproperties\n    p\nend\nmethods\n"
        "    function r = run(obj, x)\n    end\nend\nend\n",
        "@Vault/Vault.m": "classdef (Hidden = true) Vault\nmethods\n"
        "    r = open(obj, x)\nend\nend\n",
        "@Vault/open.m": "function r = open(obj, x)\nend\n",
    }
    for name, text in sources.items():
        (tmp_path / name).parent.mkdir(exist_ok=True)
        (tmp_path / name).write_text(text)
    (tmp_path / "conf.py").write_text(CONF)
    (tmp_path / "index.rst").write_text("Index\n=====\n")
    app = build(make_app, tmp_path)
    assert app.statuscode == 0
    data = report(app)
    assert data["findings"] == []
    assert data["summary"]["checked"]["class"] == 1
    assert data["summary"]["checked"]["method"] == 0
    assert data["summary"]["not_checked"]["hidden"] == 2


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


def test_simulink_files_pass_through(make_app, tmp_path):
    (tmp_path / "conf.py").write_text(CONF)
    (tmp_path / "index.rst").write_text("Index\n=====\n")
    for name in ("probeModel", "probeLib"):
        shutil.copyfile(SIMULINK / f"{name}.slx", tmp_path / f"{name}.slx")
    (tmp_path / "lfs.slx").write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:00\nsize 1\n"
    )
    app = build(make_app, tmp_path)
    assert findings(app) == set()
    not_checked = report(app)["summary"]["not_checked"]
    assert not_checked["simulink_files"] == 2
    assert not_checked["not_parsed"] == 1


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
    expected |= {("Used.m", "example"), ("Unused.m", "example")}
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


# --- matlab_api_check_files ---------------------------------------------------

#: the files of the test root: 18, of which the check sees all by default
ROOT_FILES = 18


def file_of(ref):
    """Return the file reference of a file, method or property reference."""
    head, sep, _ = ref.partition(".m.")
    return f"{head}.m" if sep else ref


def text_lines(app):
    return (app.outdir / "api-check.txt").read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize(
    ("files", "entries", "selected"),
    [
        (
            ["noHelp.m", "@Shape/area.m", "+pkg/Widget.m"],
            ["noHelp.m", "@Shape/area.m", "+pkg/Widget.m"],
            {"noHelp.m", "@Shape/area.m", "+pkg/Widget.m"},
        ),
        (["@Shape/Shape.m"], ["@Shape/Shape.m"], {"@Shape/Shape.m"}),
        (["@Shape/area.m"], ["@Shape/area.m"], {"@Shape/area.m"}),
        (
            ["@Shape/", "private/*.m", "**/good.m", "./good.m", "good.m"],
            ["@Shape/", "private/*.m", "**/good.m", "good.m"],
            {"@Shape/area.m", "@Shape/Shape.m", "private/helper.m", "good.m"},
        ),
    ],
    ids=["exact", "classdef-of-class-folder", "method-file", "globs"],
)
def test_selected_files(make_app, root, files, entries, selected):
    app = build(make_app, root, matlab_api_check_files=files)
    expected = {f for f in EXPECTED | WARNED if file_of(f[0]) in selected}
    assert findings(app) == expected
    errors = {f for f in expected if f in EXPECTED}
    assert app.statuscode == (1 if errors else 0)
    summary = report(app)["summary"]
    assert summary["selection"] == {
        "entries": entries,
        "selected": len(selected),
        "unmatched": [],
        "ignore_unmatched": False,
    }
    assert summary["not_checked"]["not_selected"] == ROOT_FILES - len(selected)
    assert summary["errors"] == len(errors)
    assert (
        f"Selected: {len(selected)} of {ROOT_FILES} files by {len(entries)} "
        "entries, 0 matching no file"
    ) in text_lines(app)


def test_patterns_are_taken_in_nfc_form(tmp_path):
    # "e" + U+0301 (NFD), as macOS or a pasted name may give it, selects the
    # NFC references of the index.
    listing = tmp_path / "files.txt"
    listing.write_text("+cafe\u0301/b.m\n", encoding="utf-8")
    config = SimpleNamespace(
        matlab_api_check_ignore_patterns=["cafe\u0301.m"],
        matlab_api_check_files=["+cafe\u0301/a.m"],
        matlab_api_check_files_from=str(listing),
    )
    assert mat_api_check.ignore_patterns(config) == ["caf\xe9.m"]
    assert mat_api_check.selected_files(config) == ["+caf\xe9/a.m", "+caf\xe9/b.m"]


def test_selected_file_members(make_app, root):
    app = build(
        make_app,
        root,
        matlab_api_check_files=["noHelp.m", "@Shape/area.m", "+pkg/Widget.m"],
    )
    summary = report(app)["summary"]
    # Widget.m: the class, its property and six methods; area.m is a method.
    assert summary["checked"] == {
        "function": 1,
        "class": 1,
        "method": 7,
        "property": 1,
        "event": 0,
        "script": 0,
        "application": 0,
        "sidecar": 0,
    }
    assert summary["not_checked"] == {
        "ignored": 1,  # +pkg/Widget.m.skipMe
        "hidden": 0,
        "unreadable": 0,
        "not_parsed": 0,
        "simulink_files": 0,
        "not_selected": 15,
    }
    assert text_lines(app)[-15:-12] == [
        "Selected: 3 of 18 files by 3 entries, 0 matching no file",
        "Checked: 1 functions, 1 classes, 7 methods, 1 properties, 0 events, "
        "0 scripts, 0 apps, 0 sidecars",
        "Not checked: 1 ignored, 0 hidden, 0 unreadable, 0 not parsed, "
        "0 simulink files, 15 not selected",
    ]


def test_selected_files_exclusions(make_app, root):
    # Selected but ignored or hidden: counted, not checked, not unmatched.
    app = build(
        make_app, root, matlab_api_check_files=["ignored/skipped.m", "Contents.m"]
    )
    assert app.statuscode == 0
    assert findings(app) == set()
    summary = report(app)["summary"]
    assert summary["checked"] == dict.fromkeys(mat_api_check.KINDS, 0)
    assert summary["not_checked"] == {
        "ignored": 1,
        "hidden": 1,
        "unreadable": 0,
        "not_parsed": 0,
        "simulink_files": 0,
        "not_selected": 16,
    }
    assert summary["selection"]["unmatched"] == []


def test_unmatched_selection(make_app, root):
    (root / "src" / "notes.txt").write_text("Not a MATLAB file.\n")
    files = ["good.m", "missing.m", "src/good.m", "+pkg", "notes.txt", "*.txt"]
    unmatched = [
        ("missing.m", "no such file below the project root"),
        ("src/good.m", "no such file below the project root"),
        ("+pkg", "it is a folder; end it with '/' to select the files below it"),
        (
            "notes.txt",
            "the project does not index it (excluded, not a MATLAB file or "
            "sidecar doc, or another letter case)",
        ),
        ("*.txt", "no indexed file matches it"),
    ]
    # good.m passes the error rules: only the unmatched entries fail.
    app = build(make_app, root, matlab_api_check_files=files)
    assert app.statuscode == 1
    assert findings(app) == {("good.m", "example")}
    summary = report(app)["summary"]
    assert summary["errors"] == 0
    assert summary["selection"] == {
        "entries": files,
        "selected": 1,
        "unmatched": [{"entry": e, "reason": why} for e, why in unmatched],
        "ignore_unmatched": False,
    }
    warnings = app.warning.getvalue()
    for entry, why in unmatched:
        assert (
            f"ERROR: [sphinxcontrib-matlabdomain] selection entry {entry!r} "
            f"matches no indexed file or sidecar doc: {why} [mat.api_check]"
        ) in warnings
    lines = text_lines(app)
    assert lines[:5] == [
        f"{e}: error: matches no indexed file or sidecar doc: {why} [selection]"
        for e, why in unmatched
    ]
    assert "Selected: 1 of 18 files by 6 entries, 5 matching no file" in lines

    # No rule severity hides an unmatched entry.
    app = build(
        make_app,
        root,
        matlab_api_check_files=["missing.m"],
        matlab_api_check_rules=dict.fromkeys(ALL_RULES, "ignore"),
    )
    assert app.statuscode == 1
    assert report(app)["findings"] == []


def test_unmatched_without_project_root(make_app, tmp_path):
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
    )
    (tmp_path / "index.rst").write_text("Index\n=====\n")
    app = build(make_app, tmp_path, matlab_api_check_files=["a.m"])
    assert app.statuscode == 1
    assert report(app)["summary"]["selection"]["unmatched"] == [
        {"entry": "a.m", "reason": "matlab_src_code_project_root is not set"}
    ]


@pytest.mark.parametrize("files", [[], "", " , \n"], ids=["list", "str", "blank"])
def test_empty_selection(make_app, root, files):
    app = build(make_app, root, matlab_api_check_files=files)
    assert app.statuscode == 0
    data = report(app)
    assert data["findings"] == []
    assert data["summary"]["selection"] == {
        "entries": [],
        "selected": 0,
        "unmatched": [],
        "ignore_unmatched": False,
    }
    assert data["summary"]["not_checked"]["not_selected"] == ROOT_FILES
    assert text_lines(app)[:2] == [
        "The selection is empty: no file was selected.",
        "Selected: 0 of 18 files by 0 entries, 0 matching no file",
    ]


def test_selection_as_string(make_app, root):
    app = build(make_app, root, matlab_api_check_files="noHelp.m, blankH1.m\r\n")
    assert report(app)["summary"]["selection"]["entries"] == ["noHelp.m", "blankH1.m"]
    assert {file_of(ref) for ref, _ in findings(app)} == {"noHelp.m", "blankH1.m"}


@pytest.mark.parametrize(
    ("value", "status", "entries"),
    [
        ("noHelp.m,blankH1.m", 1, ["noHelp.m", "blankH1.m"]),
        ("good.m", 0, ["good.m"]),
        ("", 0, []),
        ("good.m,missing.m", 1, ["good.m", "missing.m"]),
    ],
    ids=["errors", "passes", "empty", "unmatched"],
)
def test_selection_on_the_command_line(root, tmp_path, value, status, entries):
    out = tmp_path / "out"
    argv = ["-b", BUILDER, "-q", "-E", "-D", f"matlab_api_check_files={value}"]
    assert build_main([*argv, str(root), str(out)]) == status
    data = json.loads((out / "api-check.json").read_text(encoding="utf-8"))
    assert data["summary"]["selection"]["entries"] == entries


def test_selection_does_not_reread_pages(make_app, root):
    build(make_app, root)
    app = make_app(
        BUILDER, srcdir=root, confoverrides={"matlab_api_check_files": ["noHelp.m"]}
    )
    app.build()
    assert "0 added, 0 changed, 0 removed" in app.status.getvalue()
    assert {file_of(ref) for ref, _ in findings(app)} == {"noHelp.m"}


def test_unselected_files_are_not_parsed(make_app, tmp_path):
    (tmp_path / "conf.py").write_text(CONF)
    (tmp_path / "index.rst").write_text("Index\n=====\n")
    (tmp_path / "Unused.m").write_text(BROKEN.format(name="Unused"))
    (tmp_path / "ok.m").write_text("function ok\n% OK Help.\nend\n")
    app = build(make_app, tmp_path, matlab_api_check_files=["ok.m"])
    warnings = app.warning.getvalue()
    assert "Unused.m" not in warnings
    parsed = {Path(key[0]).name for key in app.env.domains["mat"].data["parse_cache"]}
    assert parsed == {"ok.m"}
    assert findings(app) == {("ok.m", "example")}
    # The same environment, the broken file selected: parsed and warned now.
    app = make_app(
        BUILDER, srcdir=tmp_path, confoverrides={"matlab_api_check_files": ["Unused.m"]}
    )
    app.build()
    warnings = app.warning.getvalue()
    assert warnings.count("Unused.m: its first line of code makes it a class") == 1


def test_selected_sidecars(make_app, tmp_path):
    src, docs = tmp_path / "src", tmp_path / "docs"
    src.mkdir()
    docs.mkdir()
    (src / "a.m").write_text("function a\n% A Help.\n%\n% Example:\n%   a\nend\n")
    (src / "guide.rst").write_text("Guide\n=====\n")
    (src / "other.rst").write_text("Other\n=====\n")
    (docs / "conf.py").write_text(
        'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "../src"\n'
        'matlab_src_sidecar_suffixes = [".rst"]\n'
    )
    (docs / "index.rst").write_text("Index\n=====\n")
    app = build(make_app, docs)
    assert findings(app) == {
        ("guide.rst", "sidecar-documented"),
        ("other.rst", "sidecar-documented"),
    }
    app = build(make_app, docs, matlab_api_check_files=["guide.rst"])
    assert app.statuscode == 1
    assert findings(app) == {("guide.rst", "sidecar-documented")}
    summary = report(app)["summary"]
    assert summary["checked"]["sidecar"] == 1
    assert summary["not_checked"]["not_selected"] == 2
    assert summary["selection"]["selected"] == 1


# --- selection from a file, unmatched entries ---------------------------------


def test_selection_from_a_file(make_app, root, tmp_path, monkeypatch):
    listing = tmp_path / "changed.txt"
    listing.write_text("noHelp.m\r\n\r\n  blankH1.m  \r\n", encoding="utf-8-sig")
    app = build(
        make_app,
        root,
        matlab_api_check_files=["good.m", "noHelp.m"],
        matlab_api_check_files_from=str(listing),
    )
    entries = report(app)["summary"]["selection"]["entries"]
    assert entries == ["good.m", "noHelp.m", "blankH1.m"]
    # A relative path is relative to the current folder.
    monkeypatch.chdir(tmp_path)
    app = build(make_app, root, matlab_api_check_files_from="changed.txt")
    assert report(app)["summary"]["selection"]["entries"] == ["noHelp.m", "blankH1.m"]
    assert {file_of(ref) for ref, _ in findings(app)} == {"noHelp.m", "blankH1.m"}
    # An empty file selects nothing; lines are not split at commas.
    listing.write_text("")
    app = build(make_app, root, matlab_api_check_files_from="changed.txt")
    assert app.statuscode == 0
    assert report(app)["summary"]["selection"]["entries"] == []
    listing.write_text("a,b.m\n")
    app = build(make_app, root, matlab_api_check_files_from="changed.txt")
    assert report(app)["summary"]["selection"]["entries"] == ["a,b.m"]


@pytest.mark.parametrize(
    ("setting", "match"),
    [
        ("matlab_api_check_files_from = 3", "must be None or the path"),
        ('matlab_api_check_files_from = "missing.txt"', "cannot read 'missing.txt'"),
        ("matlab_api_check_files_from = 'abs.txt'", "must be relative"),
    ],
    ids=["type", "missing", "absolute-entry"],
)
def test_selection_file_errors(make_app, root, monkeypatch, setting, match):
    monkeypatch.chdir(root)
    (root / "abs.txt").write_text("/abs.m\n")
    conf = root / "conf.py"
    conf.write_text(f"{conf.read_text()}{setting}\n")
    with pytest.raises(ConfigError, match=match):
        make_app(BUILDER, srcdir=root)


def test_ignore_unmatched(make_app, root):
    files = ["good.m", "missing.m"]
    app = build(
        make_app,
        root,
        matlab_api_check_files=files,
        matlab_api_check_ignore_unmatched=True,
    )
    assert app.statuscode == 0
    selection = report(app)["summary"]["selection"]
    assert selection["unmatched"] == [
        {"entry": "missing.m", "reason": "no such file below the project root"}
    ]
    assert selection["ignore_unmatched"] is True
    assert "missing.m" not in app.warning.getvalue()
    assert (
        "selection entry 'missing.m' matches no indexed file or sidecar doc: no "
        "such file below the project root (ignored)"
    ) in app.status.getvalue()
    lines = text_lines(app)
    assert lines[0] == (
        "missing.m: ignored: matches no indexed file or sidecar doc: no such file "
        "below the project root [selection]"
    )
    assert "Selected: 1 of 18 files by 2 entries, 1 matching no file (ignored)" in lines
    # Findings of error rules still fail.
    app = build(
        make_app,
        root,
        matlab_api_check_files=["noHelp.m", "missing.m"],
        matlab_api_check_ignore_unmatched=True,
    )
    assert app.statuscode == 1


@pytest.mark.parametrize(("flag", "status"), [("0", 1), ("1", 0)])
def test_selection_file_and_flag_on_the_command_line(root, tmp_path, flag, status):
    listing = tmp_path / "changed-files.txt"
    listing.write_text("good.m\nREADME.md\ndeleted.m\n")
    out = tmp_path / "out"
    argv = [
        "-b",
        BUILDER,
        "-q",
        "-E",
        "-D",
        f"matlab_api_check_files_from={listing}",
        "-D",
        f"matlab_api_check_ignore_unmatched={flag}",
    ]
    assert build_main([*argv, str(root), str(out)]) == status
    data = json.loads((out / "api-check.json").read_text(encoding="utf-8"))
    selection = data["summary"]["selection"]
    assert selection["selected"] == 1
    assert [u["entry"] for u in selection["unmatched"]] == ["README.md", "deleted.m"]


# --- matlab_api_check_section_labels ------------------------------------------

SECTION_LABELS = {
    "inputs": ["Eingaben", "Eingabe"],
    "outputs": ["Ausgaben"],
    "name-value": ["Optionen"],
}
LABEL_SRC = {
    "eingaben.m": "function y = eingaben(x)\n% EINGABEN Help.\n%\n% Eingaben:\n"
    "%   x - the data\n%\n% AUSGABEN\n%   y - the result\nend\n",
    "eingabe.m": "function eingabe(x)\n% EINGABE Help.\n%\n% Eingabe:\n"
    "%   x - data\nend\n",
    "hinweise.m": "function y = hinweise(x)\n% HINWEISE Help.\n%\n% Hinweise:\n"
    "%   x - data\n%\n% Ergebnis:\n%   y - result\nend\n",
    "standard.m": "function y = standard(x)\n% STANDARD Help.\n%\n% Inputs:\n"
    "%   x - data\n% Outputs:\n%   y - result\nend\n",
    # a lowercase label alone after a line of text is wrapped prose
    "prose.m": "function prose(x)\n% PROSE Help. It takes the\n% eingaben\n"
    "%   x - data\nend\n",
    # an entry of an argument named like the label
    "arg.m": "function y = arg(eingaben)\n% ARG Help.\n%\n% eingaben: the data\n"
    "% Ausgaben:\n%   y - result\nend\n",
    # an inputs label is not a name-value label
    "nv.m": "function nv(x, opts)\n% NV Help.\n%\n% Eingaben:\n%   x - data\n"
    "%   opts.Tol - tolerance\narguments\n    x\n    opts.Tol = 1\nend\nend\n",
    "optionen.m": "function optionen(opts)\n% OPTIONEN Help.\n%\n% Optionen:\n"
    "%   opts.Tol - tolerance\narguments\n    opts.Tol = 1\nend\nend\n",
}
# findings whatever the labels
BOTH = {
    ("hinweise.m", "inputs"),
    ("hinweise.m", "outputs"),
    ("prose.m", "inputs"),
    ("arg.m", "inputs"),
    ("nv.m", "name-value"),
}
# the labels replace the built-in ones: standard.m's Inputs/Outputs no longer count
WITH_LABELS = BOTH | {("standard.m", "inputs"), ("standard.m", "outputs")}
WITHOUT_LABELS = BOTH | {
    ("eingaben.m", "inputs"),
    ("eingaben.m", "outputs"),
    ("eingabe.m", "inputs"),
    ("arg.m", "outputs"),
    ("nv.m", "inputs"),
    ("optionen.m", "name-value"),
}
NO_EXAMPLES = {"example": "ignore"}
NAPOLEON = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinxcontrib.matlab"]


def label_project(path, labels=None, extra=""):
    path.mkdir()
    for name, text in LABEL_SRC.items():
        (path / name).write_text(text)
    conf = f"extensions = {NAPOLEON!r}\nmatlab_src_code_project_root = '.'\n{extra}"
    if labels is not None:
        conf += f"matlab_api_check_section_labels = {labels!r}\n"
    (path / "conf.py").write_text(conf)
    (path / "index.rst").write_text("Index\n=====\n")
    return path


def test_section_labels(make_app, tmp_path):
    with_labels = label_project(tmp_path / "a", SECTION_LABELS)
    app = build(make_app, with_labels, matlab_api_check_rules=NO_EXAMPLES)
    assert findings(app) == WITH_LABELS
    # A separate application without them: nothing leaks.
    without = label_project(tmp_path / "b")
    app = build(make_app, without, matlab_api_check_rules=NO_EXAMPLES)
    assert findings(app) == WITHOUT_LABELS
    assert not has("inputs", "F Help.\n\nEingaben:\n")


def test_section_labels_with_built_in_ones(make_app, tmp_path):
    labels = {
        section: [mat_api_check.BUILTIN_LABELS, *given]
        for section, given in SECTION_LABELS.items()
    }
    srcdir = label_project(tmp_path / "a", labels)
    app = build(make_app, srcdir, matlab_api_check_rules=NO_EXAMPLES)
    assert findings(app) == BOTH


def test_napoleon_sections_are_not_labels(make_app, tmp_path):
    sections = [("Eingaben", "params_style"), ("Ausgaben", "params_style")]
    srcdir = label_project(
        tmp_path / "a", extra=f"napoleon_custom_sections = {sections!r}\n"
    )
    app = build(make_app, srcdir, matlab_api_check_rules=NO_EXAMPLES)
    assert findings(app) == WITHOUT_LABELS


def test_section_label_changes_take_effect(make_app, tmp_path):
    srcdir = label_project(tmp_path / "a", SECTION_LABELS)
    app = build(make_app, srcdir, matlab_api_check_rules=NO_EXAMPLES)
    assert findings(app) == WITH_LABELS
    app = make_app(
        BUILDER,
        srcdir=srcdir,
        confoverrides={
            "matlab_api_check_section_labels": {},
            "matlab_api_check_rules": NO_EXAMPLES,
        },
    )
    app.build()
    assert "0 added, 0 changed, 0 removed" in app.status.getvalue()
    assert findings(app) == WITHOUT_LABELS


def test_section_labels_with_selection(make_app, tmp_path):
    srcdir = label_project(tmp_path / "a", SECTION_LABELS)
    app = build(
        make_app,
        srcdir,
        matlab_api_check_rules=NO_EXAMPLES,
        matlab_api_check_files=["eingaben.m", "hinweise.m"],
    )
    assert findings(app) == {("hinweise.m", "inputs"), ("hinweise.m", "outputs")}
    assert report(app)["summary"]["not_checked"]["not_selected"] == len(LABEL_SRC) - 2


def test_example_label(make_app, tmp_path):
    (tmp_path / "conf.py").write_text(CONF)
    (tmp_path / "index.rst").write_text("Index\n=====\n")
    (tmp_path / "f.m").write_text("function f\n% F Help.\n%\n% Beispiel:\n%   f\nend\n")
    (tmp_path / "g.m").write_text("function g\n% G Help.\n%\n% Example:\n%   g\nend\n")
    (tmp_path / "h.m").write_text(
        "function h\n% H Help.\n%\n% .. rubric:: Example\n%\n%    h\nend\n"
    )
    assert findings(build(make_app, tmp_path)) == {("f.m", "example")}
    app = build(
        make_app, tmp_path, matlab_api_check_section_labels={"example": ["Beispiel"]}
    )
    # The rubric still counts.
    assert findings(app) == {("g.m", "example")}


def test_section_label_values():
    config = SimpleNamespace(
        matlab_api_check_section_labels={
            "inputs": ["Eingaben", "  Zwei   Worte ", "EINGABEN", "<Built-In>"],
            "example": ("Beispiel",),
            "name-value": [],
        }
    )
    assert mat_api_check.section_labels(config) == (
        ("example", ("beispiel",)),
        ("inputs", ("<built-in>", "eingaben", "zwei worte")),
        ("name-value", ()),
    )


@pytest.mark.parametrize(
    ("value", "match"),
    [
        ('["Eingaben"]', "must be a dict"),
        ('{"input": ["Eingaben"]}', "unknown section 'input'"),
        ('{"inputs": "Eingaben"}', "must be a list of labels"),
        ('{"inputs": ["Eingaben:"]}', "is not a label"),
        ('{"inputs": [" "]}', "is not a label"),
        ('{"inputs": [1]}', "is not a label"),
    ],
    ids=["not-dict", "section", "str", "colon", "blank", "type"],
)
def test_section_label_errors(make_app, root, value, match):
    conf = root / "conf.py"
    conf.write_text(f"{conf.read_text()}matlab_api_check_section_labels = {value}\n")
    with pytest.raises(ConfigError, match=match):
        make_app(BUILDER, srcdir=root)


def test_sections_with_labels():
    labels = (
        ("example", ("beispiel",)),
        ("inputs", ("args (opt)", "eingaben")),
        ("name-value", ()),
        ("outputs", ("<built-in>", "zwei worte")),
    )
    sections = mat_api_check.sections_for(labels)
    assert mat_api_check.sections_for(()) is mat_api_check.SECTIONS
    assert mat_api_check.sections_for(labels) is sections
    inputs_only = mat_api_check.sections_for((("inputs", ("eingaben",)),))
    assert inputs_only["outputs"] is mat_api_check.SECTIONS["outputs"]

    def has_label(rule, help_text, names=()):
        return mat_api_check.has_section(rule, help_text, names, sections)

    for line in ("Eingaben:", "EINGABEN", "Eingaben (optional):", "Args (opt):"):
        assert has_label("inputs", f"F Help.\n\n{line}\n")
    assert has_label("outputs", "F Help.\n\nZwei   Worte:\n")
    assert not has_label("inputs", "F Help.\n\nInputs:\n")  # replaced
    assert has_label("outputs", "F Help.\n\nReturns:\n")  # <built-in> kept
    assert has("inputs", "F Help.\n\nInputs:\n")  # other builds unchanged
    for line in ("Options:", "Name-Value Arguments:", "Optionen:", ":", ""):
        assert not has_label("name-value", f"F Help.\n\n{line}\n")
    assert not has_label("outputs", "F Help.\n\nEingaben:\n")
    assert not has_label("name-value", "F Help.\n\nEingaben:\n")
    assert not has_label("inputs", "F Help. It takes the\neingaben\n  x - data\n")
    assert has_label("inputs", "F Help. Some\neingaben\n--------\n")
    assert not has_label("inputs", "F Help.\n\neingaben: the data", {"eingaben"})
    assert not has_label("inputs", "F Help.\n\nArgs opt:\n")
    assert mat_api_check.has_example("F Help.\n\nBeispiel:\n  f\n", sections)
    assert not mat_api_check.has_example("F Help.\n\nExample:\n  f\n", sections)
    assert not mat_api_check.has_example("F Help.\n\nBeispiel:\n  f\n")
