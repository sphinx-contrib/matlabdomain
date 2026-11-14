"""Autodoc options and member documentation of the mat documenters."""

import os
import re

import pytest
from docutils import nodes
from sphinx import addnodes

from sphinxcontrib import mat_types

CONF = (
    'extensions = ["sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "."\n'
    'primary_domain = "mat"\n'
)

ACCESS = """\
classdef Access < handle
    % ACCESS HELP
    properties
        pub % public property
        pubUndoc
    end
    properties (GetAccess = private, SetAccess = private)
        getPriv % get-private property
    end
    properties (Access = protected)
        prot % protected property
    end
    properties (Hidden)
        hid % hidden property
    end
    methods
        function obj = Access()
            % the constructor
        end
        function zMeth(obj)
            % public method, last by name
        end
        function pubUndocMeth(obj)
        end
    end
    methods (Access = 'private')
        function quotedPriv(obj)
            % quoted private method
        end
    end
    methods (Access = private)
        function priv(obj)
            % private method
        end
        function privUndoc(obj)
        end
    end
    methods (Access = ?Friend)
        function friendly(obj)
            % access-list method
        end
    end
    methods (Access = {?Friend, ?pkg.Other})
        function friendlier(obj)
            % two-class access-list method
        end
    end
    methods (Static)
        function s = make()
            % static method
        end
    end
end
"""

FILES = {
    "Access.m": ACCESS,
    "Color.m": (
        "classdef Color\n% COLOR HELP\nenumeration\nRed % the red\nGreen\nend\nend\n"
    ),
    "Sig.m": (
        "classdef Sig\n% SIG HELP\nproperties\nx double % typed\nend\nmethods\n"
        "function obj = Sig(a, b)\n% Sig(a, b)\n%\n% CTOR HELP\nend\nend\nend\n"
    ),
    "Bare.m": (
        "classdef Bare\n% BARE HELP\nmethods\nfunction obj = Bare\n% BARE CTOR\n"
        "end\nend\nend\n"
    ),
    "NoCtor.m": "classdef NoCtor\n% NOCTOR HELP\nend\n",
    "fsig.m": "function fsig(x)\n% fsig(x, y) -> z\n%\n%\n% FSIG HELP\nend\n",
    "fother.m": "function fother(x)\n% other(a)\n% FOTHER HELP\nend\n",
    "fnone.m": "function fnone(x)\nend\n",
    "consts.m": "% CONSTS HELP\na = 1;\n",
    "undoc.m": "function undoc\nend\n",
    "sub/g.m": "function g\n% G HELP\nend\n",
}


def build(make_app, tmp_path, page, files=FILES, verbosity=0, **confoverrides):
    for path, text in {**files, "conf.py": CONF, "index.rst": page}.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")
    app = make_app(srcdir=tmp_path, confoverrides=confoverrides, verbosity=verbosity)
    app.build()
    return app


def page(*directives):
    return "Index\n=====\n\n" + "\n".join(directives)


def documented(app, prefix=""):
    """Return the documented references below ``prefix``, in page order."""
    doctree = app.env.get_doctree("index")
    refs = [
        n["names"][0] for n in doctree.findall(addnodes.desc_signature) if n["names"]
    ]
    return [r[len(prefix) :] for r in refs if r.startswith(prefix)]


def html(app):
    return (app.outdir / "index.html").read_text(encoding="utf-8")


DEFAULT = {"Access", "pub", "zMeth", "make"}


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ("", DEFAULT),
        (":undoc-members:", DEFAULT | {"pubUndoc", "pubUndocMeth"}),
        (":private-members:", DEFAULT | {"getPriv", "quotedPriv", "priv"}),
        (":private-members: priv", DEFAULT | {"priv"}),
        (
            ":private-members:\n   :undoc-members:",
            DEFAULT
            | {
                "getPriv",
                "quotedPriv",
                "priv",
                "privUndoc",
                "pubUndoc",
                "pubUndocMeth",
            },
        ),
        (":protected-members:", DEFAULT | {"prot"}),
        (":hidden-members:", DEFAULT | {"hid"}),
        (":access-list-members:", DEFAULT | {"friendly", "friendlier"}),
        (":access-list-members: pkg.Other", DEFAULT | {"friendlier"}),
        (":friend-members: ?Friend", DEFAULT | {"friendly", "friendlier"}),
        (":exclude-members:", DEFAULT),
        (":exclude-members: pub, make", DEFAULT - {"pub", "make"}),
    ],
)
def test_member_filters(make_app, tmp_path, options, expected):
    app = build(
        make_app,
        tmp_path,
        page(f".. mat:autoclass:: Access\n   :members:\n   {options}\n"),
    )
    assert set(documented(app, "Access.m.")) == expected
    assert "WARNING" not in app.warning.getvalue()


