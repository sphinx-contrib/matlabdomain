"""The ``:inherited-members:`` option of ``mat:autoclass`` and ``mat:autofolder``.

The members a class inherits from the project classes among its bases are
documented under the class (``Sub.member``), each starting with "Inherited
from <base>."

MATLAB rules the walk follows: the class's own members come first, then its
bases depth-first, left to right as the ``classdef`` lists them, and the first
owner of a name wins (an override, an implemented abstract method). Base
constructors, enumeration values and private members are not inherited.
"""

import os
import time
from pathlib import Path
from typing import Any, cast

import pytest
from docutils import nodes
from sphinx import addnodes
from sphinx.errors import ConfigError
from sphinx.util import console
from sphinx.util.inventory import InventoryFile
from test_incremental_equals_clean import differences, snapshot

from sphinxcontrib import mat_handlers, mat_naming

#: matlab_inherited_members off, its default
CONF_OFF = (
    'extensions = ["sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "src"\n'
    'primary_domain = "mat"\n'
)
CONF = CONF_OFF + "matlab_inherited_members = True\n"

ROOT = """\
classdef Root < handle
    % ROOT HELP
    properties
        rootProp % root property
    end
    methods
        function obj = Root()
            % ROOT CTOR HELP
        end
        function rootMeth(obj)
            % root method
        end
    end
end
"""

BASE = """\
classdef Base < Root & matlab.mixin.Copyable
    % BASE HELP
    properties
        baseProp % base property
        baseUndoc
    end
    properties (Access = private)
        basePriv % base private property
    end
    properties (GetAccess = private, SetAccess = private)
        baseGetPriv % base get-private property
    end
    properties (Access = protected)
        baseProt % base protected property
    end
    properties (Hidden)
        baseHid % base hidden property
    end
    properties (SetAccess = protected)
        baseReadOnly % base read-only property
    end
    methods
        function obj = Base()
            % BASE CTOR HELP
        end
        function baseMeth(obj)
            % base method, calls over() and rootMeth()
        end
        function over(obj)
            % BASE OVER HELP
        end
    end
    methods (Abstract)
        impl(obj) % BASE ABSTRACT HELP
    end
    methods (Static)
        function s = baseStatic()
            % base static method
        end
    end
    methods (Access = private)
        function basePrivMeth(obj)
            % base private method
        end
    end
    events
        BaseEvent % base event
    end
    events (ListenAccess = private)
        BasePrivEvent % base private event
    end
end
"""

SUB = """\
classdef Sub < Base
    % SUB HELP, call baseMeth() first
    properties
        subProp % sub property
    end
    methods
        function obj = Sub()
            % SUB CTOR HELP
        end
        function over(obj)
            % SUB OVER HELP
        end
        function impl(obj)
            % SUB IMPL HELP
        end
    end
end
"""

FILES = {
    "src/Root.m": ROOT,
    "src/Base.m": BASE,
    "src/Sub.m": SUB,
    # enumeration values are not inherited (MATLAB: an enumeration class
    # cannot be subclassed; the rule holds for a project that tries)
    "src/Color.m": (
        "classdef Color\n% COLOR HELP\nenumeration\nRed % the red\nend\nend\n"
    ),
    "src/Shade.m": "classdef Shade < Color\n% SHADE HELP\nend\n",
}

INHERITED = {"rootProp", "rootMeth", "baseProp", "baseMeth", "baseStatic"}
INHERITED |= {"BaseEvent", "baseReadOnly"}
OWN = {"Sub", "subProp", "over", "impl"}


def write(root, files):
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def build(make_app, tmp_path, page, files=FILES, conf="", base=CONF, **kwargs):
    write(tmp_path, {**files, "conf.py": base + conf, "index.rst": page})
    app = make_app(srcdir=tmp_path, **kwargs)
    app.build()
    return app


def page(*directives):
    return "Index\n=====\n\n" + "\n".join(directives)


def autoclass(name, *options):
    return f".. mat:autoclass:: {name}\n   :members:\n" + "".join(
        f"   {option}\n" for option in options
    )


def signatures(app, docname="index"):
    return [
        node
        for node in app.env.get_doctree(docname).findall(addnodes.desc_signature)
        if node["names"]
    ]


def documented(app, prefix):
    """Return the documented member names of the class with reference ``prefix``."""
    names = [n["names"][0] for n in signatures(app)]
    return [r[len(prefix) :] for r in names if r.startswith(prefix)]


def descriptions(app, ref):
    """Text of each description of ``ref`` on the index page."""
    return [node.parent.astext() for node in signatures(app) if node["names"][0] == ref]


def warnings(app):
    text = cast(Any, console).strip_escape_sequences(app.warning.getvalue())
    return [line for line in text.splitlines() if "WARNING" in line or "ERROR" in line]


def xrefs(app, docname="index"):
    return [
        (n["reftype"], n["reftarget"])
        for n in app.env.get_doctree(docname).findall(addnodes.pending_xref)
    ]


