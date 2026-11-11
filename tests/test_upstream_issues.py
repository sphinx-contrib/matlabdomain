# ruff: noqa: E501
"""One regression test for each upstream issue that pull request #373 closes
or answers, rebuilt from the text of the issue with 1.0 syntax.
"""

import importlib.metadata
import re
import subprocess
import sys

from sphinxcontrib import matlab_cli

CONF = (
    'extensions = ["sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "."\n'
    'primary_domain = "mat"\n'
)


def write(root, files):
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def build(make_app, tmp_path, files, rst, conf=""):
    """Build a project; return the warnings, the page text and the page HTML."""
    root = tmp_path / "src"
    write(root, {**files, "conf.py": CONF + conf, "index.rst": "T\n=\n\n" + rst})
    app = make_app(srcdir=root)
    app.build()
    page = (app.outdir / "index.html").read_text(encoding="utf-8")
    body = page[page.index('role="main"') :]
    text = " ".join(re.sub(r"<[^>]+>", " ", body).split())
    return app.warning.getvalue(), text, page


def links(page):
    return re.findall(r'<a class="reference internal" href="([^"]*)"[^>]*><code', page)


def build_with_timeout(tmp_path, files, rst):
    """Build in a child process; a hang fails the test after 60 seconds."""
    root = tmp_path / "src"
    write(root, {**files, "conf.py": CONF, "index.rst": "T\n=\n\n" + rst})
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "html",
            "-q",
            str(root),
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def test_issue_44_attributes_of_methods_in_separate_files(make_app, tmp_path):
    # #44: the attributes of a method defined in its own file (declared in the classdef).
    files = {
        "@C/C.m": "classdef C\n% Class C\nmethods (Static)\n    sfun(x)\nend\nend\n",
        "@C/sfun.m": "function sfun(x)\n% SFUN help\nend\n",
    }
    warnings, text, _ = build(
        make_app, tmp_path, files, ".. mat:autoclass:: C\n   :members:\n"
    )
    assert warnings == ""
    assert "static sfun ( x )" in text
    assert "SFUN help" in text


def test_issue_53_events_are_documented(make_app, tmp_path):
    # #53: `events` blocks of a classdef were ignored.
    files = {
        "C.m": "classdef C\n% Class C\nevents\n    % Fired when done\n    Done\nend\nend\n"
    }
    warnings, text, _ = build(
        make_app, tmp_path, files, ".. mat:autoclass:: C\n   :members:\n"
    )
    assert warnings == ""
    assert "Event Summary Done" in text
    assert "Fired when done" in text


def test_issue_54_enumerations_are_documented(make_app, tmp_path):
    # #54: `enumeration` blocks of a classdef were ignored.
    files = {
        "C.m": "classdef C\n% Class C\nenumeration\n    % the red one\n    Red\n"
        "    Blue % the blue one\nend\nend\n"
    }
    warnings, text, _ = build(
        make_app, tmp_path, files, ".. mat:autoclass:: C\n   :members:\n"
    )
    assert warnings == ""
    assert "Enumeration Values Blue" in text
    assert "the blue one" in text
    assert "the red one" in text


def test_issue_147_parallel_read_is_declared_safe(make_app, tmp_path):
    # #147: the extension must not block parallel builds (parallel_read_safe was False).
    # The builds themselves: tests/test_lazy_index.py::test_parallel_build_matches_serial.
    _, _, _ = build(make_app, tmp_path, {}, "")
    extension = make_app(srcdir=tmp_path / "src").extensions["sphinxcontrib.matlab"]
    assert extension.parallel_read_safe is True
    assert extension.parallel_write_safe is True


