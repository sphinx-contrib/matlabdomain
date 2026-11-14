"""Test autodoc of class folders and their method files.

:copyright: Copyright by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import json
import pickle
import re

import pytest


@pytest.fixture
def srcdir(rootdir):
    return rootdir / "roots" / "test_classfolder"


def test_first(app):
    content = pickle.loads((app.doctreedir / "index_first.doctree").read_bytes())

    assert content[0].astext() == (
        "First\n\n\n\n"
        "class First\n\n"
        "The first class\n\n"
        "Constructor Summary\n\n\n\n\n\n"
        "First(a)\n\n"
        "Constructor for First\n\n"
        "Property Summary\n\n\n\n\n\n"
        "a\n\n"
        "The property\n\n"
        "Method Summary\n\n\n\n\n\n"
        "method_in_folder(varargin)\n\n"
        "A method defined in the folder\n\n\n\n"
        "method_inside_classdef(b)\n\n"
        "Method inside class definition"
    )


def test_second(app):
    content = pickle.loads((app.doctreedir / "index_second.doctree").read_bytes())

    assert content[0].astext() == (
        "Second\n\n\n\n"
        "class Second\n\n"
        "The second class\n\n"
        "Constructor Summary\n\n\n\n\n\n"
        "Second(b)\n\n"
        "Constructor for Second\n\n"
        "Property Summary\n\n\n\n\n\n"
        "b\n\n"
        "a property of a class folder\n\n"
        "Method Summary\n\n\n\n\n\n"
        "method_in_folder(varargin)\n\n"
        "A method defined in the folder\n\n\n\n"
        "method_inside_classdef(c)\n\n"
        "Method inside class definition"
    )


def test_third(app):
    content = pickle.loads((app.doctreedir / "index_third.doctree").read_bytes())

    assert content[0].astext() == (
        "Third\n\n\n\n"
        "class pkg.Third\n\n"
        "The third class\n\n"
        "Constructor Summary\n\n\n\n\n\n"
        "Third(c)\n\n"
        "Constructor for Third\n\n"
        "Property Summary\n\n\n\n\n\n"
        "c\n\n"
        "a property of a class folder\n\n"
        "Method Summary\n\n\n\n\n\n"
        "method_in_folder(varargin)\n\n"
        "A method defined in the folder\n\n\n\n"
        "method_inside_classdef(d)\n\n"
        "Method inside class definition"
    )


# Method signatures declared in the classdef, implemented in their own files.
# MATLAB R2026a and R2026b (meta.class): make is public and static (inputs obj,
# y); secret private; listed access-listed and hidden; guarded protected;
# sealedAway private and static; declared, inline and undeclared public.
GADGET = {
    "@Gadget/Gadget.m": """\
classdef Gadget < handle
    % GADGET A class folder with declared methods.
    %
    % Example:
    %   g = Gadget();
    methods (Static)
        out = make(obj, y)  % first input named obj, yet static
    end
    methods (Access = private)
        r = secret(obj, z)
    end
    methods (Access = {?Gadget, ?handle}, Hidden)
        listed(obj)
    end
    methods (~Static, Access = protected)
        r = guarded(obj)
    end
    methods (Static, Access = private)
        r = sealedAway(a)
    end
    methods
        function obj = Gadget()
            % GADGET Construct it.
        end
        function r = inline(obj, q)
            % INLINE An inline method.
            r = q;
        end
        r = declared(obj, q)
    end
end
""",
    "@Gadget/make.m": (
        "function out = make(obj, y)\n% MAKE Make one.\nout = obj + y;\nend\n"
    ),
    "@Gadget/secret.m": "function r = secret(obj, z)\n% SECRET Private.\nr = z;\nend\n",
    "@Gadget/listed.m": "function listed(obj)\n% LISTED Access-listed, hidden.\nend\n",
    "@Gadget/guarded.m": (
        "function r = guarded(obj)\n% GUARDED Protected.\nr = 1;\nend\n"
    ),
    "@Gadget/sealedAway.m": (
        "function r = sealedAway(a)\n% SEALEDAWAY Static, private.\nr = a;\nend\n"
    ),
    "@Gadget/declared.m": (
        "function r = declared(obj, q)\n% DECLARED Public.\nr = q;\nend\n"
    ),
    "@Gadget/undeclared.m": (
        "function r = undeclared(obj, q)\n% UNDECLARED Not declared.\nr = q;\nend\n"
    ),
}
GADGET_PAGE = """\
Gadget
======