# --- what is inherited --------------------------------------------------------


def test_without_the_option_no_base_members(make_app, tmp_path):
    # The case of PR #346 (issue #180): a class in a namespace whose base is
    # in the same namespace.
    files = {
        "src/+pkg/BaseTable.m": (
            "classdef BaseTable < handle\n    % BaseTable - A base class.\n"
            "    properties\n        baseProp % A property of the base class.\n"
            "    end\n    methods\n        function obj = BaseTable(x)\n"
            "            % BaseTable - Base constructor.\n        end\n"
            "        function addRow(obj, val)\n"
            "            % addRow - Add a row, defined on the base class.\n"
            "        end\n    end\nend\n"
        ),
        "src/+pkg/DerivedTable.m": (
            "classdef DerivedTable < pkg.BaseTable\n    % DerivedTable - A derived "
            "class.\n    properties\n        derivedProp % A property of the derived "
            "class.\n    end\n    methods\n        function obj = DerivedTable(y)\n"
            "            % DerivedTable - Derived constructor.\n        end\n"
            "        function ownMethod(obj)\n            % ownMethod - A method of "
            "the derived class.\n        end\n    end\nend\n"
        ),
    }
    app = build(
        make_app,
        tmp_path,
        page(
            autoclass("pkg.DerivedTable", ":show-inheritance:"),
            autoclass("pkg.DerivedTable", ":inherited-members:", ":no-index:"),
        ),
        files,
    )
    prefix = "+pkg/DerivedTable.m."
    assert sorted(documented(app, prefix)) == [
        "DerivedTable",
        "derivedProp",
        "ownMethod",
    ]
    text = app.env.get_doctree("index").astext()
    without, _, with_option = text.partition("DerivedTable - A derived class.")[
        2
    ].partition("DerivedTable - A derived class.")
    assert "addRow" not in without
    assert "baseProp" not in without
    assert "addRow(val)" in with_option
    assert "baseProp" in with_option
    assert "Base constructor" not in text
    assert warnings(app) == []


def test_base_members_are_documented_under_the_class(make_app, tmp_path):
    app = build(make_app, tmp_path, page(autoclass("Sub", ":inherited-members:")))
    assert set(documented(app, "Sub.m.")) == OWN | INHERITED
    # nothing is documented under the bases
    assert documented(app, "Base.m.") == documented(app, "Root.m.") == []
    signature = next(n for n in signatures(app) if n["names"] == ["Sub.m.baseMeth"])
    assert signature["ids"] == [mat_naming.make_target_id("Sub.m.baseMeth")]
    (text,) = descriptions(app, "Sub.m.baseMeth")
    assert text.startswith("baseMeth()\n\nInherited from Base.\n\nbase method")
    (text,) = descriptions(app, "Sub.m.rootProp")
    assert "Inherited from Root." in text
    assert ("class", "Base.m") in xrefs(app)
    assert ("class", "Root.m") in xrefs(app)
    # the link to the base resolves when the base is documented
    assert warnings(app) == []


def test_inherited_link_line_in_the_html(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(
            autoclass("Base"),
            autoclass("Root"),
            autoclass("Sub", ":inherited-members:"),
        ),
    )
    html = (Path(app.outdir) / "index.html").read_text(encoding="utf-8")
    assert html.count("Inherited from") == len(INHERITED)
    link = (
        'Inherited from <a class="reference internal" href="#mat-Base.m" '
        'title="Base"><code class="xref mat mat-class docutils literal notranslate">'
        '<span class="pre">Base</span></code></a>.'
    )
    assert link in html


def test_override_and_implemented_abstract_method_appear_once(make_app, tmp_path):
    app = build(make_app, tmp_path, page(autoclass("Sub", ":inherited-members:")))
    names = documented(app, "Sub.m.")
    assert names.count("over") == names.count("impl") == 1
    (over,) = descriptions(app, "Sub.m.over")
    assert "SUB OVER HELP" in over
    assert "Inherited from" not in over
    (impl,) = descriptions(app, "Sub.m.impl")
    assert "SUB IMPL HELP" in impl
    assert "abstract" not in impl
    text = app.env.get_doctree("index").astext()
    assert "BASE OVER HELP" not in text
    assert "BASE ABSTRACT HELP" not in text


def test_base_constructors_are_not_inherited(make_app, tmp_path):
    app = build(make_app, tmp_path, page(autoclass("Sub", ":inherited-members:")))
    text = app.env.get_doctree("index").astext()
    assert "BASE CTOR HELP" not in text
    assert "ROOT CTOR HELP" not in text
    assert "Base" not in documented(app, "Sub.m.")
    assert "Root" not in documented(app, "Sub.m.")
    # the constructor section holds the class's own constructor only
    constructor = text.split("Constructor Summary")[1].split("Property Summary")[0]
    assert "SUB CTOR HELP" in constructor