def test_issue_149_apidoc_documents_a_folder_recursively(make_app, tmp_path):
    # #149: one command documents every package and subfolder of a folder (scmd apidoc).
    files = {
        "p/a.m": "function a\n% A help\nend\n",
        "p/+pk/b.m": "function b\n% B help\nend\n",
        "p/+pk/C.m": "classdef C\n% C help\nend\n",
        "p/sub/d.m": "function d\n% D help\nend\n",
    }
    conf = CONF.replace('"."', '"p"') + 'matlab_apidoc_output_dir = "api"\n'
    root = tmp_path / "src"
    write(
        root,
        {
            **files,
            "conf.py": conf,
            "index.rst": "T\n=\n\n.. toctree::\n\n   api/index\n",
        },
    )
    assert matlab_cli.main(["apidoc", "--conf-dir", str(root), "-q"]) in (0, None)
    app = make_app(srcdir=root)
    app.build()
    assert app.warning.getvalue() == ""
    pages = " ".join(
        p.read_text(encoding="utf-8") for p in (app.outdir / "api").glob("*.html")
    )
    for reference in ("+pk/b.m", "+pk/C.m", "a.m", "sub/d.m"):
        assert f'id="mat-{reference}"' in pages


def test_issue_184_member_links_need_no_class_name(make_app, tmp_path):
    # #184: :meth: and :attr: in any docstring of the class link by the member name alone.
    files = {
        "MyClass.m": "classdef MyClass\n% See :mat:meth:`my_method` and :mat:attr:`Prop`.\n"
        "properties\n    % Prop help, see :mat:meth:`my_method`\n    Prop\nend\n"
        "methods\n    function my_method(obj)\n    % uses :mat:attr:`Prop` and :mat:meth:`other`\n    end\n"
        "    function other(obj)\n    % other\n    end\nend\nend\n"
    }
    warnings, text, page = build(
        make_app, tmp_path, files, ".. mat:autoclass:: MyClass\n   :members:\n"
    )
    assert warnings == ""
    assert links(page).count("#mat-MyClass.m.my_method") == 2
    assert links(page).count("#mat-MyClass.m.Prop") == 2
    assert "#mat-MyClass.m.other" in links(page)
    assert "See my_method() and Prop" in text
    assert "uses Prop and other()" in text


def test_issue_222_abstract_methods_are_documented(make_app, tmp_path):
    # #222: abstract methods (no body, no `end`) were not documented.
    files = {
        "C.m": "classdef C < handle\n% Doc\nmethods (Abstract)\n    % Doc above\n"
        "    val = abs1(arg)\n    [v1, v2] = abs2(arg1, arg2)\n        % Doc below\nend\nend\n"
    }
    warnings, text, _ = build(
        make_app, tmp_path, files, ".. mat:autoclass:: C\n   :members:\n"
    )
    assert warnings == ""
    assert "abstract abs1 ( arg )" in text
    assert "Doc above" in text
    assert "abstract abs2 ( arg1 , arg2 )" in text
    assert "Doc below" in text


def test_issue_243_function_named_like_its_folder_links(make_app, tmp_path):
    # #243: :func:`foo` did not link when the function is named like its folder.
    files = {"foo/foo.m": "function foo\n% FOO help\nend\n"}
    rst = ".. mat:autofunction:: foo/foo.m\n\nSee :mat:func:`foo` and :mat:func:`foo/foo.m`.\n"
    warnings, _, page = build(make_app, tmp_path, files, rst)
    assert warnings == ""
    assert links(page) == ["#mat-foo/foo.m", "#mat-foo/foo.m"]


def test_issue_246_reference_beside_a_section_of_the_same_name(make_app, tmp_path):
    # #246: :func:`myfunction` did not link beside a section titled `myfunction`.
    files = {
        "myfunction.m": "function myfunction\n% help\nend\n",
        "myclass.m": "classdef myclass\n% cls help\nend\n",
    }
    rst = (
        "myfunction\n----------\n\n.. mat:autofunction:: myfunction\n\n"
        "myclass\n-------\n\n.. mat:autoclass:: myclass\n\n"
        "Refs: :mat:func:`myfunction` and :mat:class:`myclass`.\n"
    )
    warnings, _, page = build(make_app, tmp_path, files, rst)
    assert warnings == ""
    assert {"#mat-myfunction.m", "#mat-myclass.m"} <= set(links(page))