def test_explicit_members(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(".. mat:autoclass:: Access\n   :members: pub, priv, nothing\n"),
    )
    assert set(documented(app, "Access.m.")) == {"pub", "priv"}
    assert "missing attribute nothing in object Access.m" in app.warning.getvalue()


def test_member_order(make_app, tmp_path):
    directive = ".. mat:autoclass:: Access\n   :members:\n   :member-order: {}\n"
    orders = {}
    for order in ("alphabetical", "groupwise", "bysource"):
        app = build(make_app, tmp_path, page(directive.format(order)))
        orders[order] = documented(app, "Access.m.")
    # Sections: constructor, properties, methods.
    assert orders["alphabetical"] == ["Access", "pub", "make", "zMeth"]
    # Static methods before ordinary ones.
    assert orders["groupwise"] == ["Access", "pub", "make", "zMeth"]
    assert orders["bysource"] == ["Access", "pub", "zMeth", "make"]


def signatures(app):
    doctree = app.env.get_doctree("index")
    return {
        (n["names"] or [""])[0]: n.astext()
        for n in doctree.findall(addnodes.desc_signature)
    }


def test_static_methods(make_app, tmp_path):
    app = build(make_app, tmp_path, page(".. mat:autoclass:: Access\n   :members:\n"))
    entries = {e[1] for e in app.env.get_domain("index").entries["index"]}
    assert "make() (Access static method)" in entries
    assert (
        app.env.get_domain("mat").data["objects"]["Access.m.make"][1] == "staticmethod"
    )
    assert signatures(app)["Access.m.make"] == "static make()"


def test_root_class_without_undoc_members(make_app, tmp_path):
    # Regression: at the project root, members without help were listed.
    app = build(
        make_app,
        tmp_path,
        page(
            ".. mat:autoclass:: Access\n   :members:\n",
            ".. mat:autofolder:: .\n   :members:\n",
        ),
    )
    assert "pubUndoc" not in documented(app, "Access.m.")
    assert "undoc.m" not in documented(app)
    assert "fsig.m" in documented(app)


def test_enumeration_values(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(
            ".. mat:autoclass:: Color\n   :members:\n   :member-order: bysource\n",
            ".. mat:autoenum:: Color.Red\n   :no-index:\n",
        ),
        matlab_show_property_default_value=True,
        matlab_show_property_specs=True,
    )
    # Values without help are listed too.
    assert documented(app, "Color.m.") == ["Red", "Green"]
    assert "Enumeration Values" in html(app)
    assert html(app).count("the red") == 2


@pytest.mark.parametrize(
    ("content", "signature", "texts", "constructor"),
    [
        ("class", "(a, b)", ["SIG HELP"], True),
        ("both", "(a, b)", ["SIG HELP", "CTOR HELP"], False),
        ("init", "(a, b)", ["CTOR HELP"], False),
    ],
)
def test_autoclass_content(make_app, tmp_path, content, signature, texts, constructor):
    app = build(
        make_app,
        tmp_path,
        page(".. mat:autoclass:: Sig\n   :members:\n", ".. mat:autoclass:: NoCtor\n"),
        autoclass_content=content,
    )
    doctree = app.env.get_doctree("index")
    (sig,) = (
        n for n in doctree.findall(addnodes.desc_signature) if "Sig.m" in n["names"]
    )
    assert sig.astext().endswith(signature)
    text = doctree.astext()
    for shown in texts:
        assert shown in text
    # the signature line is not help text
    assert "Sig(a, b)" not in [p.astext() for p in doctree.findall(nodes.paragraph)]
    assert ("Sig.m.Sig" in documented(app)) is constructor
    assert "None singleton" not in text


def test_autoclass_content_without_docstring_signature(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(".. mat:autoclass:: Sig\n", ".. mat:autoclass:: NoCtor\n"),
        autoclass_content="both",
        autodoc_docstring_signature=False,
    )
    text = app.env.get_doctree("index").astext()
    assert "Sig(a, b)" in text and "CTOR HELP" in text
    assert "None singleton" not in text