def test_static_method_is_inherited(make_app, tmp_path):
    app = build(make_app, tmp_path, page(autoclass("Sub", ":inherited-members:")))
    signature = next(n for n in signatures(app) if n["names"] == ["Sub.m.baseStatic"])
    assert signature.parent["objtype"] == "staticmethod"


def test_enumeration_values_are_not_inherited(make_app, tmp_path):
    app = build(make_app, tmp_path, page(autoclass("Shade", ":inherited-members:")))
    assert documented(app, "Shade.m.") == []
    assert "Enumeration Values" not in app.env.get_doctree("index").astext()


def test_inherited_entries_are_objects_like_any_member(make_app, tmp_path):
    # objects.inv and the stable addresses list them; the base's own entry on
    # the same page has another anchor, so there is no duplicate.
    app = build(
        make_app,
        tmp_path,
        page(
            autoclass("Base"),
            autoclass("Root"),
            autoclass("Sub", ":inherited-members:"),
        ),
        conf="nitpicky = True\n",
    )
    assert warnings(app) == []
    objects = app.env.get_domain("mat").data["objects"]
    assert objects["Sub.m.baseMeth"] == ("index", "method", "Sub.baseMeth")
    assert objects["Base.m.baseMeth"] == ("index", "method", "Base.baseMeth")
    ids = {n["names"][0]: n["ids"] for n in signatures(app)}
    assert ids["Sub.m.baseMeth"] != ids["Base.m.baseMeth"]
    outdir = Path(app.outdir)
    with open(outdir / "objects.inv", "rb") as f:
        inv = InventoryFile.load(cast(Any, f), "", lambda _base, uri: uri)
    assert "Sub.m.baseMeth" in inv["mat:method"]
    assert "Sub.m.BaseEvent" in inv["mat:event"]
    assert (outdir / "mat/ref/Sub.m.baseMeth.html").is_file()
    assert (outdir / "mat/name/Sub.baseMeth.html").is_file()


# --- access ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("options", "added"),
    [
        ((), set()),
        ((":private-members:",), {"subPriv"}),
        ((":protected-members:",), {"baseProt"}),
        ((":hidden-members:",), {"baseHid"}),
        ((":undoc-members:",), {"baseUndoc"}),
    ],
)
def test_access_rules_apply_to_inherited_members(make_app, tmp_path, options, added):
    files = {
        **FILES,
        "src/Sub.m": SUB.replace(
            "    methods\n",
            "    methods (Access = private)\n        function subPriv(obj)\n"
            "            % sub private method\n        end\n    end\n    methods\n",
            1,
        ),
    }
    app = build(
        make_app,
        tmp_path,
        page(autoclass("Sub", ":inherited-members:", *options)),
        files,
    )
    assert set(documented(app, "Sub.m.")) == OWN | INHERITED | added


def test_private_base_members_are_never_inherited(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("Sub", ":inherited-members:", ":private-members:")),
    )
    names = set(documented(app, "Sub.m."))
    assert names.isdisjoint(
        {"basePriv", "baseGetPriv", "basePrivMeth", "BasePrivEvent"}
    )
    text = app.env.get_doctree("index").astext()
    assert "base private" not in text
    assert "base get-private" not in text


def test_exclude_members_and_skip_member_apply(make_app, tmp_path):
    conf = (
        "def skip(app, what, name, obj, skip, options):\n"
        "    return True if name == 'rootMeth' else None\n\n"
        "def setup(app):\n"
        "    app.connect('autodoc-skip-member', skip)\n"
    )
    app = build(
        make_app,
        tmp_path,
        page(autoclass("Sub", ":inherited-members:", ":exclude-members: baseProp")),
        conf=conf,
    )
    assert set(documented(app, "Sub.m.")) == OWN | INHERITED - {"baseProp", "rootMeth"}


def test_members_may_name_inherited_members(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(
            ".. mat:autoclass:: Sub\n   :members: baseMeth, subProp, basePriv\n"
            "   :inherited-members:\n"
        ),
    )
    assert documented(app, "Sub.m.") == ["subProp", "baseMeth"]
    (text,) = descriptions(app, "Sub.m.baseMeth")
    assert "Inherited from Base." in text
    # a private base member is not a member of Sub
    (warning,) = warnings(app)
    assert "missing attribute basePriv in object Sub.m" in warning


def test_named_members_without_the_option(make_app, tmp_path):
    app = build(
        make_app, tmp_path, page(".. mat:autoclass:: Sub\n   :members: baseMeth\n")
    )
    assert documented(app, "Sub.m.") == []
    (warning,) = warnings(app)
    assert "missing attribute baseMeth in object Sub.m" in warning


# --- the walk -------------------------------------------------------------------