def test_issue_247_class_folder_below_the_current_folder(make_app, tmp_path):
    # #247: a class folder documented after a "current folder" directive was a fatal error.
    files = {
        "target/@ClassFolder/ClassFolder.m": "classdef ClassFolder\n% CF help\nmethods\n"
        " function obj = ClassFolder()\n end\n m1(obj)\nend\nend\n",
        "target/@ClassFolder/m1.m": "function m1(obj)\n% M1 help\nend\n",
    }
    rst = ".. mat:currentfolder:: target/\n\n.. mat:autoclass:: ClassFolder\n   :members:\n"
    warnings, text, _ = build(make_app, tmp_path, files, rst)
    assert warnings == ""
    assert "class ClassFolder" in text
    assert "m1 ( )" in text
    assert "M1 help" in text


def test_issue_264_version_is_returned_by_setup(make_app, tmp_path):
    # #264: setup() returns the version of the package.
    build(make_app, tmp_path, {}, "")
    extension = make_app(srcdir=tmp_path / "src").extensions["sphinxcontrib.matlab"]
    assert extension.version == importlib.metadata.version("sphinxcontrib-matlabdomain")


def test_issue_269_help_above_the_function_line(make_app, tmp_path):
    # #269: a header comment above `function` (EEGLAB style) was not the help text.
    files = {
        "f.m": "%% f\n% F header help line one\n% second line\nfunction out = f(x)\nout = x;\nend\n"
    }
    warnings, text, _ = build(make_app, tmp_path, files, ".. mat:autofunction:: f\n")
    assert warnings == ""
    assert "F header help line one second line" in text


def test_issue_271_excluded_files_are_left_out(make_app, tmp_path):
    # #271: files the project excludes must not be documented (now matlab_src_exclude_patterns).
    files = {
        "a.m": "function a\n% A help\nend\n",
        "tests/t.m": "function t\n% T help\nend\n",
    }
    rst = ".. mat:autofunction:: a\n\n.. mat:autofunction:: tests/t.m\n"
    warnings, text, _ = build(
        make_app, tmp_path, files, rst, 'matlab_src_exclude_patterns = ["tests/**"]\n'
    )
    assert "A help" in text
    assert "T help" not in text
    assert "don't know which object to document for 'tests/t.m'" in warnings


def test_issue_272_missing_folder_is_a_warning(make_app, tmp_path):
    # #272: a folder that does not exist stopped the build with an exception.
    files = {"a.m": "function a\n% A\nend\n"}
    rst = ".. mat:autofolder:: mech/nothere/\n   :members:\n\n.. mat:autofunction:: nothere\n"
    warnings, _, _ = build(make_app, tmp_path, files, rst)
    assert warnings.count("[mat.not_found]") == 2
    assert "mech/nothere/" in warnings


def test_issue_273_all_help_lines_are_rendered(make_app, tmp_path):
    # #273: only the first help line of a class or function was rendered.
    files = {
        "MatlabClass.m": "classdef MatlabClass\n% First line summary.\n%\n"
        "% Longer description :math:`x^2` here.\n%\n% :param a: the a\n% :returns: r\n%\n"
        "%   Second paragraph.\nend\n",
        "g.m": "function g(a)\n% G first line.\n%\n% G more lines.\n% and more.\nend\n",
    }
    rst = ".. mat:autoclass:: MatlabClass\n\n.. mat:autofunction:: g\n"
    warnings, text, _ = build(make_app, tmp_path, files, rst)
    assert warnings == ""
    for part in (
        "First line summary.",
        "Longer description",
        "Parameters",
        "a – the a",
        "Returns",
        "Second paragraph.",
        "G more lines. and more.",
    ):
        assert part in text