@pytest.mark.parametrize("class_signature", [True, False])
def test_class_signature_from_constructor(make_app, tmp_path, class_signature):
    app = build(
        make_app,
        tmp_path,
        page(".. mat:autoclass:: Bare\n", ".. mat:autoclass:: Access\n"),
        matlab_class_signature=class_signature,
        autodoc_docstring_signature=False,
    )
    doctree = app.env.get_doctree("index")
    sigs = [n.astext() for n in doctree.findall(addnodes.desc_signature)]
    assert (
        sigs == ["class Bare", "class Access"]
        if not class_signature
        else [
            "class Bare",
            "class Access()",
        ]
    )


def test_docstring_signature(make_app, tmp_path):
    directives = [f".. mat:autofunction:: {f}\n" for f in ("fsig", "fother", "fnone")]
    app = build(make_app, tmp_path, page(*directives))
    doctree = app.env.get_doctree("index")
    sigs = [n.astext() for n in doctree.findall(addnodes.desc_signature)]
    assert sigs == ["fsig(x, y) -> z", "fother(x)", "fnone(x)"]
    text = doctree.astext()
    assert "FSIG HELP" in text and "fsig(x, y)" not in text.replace(sigs[0], "")
    assert "other(a)" in text  # another name: not a signature

    app = build(
        make_app, tmp_path, page(*directives), autodoc_docstring_signature=False
    )
    sigs = [
        n.astext()
        for n in app.env.get_doctree("index").findall(addnodes.desc_signature)
    ]
    assert sigs[0] == "fsig(x)"


def test_data(make_app, tmp_path):
    app = build(make_app, tmp_path, page(".. mat:autodata:: consts\n"))
    assert documented(app) == ["consts.m"]
    assert app.env.get_domain("mat").data["objects"]["consts.m"][1] == "data"
    assert "CONSTS HELP" in html(app)


def test_attribute_annotations(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(
            ".. mat:autoattribute:: Sig.x\n",
            ".. mat:autoattribute:: Access.pub\n   :annotation: 5\n",
            ".. mat:autoattribute:: Access.prot\n   :annotation:\n",
            ".. mat:autoattribute:: Access.zMeth\n",
        ),
        matlab_show_property_specs=True,
    )
    sigs = [
        n.astext()
        for n in app.env.get_doctree("index").findall(addnodes.desc_signature)
    ]
    assert sigs == ["Sig.x double", "Access.pub = 5", "Access.prot", "Access.zMeth"]


def test_folder_options(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(
            ".. mat:autofolder:: sub\n   :synopsis: the sub folder\n   :platform: any\n"
            "   :deprecated:\n   :no-index:\n",
            ".. mat:autofolder:: sub(x)\n",
            ".. mat:autofolder:: sub\n   :members: g, nothing\n",
            ".. mat:autofolder:: Access.pub\n",
        ),
    )
    warnings = app.warning.getvalue()
    assert (
        "signature arguments or return annotation given for autofolder sub/" in warnings
    )
    assert (
        "missing attribute mentioned in :members: or __all__: folder sub, "
        "attribute nothing" in warnings
    )
    assert "don't know which object to document for 'Access.pub'" in warnings
    assert documented(app, "sub/") == ["", "g.m"]


def test_option_lists(make_app, tmp_path):
    # :no-index: everywhere; folders take the class member options (also
    # :inherited-members:); options of Python's autodoc that do nothing for
    # MATLAB are errors.
    app = build(
        make_app,
        tmp_path,
        page(
            ".. mat:autoclass:: Access\n   :no-index:\n",
            ".. mat:function:: handWritten(x)\n   :no-index:\n",
            ".. mat:folder:: sub\n   :no-index:\n",
            ".. mat:autofolder:: .\n   :members: Access\n   :protected-members:\n"
            "   :no-index:\n",
            ".. mat:autofolder:: sub\n   :inherited-members:\n   :no-index:\n",
            ".. mat:autodata:: consts\n   :annotation: x\n",
            ".. mat:autofunction:: fnone\n   :no-index-entry:\n",
        ),
    )
    domain = app.env.get_domain("mat")
    assert domain.data["objects"] == {}
    assert domain.data["folders"] == {}
    assert "protected property" in html(app)
    errors = app.warning.getvalue()
    for directive in ("mat:autodata", "mat:autofunction"):
        assert f"An option to {directive} is either unknown" in errors
    assert errors.count("is either unknown") == 2


def test_more_content(make_app, tmp_path):
    app = build(
        make_app, tmp_path, page(".. mat:autofunction:: fnone\n\n   EXTRA TEXT\n")
    )
    assert "EXTRA TEXT" in html(app)