DIAMOND = {
    "src/Top.m": (
        "classdef Top < handle\n% TOP\nproperties\ntopProp % top property\nend\nend\n"
    ),
    "src/Left.m": (
        "classdef Left < Top\n% LEFT\nproperties\nleftProp % left property\nend\nend\n"
    ),
    "src/Right.m": (
        "classdef Right < Top\n% RIGHT\nproperties\nrightProp % right property\n"
        "end\nend\n"
    ),
    "src/Bottom.m": "classdef Bottom < Left & Right\n% BOTTOM\nend\n",
    # the left base comes first: both declare "both"
    "src/One.m": "classdef One\n% ONE\nproperties\nboth % ONE BOTH\nend\nend\n",
    "src/Two.m": "classdef Two\n% TWO\nproperties\nboth % TWO BOTH\nend\nend\n",
    "src/Pair.m": "classdef Pair < One & Two\n% PAIR\nend\n",
    # depth-first: Deep's member (through Mid) before Near's
    "src/Deep.m": "classdef Deep\n% DEEP\nproperties\nx % DEEP X\nend\nend\n",
    "src/Mid.m": "classdef Mid < Deep\n% MID\nend\n",
    "src/Near.m": "classdef Near\n% NEAR\nproperties\nx % NEAR X\nend\nend\n",
    "src/Far.m": "classdef Far < Mid & Near\n% FAR\nend\n",
    # a cycle of bases (not valid MATLAB) ends
    "src/CycA.m": "classdef CycA < CycB\n% CYCA\nproperties\na % cyc a\nend\nend\n",
    "src/CycB.m": "classdef CycB < CycA\n% CYCB\nproperties\nb % cyc b\nend\nend\n",
    "src/Self.m": "classdef Self < Self\n% SELF\nproperties\ns % self s\nend\nend\n",
}


def test_three_levels(make_app, tmp_path):
    app = build(make_app, tmp_path, page(autoclass("Sub", ":inherited-members:")))
    (text,) = descriptions(app, "Sub.m.rootMeth")
    assert "Inherited from Root." in text


def test_diamond_documents_the_root_members_once(make_app, tmp_path):
    app = build(
        make_app, tmp_path, page(autoclass("Bottom", ":inherited-members:")), DIAMOND
    )
    assert documented(app, "Bottom.m.") == ["leftProp", "rightProp", "topProp"]
    (text,) = descriptions(app, "Bottom.m.topProp")
    assert "Inherited from Top." in text


def test_the_first_base_wins(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(
            autoclass("Pair", ":inherited-members:"),
            autoclass("Far", ":inherited-members:"),
        ),
        DIAMOND,
    )
    (both,) = descriptions(app, "Pair.m.both")
    assert "ONE BOTH" in both
    (x,) = descriptions(app, "Far.m.x")
    assert "DEEP X" in x


def test_a_cycle_of_bases_ends(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(
            autoclass("CycA", ":inherited-members:"),
            autoclass("Self", ":inherited-members:"),
        ),
        DIAMOND,
    )
    assert documented(app, "CycA.m.") == ["a", "b"]
    assert documented(app, "Self.m.") == ["s"]
    assert warnings(app) == []


def test_bases_outside_the_project_are_skipped_quietly(make_app, tmp_path, monkeypatch):
    files = {
        "src/a/Amb.m": "classdef Amb\n% AMB A\nproperties\nambA % amb a\nend\nend\n",
        "src/b/Amb.m": "classdef Amb\n% AMB B\nproperties\nambB % amb b\nend\nend\n",
        "src/Broken.m": (
            "classdef Broken\n% BROKEN\nproperties\nbr % broken\nend\nend\n"
        ),
        "src/Ext.m": (
            "classdef Ext < handle & matlab.mixin.Copyable & NoSuchClass & Amb"
            " & Broken\n"
            "% EXT\nproperties\nown % own property\nend\nend\n"
        ),
    }
    parse = mat_handlers.MFileHandler.parse

    def broken(self, path, *args, **kwargs):
        if path.endswith("Broken.m"):
            raise ValueError("cannot parse this")
        return parse(self, path, *args, **kwargs)

    monkeypatch.setattr(mat_handlers.MFileHandler, "parse", broken)
    app = build(
        make_app, tmp_path, page(autoclass("Ext", ":inherited-members:")), files
    )
    assert documented(app, "Ext.m.") == ["own"]
    # the parse failure is the only warning
    (warning,) = warnings(app)
    assert "Broken.m cannot be parsed" in warning


CLASS_FOLDER = {
    "src/+geo/@Poly/Poly.m": (
        "classdef Poly < handle\n    % POLY HELP\n    properties\n"
        "        corners % the corners\n    end\n    methods\n"
        "        p = perimeter(obj)\n    end\n    methods (Access = private)\n"
        "        hidden = secret(obj)\n    end\nend\n"
    ),
    "src/+geo/@Poly/perimeter.m": (
        "function p = perimeter(obj)\n% PERIMETER the length of the border\n"
        "p = 0;\nend\n"
    ),
    "src/+geo/@Poly/secret.m": "function s = secret(obj)\n% SECRET HELP\nend\n",
    "src/+other/Tri.m": "classdef Tri < geo.Poly\n% TRI HELP\nend\n",
}