.. mat:autoclass:: @Gadget/Gadget.m
   :members:

All
---

.. mat:autoclass:: @Gadget/Gadget.m
   :members:
   :private-members:
   :protected-members:
   :hidden-members:
   :access-list-members:
   :noindex:
"""


def gadget_app(make_app, tmp_path, builder="text"):
    files = {
        **GADGET,
        "conf.py": 'extensions = ["sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "."\n',
        "index.rst": GADGET_PAGE,
    }
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text, encoding="utf-8")
    app = make_app(builder, srcdir=tmp_path, freshenv=True)
    app.build()
    return app


def method_summary(text):
    """Return the signatures of a rendered Method Summary."""
    return [line[6:] for line in text.splitlines() if re.match(r" {6}\S", line)]


def test_declared_attributes_of_folder_methods(make_app, tmp_path):
    app = gadget_app(make_app, tmp_path)
    assert app.warning.getvalue() == ""
    public, every = (
        (app.outdir / "index.txt").read_text(encoding="utf-8").split("\nAll\n===\n")
    )
    assert method_summary(public.split("Method Summary")[1]) == [
        "declared(q)",
        "inline(q)",
        "static make(obj, y)",
        "undeclared(q)",
    ]
    assert method_summary(every.split("Method Summary")[1]) == [
        "declared(q)",
        "guarded()",
        "inline(q)",
        "listed()",
        "static make(obj, y)",
        "static sealedAway(a)",
        "secret(z)",
        "undeclared(q)",
    ]
    dom = app.env.get_domain("mat")
    assert {name: objtype for name, _, objtype, *_ in dom.get_objects()} == {
        "@Gadget/Gadget.m": "class",
        "@Gadget/Gadget.m.Gadget": "method",
        "@Gadget/Gadget.m.declared": "method",
        "@Gadget/Gadget.m.inline": "method",
        "@Gadget/Gadget.m.make": "staticmethod",
        "@Gadget/Gadget.m.undeclared": "method",
    }


def test_api_check_reads_declared_attributes(make_app, tmp_path):
    app = gadget_app(make_app, tmp_path, "matlab-api-check")
    data = json.loads((app.outdir / "api-check.json").read_text(encoding="utf-8"))
    findings = {
        (f["reference"], f["rule"]): f["message"].rpartition(": ")[2]
        for f in data["findings"]
        if f["rule"] in ("inputs", "outputs")
    }
    # Private, protected, access-listed and hidden method files are not
    # checked; a static method has no object, so its first input counts.
    assert findings == {
        ("@Gadget/Gadget.m.inline", "inputs"): "q",
        ("@Gadget/Gadget.m.inline", "outputs"): "r",
        ("@Gadget/declared.m", "inputs"): "q",
        ("@Gadget/declared.m", "outputs"): "r",
        ("@Gadget/make.m", "inputs"): "obj, y",
        ("@Gadget/make.m", "outputs"): "out",
        ("@Gadget/undeclared.m", "inputs"): "q",
        ("@Gadget/undeclared.m", "outputs"): "r",
    }
    assert data["summary"]["checked"]["method"] == 5


def test_classdef_edit_updates_folder_methods(make_app, tmp_path):
    app = gadget_app(make_app, tmp_path)
    classdef = tmp_path / "@Gadget" / "Gadget.m"
    classdef.write_text(
        GADGET["@Gadget/Gadget.m"].replace(
            "methods (Static)\n", "methods (Static, Hidden)\n"
        ),
        encoding="utf-8",
    )
    # Only the classdef changes; make.m and its cached parse stay.
    app = make_app("text", srcdir=tmp_path)
    app.build()
    public = (app.outdir / "index.txt").read_text(encoding="utf-8").split("\nAll\n")[0]
    assert method_summary(public.split("Method Summary")[1]) == [
        "declared(q)",
        "inline(q)",
        "undeclared(q)",
    ]
    app = make_app("matlab-api-check", srcdir=tmp_path)
    app.build()
    data = json.loads((app.outdir / "api-check.json").read_text(encoding="utf-8"))
    assert not any(f["reference"] == "@Gadget/make.m" for f in data["findings"])