LINKS = {
    "a/dup.m": "function dup\n% DUP A\nend\n",
    "b/dup.m": "function dup\n% DUP B\nend\n",
    # ambiguous too, but only inside a word in the help (no warning)
    "c/two.m": "function two\nend\n",
    "d/two.m": "function two\nend\n",
    "runme.m": "% RUNME HELP\nx = 1;\n",
    "Props.m": (
        "classdef Props\n% PROPS HELP\n%\n% Props Properties:\n%   val - the value\n%\n"
        "% Uses dup and runme, a twofold check.\n%\n% Example::\n%\n"
        "%     y = fnone(1);\n%     z = fnone(2);\n%\n% Calls fnone.\n%\n"
        "% See also fnone, :mat:func:`fsig`, Props.val\n%   ---\n%   ignored\n"
        "properties\nval % the value\nend\nend\n"
    ),
    "NoHelp.m": "classdef NoHelp\nmethods\nfunction obj = NoHelp\nend\nend\nend\n",
}


def test_auto_links(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(".. mat:autoclass:: Props\n"),
        files={**FILES, **LINKS},
        matlab_auto_link="all",
        add_function_parentheses=False,
    )
    assert (
        "'dup' in the docstring of Props.m matches several objects: a/dup.m, b/dup.m"
    ) in app.warning.getvalue()
    assert "'two'" not in app.warning.getvalue()
    # Literal blocks are not linked; scripts are not linked by name.
    doctree = app.env.get_doctree("index")
    blocks = [n.astext() for n in doctree.findall(nodes.literal_block)]
    assert blocks == ["y = fnone(1);\nz = fnone(2);"]
    xrefs = {
        (n["reftarget"], n.astext()) for n in doctree.findall(addnodes.pending_xref)
    }
    assert ("fnone.m", "fnone") in xrefs  # no parentheses added
    assert ("Props.m.val", "val") in xrefs
    assert "runme.m" not in {target for target, _ in xrefs}
    assert "ignored" in html(app)


def test_auto_links_keep_the_markup_valid(make_app, tmp_path):
    # A link next to a character that cannot start or end inline markup is
    # separated from it by an escaped space, which the output drops.
    calls = (
        "function calls\n% CALLS HELP\n%\n"
        "% y=fnone(1); [a]=Sig.x(2); (fnone) fnone.\n"
        "%\n% See also: Sig, fnone()\n%\n% See also fsig{}\nend\n"
    )
    app = build(
        make_app,
        tmp_path,
        page(".. mat:autofunction:: calls\n"),
        files={**FILES, "calls.m": calls},
        matlab_auto_link="all",
        add_function_parentheses=False,
    )
    assert "WARNING" not in app.warning.getvalue()
    doctree = app.env.get_doctree("index")
    targets = [n["reftarget"] for n in doctree.findall(addnodes.pending_xref)]
    assert sorted(targets) == ["Sig.m", "Sig.m.x"] + ["fnone.m"] * 4 + ["fsig.m"]
    text = doctree.astext()
    assert "y=fnone(1); [a]=Sig.x(2); (fnone) fnone." in text
    # the parentheses of the last entry are the link's (none here)
    assert "See also: Sig, fnone\n" in text
    assert "See also fsig{}" in text


def test_auto_links_see_also_at_line_start(make_app, tmp_path):
    # "See also" mid-line is prose; only a line starting with it is linked.
    calls = (
        "function calls\n% CALLS HELP\n%\n"
        "% Calls sub. See also nosuchthing, fnone\n%\n"
        "%   See also Sig\nend\n"
    )
    app = build(
        make_app,
        tmp_path,
        page(".. mat:autofunction:: calls\n"),
        files={**FILES, "calls.m": calls},
        matlab_auto_link="all",
        add_function_parentheses=False,
    )
    doctree = app.env.get_doctree("index")
    targets = [n["reftarget"] for n in doctree.findall(addnodes.pending_xref)]
    assert "Sig.m" in targets
    # unknown names are literal only when a See also line parses them
    literals = [n.astext() for n in doctree.findall(nodes.literal)]
    assert "nosuchthing" not in literals
    assert "Calls sub. See also nosuchthing, fnone" in doctree.astext()