def test_base_in_a_class_folder_of_another_namespace(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("other.Tri", ":inherited-members:", ":private-members:")),
        CLASS_FOLDER,
    )
    assert documented(app, "+other/Tri.m.") == ["corners", "perimeter"]
    (text,) = descriptions(app, "+other/Tri.m.perimeter")
    assert "Inherited from geo.Poly." in text
    assert "the length of the border" in text
    assert ("class", "+geo/@Poly/Poly.m") in xrefs(app)
    assert warnings(app) == []


# --- stop list --------------------------------------------------------------------

STOP = {
    "src/+ns/Base0.m": "classdef Base0\n% BASE0\nproperties\nzero % zero\nend\nend\n",
    "src/+ns/Stopper.m": (
        "classdef Stopper < ns.Base0\n% STOPPER\nproperties\nstopped % stopped\n"
        "end\nend\n"
    ),
    "src/+ns/Other.m": (
        "classdef Other\n% OTHER\nproperties\nother % other\nend\nend\n"
    ),
    "src/+ns/Through.m": "classdef Through < ns.Base0\n% THROUGH\nend\n",
    "src/+ns/Leaf.m": "classdef Leaf < ns.Stopper & ns.Other\n% LEAF\nend\n",
    "src/+ns/Both.m": "classdef Both < ns.Stopper & ns.Through\n% BOTH\nend\n",
}


@pytest.mark.parametrize("name", ["Stopper", "ns.Stopper"])
def test_stop_list_leaves_out_a_base_and_its_bases(make_app, tmp_path, name):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("ns.Leaf", f":inherited-members: {name}")),
        STOP,
    )
    assert documented(app, "+ns/Leaf.m.") == ["other"]


def test_stop_list_keeps_bases_reached_another_way(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(
            autoclass("ns.Both", ":inherited-members: ns.Stopper"),
            autoclass("ns.Leaf", ":inherited-members: ns.Base0, ns.Other"),
        ),
        STOP,
    )
    assert documented(app, "+ns/Both.m.") == ["zero"]
    assert documented(app, "+ns/Leaf.m.") == ["stopped"]


def test_without_a_stop_list_all_bases(make_app, tmp_path):
    app = build(
        make_app, tmp_path, page(autoclass("ns.Leaf", ":inherited-members:")), STOP
    )
    assert documented(app, "+ns/Leaf.m.") == ["other", "stopped", "zero"]


# --- locations and links ----------------------------------------------------------

LOCATED = {
    "src/lib/Base2.m": (
        "classdef Base2 < handle\n"
        "    % BASE2 HELP\n"
        "    methods\n"
        "        function meth(obj)\n"
        "            % METH HELP\n"
        "            %\n"
        "            % Broken `markup here.\n"
        "            %\n"
        "            % .. image:: pic.png\n"
        "            %\n"
        "            % See also libHelper\n"
        "        end\n"
        "    end\n"
        "end\n"
    ),
    "src/lib/private/libHelper.m": "function libHelper\n% LIBHELPER HELP\nend\n",
    "src/lib/pic.png": "not really a picture",
    "src/app/Sub2.m": "classdef Sub2 < Base2\n% SUB2 HELP\nend\n",
}


def test_warnings_of_inherited_help_name_the_base_file(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("app/Sub2.m", ":inherited-members:")),
        LOCATED,
    )
    base = tmp_path / "src" / "lib" / "Base2.m"
    (warning,) = warnings(app)
    # Sphinx normalizes the whole location as a path: on Windows the
    # reference has backslashes too.
    assert warning.replace("\\", "/").startswith(
        f"{base.as_posix()}:docstring of lib/Base2.m.meth:7: WARNING: Inline"
    )


def test_relative_paths_in_inherited_help_resolve_from_the_base(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("app/Sub2.m", ":inherited-members:")),
        LOCATED,
    )
    (image,) = app.env.get_doctree("index").findall(nodes.image)
    assert image["uri"].endswith("src/lib/pic.png")


def test_see_also_in_inherited_help_resolves_from_the_base(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("app/Sub2.m", ":inherited-members:")),
        LOCATED,
        conf='matlab_auto_link = "basic"\n',
    )
    assert ("func", "lib/private/libHelper.m") in xrefs(app)


ROLES = {
    "src/lib/Base3.m": (
        "classdef Base3\n"
        "    % BASE3 HELP\n"
        "    methods\n"
        "        function run(obj)\n"
        "            % RUN HELP, see :mat:func:`helper`, :mat:func:`secret`\n"
        "            % and :mat:meth:`other`.\n"
        "        end\n"
        "        function other(obj)\n"
        "            % OTHER HELP\n"
        "        end\n"
        "    end\n"
        "end\n"
    ),
    "src/lib/helper.m": "function helper\n% HELPER of lib\nend\n",
    "src/lib/private/secret.m": "function secret\n% SECRET HELP\nend\n",
    "src/app/helper.m": "function helper\n% HELPER of app\nend\n",
    "src/app/Sub3.m": "classdef Sub3 < Base3\n% SUB3 HELP\nend\n",
}