def test_issue_274_static_method_in_a_package_class(make_app, tmp_path):
    # #274 (and PR #248): `:members:` of a class with a static method raised AttributeError.
    files = {
        "+nla/+net/Test.m": "classdef Test\n% C\nmethods(Static)\n"
        " function inputs = requiredInputs()\n % Defines inputs\n %\n % :return: stuff\n"
        " inputs = {nla.inputField.Number('prob_max', 'x', 0, 0.05, 1),...\n"
        " nla.inputField.NetworkAtlasFuncConn(), nla.inputField.Behavior()};\n end\nend\nend\n"
    }
    warnings, text, _ = build(
        make_app, tmp_path, files, ".. mat:autoclass:: nla.net.Test\n   :members:\n"
    )
    assert warnings == ""
    assert "static requiredInputs ( )" in text
    assert "Defines inputs" in text


def test_issue_275_method_with_a_nested_function(make_app, tmp_path):
    # #275: a nested function in a method made parsing fail ("Parsing failed in ...").
    files = {
        "C.m": "classdef C\nmethods\n    function rv = method_with_nested_function(self, arg1)\n"
        "        % help nested\n        function rv = nested_function(arg1)\n            rv = arg1;\n"
        "        end\n        if iscell(arg1)\n"
        "            rv = cellfun(@nested_function, arg1, 'uniform', false);\n        else\n"
        "            rv = nested_function(arg1);\n        end\n    end\nend\nend\n"
    }
    warnings, text, _ = build(
        make_app, tmp_path, files, ".. mat:autoclass:: C\n   :members:\n"
    )
    assert warnings == ""
    assert "method_with_nested_function ( arg1 )" in text
    assert "help nested" in text