def test_auto_links_skip_names_in_markup(make_app, tmp_path):
    # A name in a "See also" literal (``Runner/go``) or between MATLAB's
    # ``|code|`` bars is not linked: a role inside would break the markup.
    walker = (
        "classdef Walker\n% WALKER HELP\nmethods\nfunction go(obj)\n% GO HELP\n%\n"
        "% See also: Runner/go\nend\nend\nend\n"
    )
    app = build(
        make_app,
        tmp_path,
        page(
            ".. mat:autoclass:: Walker\n   :members:\n",
            ".. mat:autofunction:: bars\n",
        ),
        files={
            **FILES,
            "Walker.m": walker,
            "bars.m": "function bars\n% |fnone|\nend\n",
        },
        matlab_auto_link="all",
    )
    # only the user's own markup problem: bars are a reST substitution
    warnings = app.warning.getvalue().strip().splitlines()
    assert len(warnings) == 1
    assert 'Undefined substitution referenced: "fnone"' in warnings[0]
    assert documented(app) == ["Walker.m", "Walker.m.go", "bars.m"]


def test_blank_help_lines(make_app, tmp_path):
    # Help of only blank ``%`` lines crashed the docstring signature lookup.
    files = {
        **FILES,
        "blank.m": "function blank(x)\n%\n%\nend\n",
        "BlankCtor.m": (
            "classdef BlankCtor\n% BLANK HELP\nmethods\nfunction obj = BlankCtor(x)\n"
            "%\n%\nend\nend\nend\n"
        ),
    }
    app = build(
        make_app,
        tmp_path,
        page(
            ".. mat:autofunction:: blank\n",
            ".. mat:autoclass:: BlankCtor\n   :members:\n",
        ),
        files=files,
        autoclass_content="both",
    )
    # (the constructor's help goes into the class's: autoclass_content)
    assert documented(app) == ["blank.m", "BlankCtor.m"]
    assert "WARNING" not in app.warning.getvalue()


def test_class_without_help(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(".. mat:autoclass:: NoHelp\n   :members:\n"),
        files={**FILES, **LINKS},
        autoclass_content="both",
    )
    assert documented(app) == ["NoHelp.m"]
    assert "WARNING" not in app.warning.getvalue()


def test_automethod_in_a_written_class(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(
            ".. mat:class:: Access\n\n   .. mat:automethod:: zMeth\n\n"
            "   .. mat:automethod:: nothing\n"
        ),
    )
    assert documented(app) == ["Access.m", "Access.m.zMeth"]
    warning = next(
        line
        for line in app.warning.getvalue().splitlines()
        if "don't know which object to document for 'nothing'" in line
    )
    # The page and line of the directive, and a subtype to suppress it by.
    assert re.search(r"index\.rst:\d+: WARNING", warning)
    assert "[mat.not_found]" in warning


def test_folder_members_without_a_documenter(make_app, tmp_path):
    files = {
        **FILES,
        "sub/h/inner.m": "function inner\nend\n",
        "sub/h.m": "function h\nend\n",
        "sub/deep/x.m": "function x\nend\n",
    }
    directive = ".. mat:autofolder:: sub\n   :members:\n   :undoc-members:\n"
    app = build(make_app, tmp_path, page(directive), files=files)
    # The file h.m wins over the folder h/; folders are not documented as members.
    assert documented(app, "sub/") == ["", "g.m", "h.m"]


@pytest.mark.parametrize("order", ["alphabetical", "bysource"])
def test_folder_members_ignore_the_listing_order(
    make_app, tmp_path, monkeypatch, order
):
    listdir = os.listdir
    monkeypatch.setattr(
        mat_types.os, "listdir", lambda path: sorted(listdir(path), reverse=True)
    )
    files = {**FILES, "sub/a.m": "function a\n% A HELP\nend\n"}
    directive = f".. mat:autofolder:: sub\n   :members:\n   :member-order: {order}\n"
    app = build(make_app, tmp_path, page(directive), files=files)
    assert documented(app, "sub/") == ["", "a.m", "g.m"]


def test_analyzer_failure_is_logged(make_app, tmp_path, monkeypatch):
    def unknown(modname):
        raise mat_types.MatcodeError(f"error importing {modname!r}")

    monkeypatch.setattr(mat_types.MatModuleAnalyzer, "for_module", unknown)
    app = build(
        make_app,
        tmp_path,
        page(".. mat:autoclass:: Access\n   :members:\n   :member-order: bysource\n"),
        verbosity=2,
    )
    # Without the source order, members stay alphabetical.
    assert documented(app, "Access.m.") == ["Access", "pub", "make", "zMeth"]
    assert "module analyzer failed: error importing './'" in app.status.getvalue()