def test_roles_in_inherited_help_resolve_from_the_base(make_app, tmp_path):
    # A role in the help of a base member names what the base's folder sees:
    # its own helper, not the one in the folder of the subclass, and the
    # private function of its folder. A member name is one of the class
    # documented.
    app = build(
        make_app,
        tmp_path,
        page(
            autoclass("app/Sub3.m", ":inherited-members:"),
            autoclass("lib/Base3.m"),
            ".. mat:autofunction:: lib/helper.m\n",
            ".. mat:autofunction:: app/helper.m\n",
            ".. mat:autofunction:: lib/private/secret.m\n",
        ),
        ROLES,
        conf="nitpicky = True\n",
    )
    assert warnings(app) == []
    html = (Path(app.outdir) / "index.html").read_text(encoding="utf-8")
    run = html[html.index('id="mat-app/Sub3.m.run"') :]
    run = run[: run.index("</dd>")]
    assert 'href="#mat-lib/helper.m"' in run
    assert 'href="#mat-app/helper.m"' not in run
    assert 'href="#mat-lib/private/secret.m"' in run
    assert 'href="#mat-app/Sub3.m.other"' in run


def test_generated_lines_of_an_inherited_member_name_the_base_file(make_app, tmp_path):
    # The base is on no page, so the link of "Inherited from" finds no target:
    # the warning is at the declaration of the member in the base's file.
    app = build(
        make_app,
        tmp_path,
        page(autoclass("app/Sub2.m", ":inherited-members:")),
        {**LOCATED, "src/lib/pic.png": ""},
        conf="nitpicky = True\n",
    )
    base = tmp_path / "src" / "lib" / "Base2.m"
    assert [w for w in warnings(app) if "mat:class" in w] == [
        f"{base}:4: WARNING: mat:class reference target not found: "
        "lib/Base2.m [ref.class]"
    ]


def test_method_links_go_to_the_inherited_entries(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("Sub", ":inherited-members:")),
        conf='matlab_auto_link = "all"\n',
    )
    found = xrefs(app)
    # in the class's help, and in the help of an inherited method
    assert ("meth", "Sub.m.baseMeth") in found
    assert ("meth", "Sub.m.over") in found
    assert ("meth", "Sub.m.rootMeth") in found
    assert ("meth", "Base.m.over") not in found
    assert warnings(app) == []


def test_see_also_of_a_base_member_links_to_the_inherited_entry(make_app, tmp_path):
    # "See also baseProp" in the help of Base's baseMeth names a member of the
    # class that documents it: Sub, here.
    files = {
        **FILES,
        "src/Base.m": BASE.replace(
            "% base method, calls over() and rootMeth()",
            "% base method\n            %\n            % See also baseProp",
        ),
    }
    app = build(
        make_app,
        tmp_path,
        page(autoclass("Sub", ":inherited-members:")),
        files,
        conf='matlab_auto_link = "basic"\n',
    )
    assert ("attr", "Sub.m.baseProp") in xrefs(app)


# --- options --------------------------------------------------------------------


def test_autofolder_applies_it_to_its_classes(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(".. mat:autofolder:: .\n   :members: Sub\n   :inherited-members: Root\n"),
    )
    assert set(documented(app, "Sub.m.")) == OWN | INHERITED - {"rootProp", "rootMeth"}


NAMESPACE = {
    "src/+pkg/Base.m": (
        "classdef Base\n    % BASE HELP\n    methods\n"
        "        function baseMeth(obj)\n            % base method\n"
        "        end\n    end\nend\n"
    ),
    "src/+pkg/Sub.m": (
        "classdef Sub < pkg.Base\n    % SUB HELP\n    methods\n"
        "        function subMeth(obj)\n            % sub method\n"
        "        end\n    end\nend\n"
    ),
}


def test_autonamespace_applies_it_to_its_classes(make_app, tmp_path):
    # the namespace directive has the options of the folder directive
    directive = ".. mat:autonamespace:: pkg\n   :members:\n   :inherited-members:\n"
    app = build(make_app, tmp_path, page(directive), NAMESPACE)
    assert set(documented(app, "+pkg/Sub.m.")) == {"subMeth", "baseMeth"}
    assert warnings(app) == []
    app.cleanup()  # else the next app warns that it registers again
    off = build(make_app, tmp_path / "off", page(directive), NAMESPACE, base=CONF_OFF)
    assert set(documented(off, "+pkg/Sub.m.")) == {"subMeth"}
    index = (tmp_path / "off" / "index.rst").as_posix()
    assert posix_warnings(off) == [f"{index}:4: {NEEDS}"]