def test_issue_276_block_comment_and_local_function_do_not_hang(tmp_path):
    # #276: a block comment before a method plus a local function hung the build.
    files = {
        "ClassWithBlockComments.m": "classdef ClassWithBlockComments\nmethods\n%{\n"
        + "=" * 40
        + "\nA multiline comment\n"
        + "=" * 40
        + "\n%}\n    function method_name(self)\n        % A method with a block comment above it\n"
        "    end\nend\nend\n\nfunction rv = local_function(arg1, arg2)\nend\n"
    }
    result = build_with_timeout(
        tmp_path, files, ".. mat:autoclass:: ClassWithBlockComments\n   :members:\n"
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    page = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert "A method with a block comment above it" in page


def test_issue_280_unknown_class_attribute_does_not_warn(make_app, tmp_path):
    # #280: "Unexpected class attribute: 'TestParameterDefinition'" warning.
    files = {
        "C.m": "classdef (TestParameterDefinition) C\n% C help\nproperties (TestParameter)\n"
        "  p = {1,2}\nend\nmethods\n function f(o)\n % f help\n end\nend\nend\n"
    }
    warnings, text, _ = build(
        make_app, tmp_path, files, ".. mat:autoclass:: C\n   :members:\n"
    )
    assert warnings == ""
    assert "f ( o )" in text


def test_issue_281_test_attributes_do_not_hang(tmp_path):
    # #281: string-valued attributes (ParameterCombination="sequential", TestTags={...}) hung the build.
    files = {
        "T1.m": 'classdef T1 < matlab.unittest.TestCase\n% T1 help\nmethods (Test, ParameterCombination="sequential")\n'
        "    function testA(testCase, p)\n    % testA help\n    end\nend\nend\n",
        "T2.m": "classdef (TestTags={'SomeTag'}) T2 < matlab.unittest.TestCase\n% T2 help\n"
        "methods (Test, TestTags={'SomeTag'})\n    function testB(testCase)\n    % testB help\n    end\nend\nend\n",
    }
    rst = ".. mat:autoclass:: T1\n   :members:\n\n.. mat:autoclass:: T2\n   :members:\n"
    result = build_with_timeout(tmp_path, files, rst)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    page = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert "testA help" in page
    assert "testB help" in page


def test_issue_299_private_method_in_a_separate_file_is_hidden(make_app, tmp_path):
    # #299: a private method in its own file was documented by `:members:`.
    files = {
        "+package1/+package2/@MyClass/MyClass.m": "classdef MyClass\n    methods\n"
        "        function obj = MyClass()\n        % The constructor\n        end\n    end\n"
        "    methods (Access = private)\n        helper1(obj)\n    end\nend\n",
        "+package1/+package2/@MyClass/helper1.m": "function helper1(obj)\n% Private helper function\nend\n",
    }
    warnings, text, _ = build(
        make_app,
        tmp_path,
        files,
        ".. mat:autoclass:: package1.package2.MyClass\n   :members:\n",
    )
    assert warnings == ""
    assert "The constructor" in text
    assert "helper1" not in text
    # With the option the same method does appear, so the file is a method of the class.
    _, text, _ = build(
        make_app,
        tmp_path / "again",
        files,
        ".. mat:autoclass:: package1.package2.MyClass\n   :members:\n   :private-members:\n",
    )
    assert "helper1" in text


def test_issue_335_and_pr_347_namespaced_validators(make_app, tmp_path):
    # #335 and PR #347: a namespaced validator (`{a.b.v}`) in a property or an argument crashed the build.
    files = {
        "C.m": "classdef C\n% C help\nproperties\n    % P help\n"
        "    Prop1 {myNamespace.myValidatorFunction(Prop1)}\n    % Q help\n    Prop2 {a.b.v}\nend\nend\n",
        "f.m": "function out = f(x)\n% f help\n    arguments\n        x {a.b.v}\n    end\n    out = x;\nend\n",
    }
    rst = ".. mat:autoclass:: C\n   :members:\n\n.. mat:autofunction:: f\n"
    warnings, text, _ = build(make_app, tmp_path, files, rst)
    assert warnings == ""
    assert "Prop1" in text
    assert "Prop2" in text
    assert "f ( x )" in text


def test_issue_336_block_comment_after_an_argument(make_app, tmp_path):
    # #336: `%{ ... }` after an argument on the same line was a parsing error.
    files = {
        "g.m": "function g(value1, value2)\n% g help\n  arguments\n    value1\n"
        '    value2 {mustBeA(value2, ["double", "single"])} %{mustBeText(value2)}\n  end\nend\n'
    }
    warnings, text, _ = build(make_app, tmp_path, files, ".. mat:autofunction:: g\n")
    assert warnings == ""
    assert "g ( value1 , value2 )" in text
    assert "g help" in text


def test_issue_337_folder_starting_with_an_underscore(make_app, tmp_path):
    # #337: files below a folder that starts with `_` caused failures.
    files = {"src/scooby/doo/_where/are/you.m": "function you\n% you help\nend\n"}
    rst = ".. mat:autofunction:: you\n\n.. mat:autofunction:: src/scooby/doo/_where/are/you.m\n"
    warnings, text, page = build(make_app, tmp_path, files, rst)
    assert warnings == ""
    assert "you help" in text
    assert 'id="mat-src/scooby/doo/_where/are/you.m"' in page


def test_pr_298_odd_arguments_and_inheritance_option_on_functions(make_app, tmp_path):
    # PR #298: an arguments block with unmatched entries and show-inheritance applied to a function crashed.
    arguments = (
        "function out = f(a, b, varargin)\n% f help\n    arguments\n        % just a comment\n"
        "        a (1,1) double {mustBePositive} = 5 % trailing\n        b {x.y.z}\n        ;\n"
        "        varargin\n    end\n    arguments (Repeating)\n        c\n    end\n    arguments\n"
        "        opts.Name (1,1) string = \"x\"\n        opts.Other {mustBeA(opts.Other, 'double')} = {}\n"
        "    end\n    out = a;\nend\n"
    )
    files = {
        "f.m": arguments,
        "B.m": "classdef B\n% B\nend\n",
        "D.m": "classdef D < B\n% D help\nend\n",
    }
    warnings, text, _ = build(
        make_app,
        tmp_path,
        files,
        ".. mat:autofunction:: f\n\n.. mat:autoclass:: D\n",
        'autodoc_default_options = {"members": True, "show-inheritance": True}\n',
    )
    assert warnings == ""
    assert "f ( a , b , varargin , c , opts )" in text
    assert "Bases: B" in text