@pytest.mark.parametrize("value", [True, "", "Root"])
def test_autodoc_default_options(make_app, tmp_path, value):
    app = build(
        make_app,
        tmp_path,
        page(
            autoclass("Sub"), autoclass("Sub", ":no-inherited-members:", ":no-index:")
        ),
        conf=f"autodoc_default_options = {{'inherited-members': {value!r}}}\n",
    )
    expected = OWN | INHERITED
    if value == "Root":
        expected -= {"rootProp", "rootMeth"}
    assert set(documented(app, "Sub.m.")) == expected
    # :no-inherited-members: turns it off
    assert app.env.get_doctree("index").astext().count("Inherited from") == len(
        expected - OWN
    )


def test_autodoc_default_options_false_is_off(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("Sub")),
        conf="autodoc_default_options = {'inherited-members': False}\n",
    )
    assert set(documented(app, "Sub.m.")) == OWN


def test_member_order_bysource_puts_own_members_first(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("Sub", ":inherited-members:", ":member-order: bysource")),
    )
    names = documented(app, "Sub.m.")
    methods = [
        n for n in names if n in {"over", "impl", "baseMeth", "baseStatic", "rootMeth"}
    ]
    assert methods == ["over", "impl", "baseMeth", "baseStatic", "rootMeth"]


# --- builds -----------------------------------------------------------------------


def _age(root):
    stamp = time.time_ns() - 60 * 10**9
    for path in root.rglob("*"):
        os.utime(path, ns=(stamp, stamp))


def _edit_base(root):
    target = root / "src" / "Base.m"
    target.write_text(BASE.replace("% base method,", "% base method, now longer,"))
    now = time.time_ns()
    os.utime(target, ns=(now, now))


def _html_build(make_app, root, **kwargs):
    app = make_app("html", srcdir=root, builddir=root / "_build", **kwargs)
    app.build()
    app.cleanup()
    return app


# more than five documents, so that -j reads in parallel
INDEX = "Index\n=====\n\n.. toctree::\n\n   base\n   sub\n   p1\n   p2\n   p3\n"
PAGES = {
    "index.rst": INDEX,
    "base.rst": "Base\n====\n\n" + autoclass("Base"),
    # the only use of Base.m and Root.m on this page is the inheritance
    "sub.rst": "Sub\n===\n\n" + autoclass("Sub", ":inherited-members:"),
    **{f"p{i}.rst": f"P{i}\n==\n\nText.\n" for i in (1, 2, 3)},
}


def test_a_change_of_the_base_rebuilds_the_subclass_page(make_app, tmp_path):
    inc = tmp_path / "inc"
    write(inc, {**FILES, **PAGES, "conf.py": CONF})
    _age(inc)
    _html_build(make_app, inc)
    _edit_base(inc)
    app = _html_build(make_app, inc)
    assert "sub" in app.env.get_domain("mat").read_docnames
    clean = tmp_path / "clean"
    write(clean, {**FILES, **PAGES, "conf.py": CONF})
    _edit_base(clean)
    _html_build(make_app, clean)
    assert "now longer" in (inc / "_build/html/sub.html").read_text(encoding="utf-8")
    a, b = snapshot(inc / "_build/html"), snapshot(clean / "_build/html")
    assert differences(a, b) == []


def test_parallel_build_equals_serial(make_app, tmp_path):
    pages = {
        **PAGES,
        "index.rst": INDEX + "   both\n",
        "both.rst": "Both\n====\n\n"
        + autoclass("Sub", ":inherited-members:", ":no-index:"),
    }
    out = {}
    for name, parallel in (("serial", 0), ("parallel", 2)):
        root = tmp_path / name
        write(root, {**FILES, **pages, "conf.py": CONF})
        app = _html_build(make_app, root, parallel=parallel)
        out[name] = (snapshot(root / "_build/html"), warnings(app))
    assert differences(out["serial"][0], out["parallel"][0]) == []
    assert out["serial"][1] == out["parallel"][1] == []


# --- matlab_inherited_members: off by default -------------------------------------

NEEDS = (
    "WARNING: [sphinxcontrib-matlabdomain] :inherited-members: needs "
    "matlab_inherited_members = True in conf.py; the inherited members are "
    "left out [mat.directive]"
)


def posix_warnings(app):
    """Return the warnings, with the paths in them written with ``/``."""
    return [line.replace(os.sep, "/") for line in warnings(app)]


def test_off_the_option_inherits_nothing_and_warns_once_per_directive(
    make_app, tmp_path
):
    app = build(
        make_app,
        tmp_path,
        page(
            autoclass("Sub", ":inherited-members:"),
            ".. mat:autofolder:: .\n   :members: Sub\n   :inherited-members: Root\n"
            "   :no-index:\n",
            autoclass("Sub", ":no-index:"),
        ),
        base=CONF_OFF,
    )
    assert set(documented(app, "Sub.m.")) == OWN
    assert "Inherited from" not in app.env.get_doctree("index").astext()
    index = (tmp_path / "index.rst").as_posix()
    assert posix_warnings(app) == [f"{index}:4: {NEEDS}", f"{index}:8: {NEEDS}"]


def test_off_the_bases_are_not_read(make_app, tmp_path):
    root = tmp_path / "off"
    write(root, {**FILES, **PAGES, "conf.py": CONF_OFF})
    _age(root)
    app = _html_build(make_app, root)
    domain = app.env.get_domain("mat")
    used = {Path(path).name for path in domain.data["doc_sources"]["sub"]}
    assert used == {"Sub.m"}
    _edit_base(root)
    app = _html_build(make_app, root)
    assert app.env.get_domain("mat").read_docnames == ["base"]


@pytest.mark.parametrize("value", [True, "", "Root"])
def test_off_autodoc_default_options_warn_once_for_the_build(make_app, tmp_path, value):
    app = build(
        make_app,
        tmp_path,
        page(
            autoclass("Sub"),
            autoclass("Base", ":no-index:"),
            ".. mat:autofolder:: .\n   :members: Sub\n   :no-index:\n",
        ),
        conf=f"autodoc_default_options = {{'inherited-members': {value!r}}}\n",
        base=CONF_OFF,
    )
    assert set(documented(app, "Sub.m.")) == OWN
    assert posix_warnings(app) == [
        "WARNING: [sphinxcontrib-matlabdomain] autodoc_default_options sets "
        "inherited-members, which needs matlab_inherited_members = True in "
        "conf.py; the inherited members are left out [mat.directive]"
    ]


def test_off_a_written_option_warns_with_autodoc_default_options_too(
    make_app, tmp_path
):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("Sub", ":inherited-members:")),
        conf="autodoc_default_options = {'inherited-members': True}\n",
        base=CONF_OFF,
    )
    found = posix_warnings(app)
    assert len(found) == 2
    assert found[1] == f"{(tmp_path / 'index.rst').as_posix()}:4: {NEEDS}"


@pytest.mark.parametrize("base", [CONF_OFF, CONF], ids=["off", "on"])
def test_turning_the_option_off_never_warns(make_app, tmp_path, base):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("Sub", ":no-inherited-members:"), autoclass("Base")),
        conf="autodoc_default_options = {'inherited-members': False}\n",
        base=base,
    )
    assert set(documented(app, "Sub.m.")) == OWN
    assert warnings(app) == []


def test_on_nothing_warns(make_app, tmp_path):
    app = build(
        make_app,
        tmp_path,
        page(autoclass("Sub", ":inherited-members:"), autoclass("Base")),
        conf="autodoc_default_options = {'inherited-members': True}\n",
    )
    assert set(documented(app, "Sub.m.")) == OWN | INHERITED
    assert warnings(app) == []


@pytest.mark.parametrize("value", [1, "yes", None])
def test_matlab_inherited_members_must_be_a_bool(make_app, tmp_path, value):
    with pytest.raises(ConfigError) as err:
        build(
            make_app,
            tmp_path,
            page(autoclass("Sub")),
            conf=f"matlab_inherited_members = {value!r}\n",
            base=CONF_OFF,
        )
    assert str(err.value) == f"matlab_inherited_members must be bool, not {value!r}."


def test_off_parallel_build_warns_as_serial(make_app, tmp_path):
    pages = {
        **PAGES,
        "index.rst": INDEX + "   both\n",
        "both.rst": "Both\n====\n\n"
        + autoclass("Sub", ":inherited-members:", ":no-index:"),
    }
    out = {}
    for name, parallel in (("serial", 0), ("parallel", 2)):
        root = tmp_path / name
        write(root, {**FILES, **pages, "conf.py": CONF_OFF})
        app = _html_build(make_app, root, parallel=parallel)
        # sorted: the workers of a parallel build report in any order
        found = sorted(
            w.replace(root.as_posix(), "<root>") for w in posix_warnings(app)
        )
        out[name] = (snapshot(root / "_build/html"), found)
    assert differences(out["serial"][0], out["parallel"][0]) == []
    assert out["serial"][1] == out["parallel"][1]
    assert out["serial"][1] == [
        f"<root>/both.rst:4: {NEEDS}",
        f"<root>/sub.rst:4: {NEEDS}",
    ]


@pytest.mark.parametrize(
    ("before", "after"), [(CONF_OFF, CONF), (CONF, CONF_OFF)], ids=["on", "off"]
)
def test_switching_the_value_equals_a_clean_build(make_app, tmp_path, before, after):
    inc = tmp_path / "inc"
    write(inc, {**FILES, **PAGES, "conf.py": before})
    _age(inc)
    _html_build(make_app, inc)
    write(inc, {"conf.py": after})
    app = _html_build(make_app, inc)
    assert "sub" in app.env.get_domain("mat").read_docnames
    clean = tmp_path / "clean"
    write(clean, {**FILES, **PAGES, "conf.py": after})
    _html_build(make_app, clean)
    a, b = snapshot(inc / "_build/html"), snapshot(clean / "_build/html")
    assert differences(a, b) == []
