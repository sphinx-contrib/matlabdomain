"""MATLAB class, method and property attributes in the rendered signatures."""

import json
import re

import pytest

# MATLAB R2026a and R2026b agree on every attribute here (meta.class).
SOURCES = {
    "+zoo/Animal.m": """\
classdef (Abstract) Animal < handle
    % ANIMAL An abstract animal.
    properties (Abstract)
        Legs  % LEGS Number of legs.
    end
    properties (Constant)
        Kingdom = "animalia"  % KINGDOM Always animalia.
    end
    properties (Dependent)
        Name  % NAME Computed name.
    end
    properties (SetAccess = immutable)
        Id  % ID Set once.
    end
    properties (GetAccess = public, SetAccess = ?zoo.Keeper)
        Pen  % PEN Set by keepers.
    end
    properties (Access = protected)
        Food  % FOOD Same read and set access: not read-only.
    end
    methods (Abstract)
        % SPEAK Make a sound.
        s = speak(obj, loud)
        % MOVE Move somewhere.
        %   It moves.
        move(obj, where)  % MOVE inline loses to the block above
        wake(obj)
        sleep(obj)
        % SLEEP Below it.

        rest(obj)

        % after rest and a blank line
    end
    methods (Sealed)
        function n = name(obj)
            % NAME Its name.
            n = class(obj);
        end
    end
end
""",
    "+zoo/Size.m": """\
classdef (Sealed) Size
    % SIZE Animal sizes.
    properties
        Rank  % RANK Its rank.
    end
    methods
        function obj = Size(rank)
            % SIZE Make a size.
            if nargin
                obj.Rank = rank;
            end
        end
    end
    enumeration
        Small (1)  % SMALL Small.
        Large (10)  % LARGE Large.
        Unknown  % UNKNOWN No argument.
    end
end
""",
}
PAGE = """\
Zoo
===

.. mat:autoclass:: +zoo/Animal.m
   :members:
   :undoc-members:
   :protected-members:

.. mat:autoclass:: +zoo/Size.m
   :members:
"""


def build(make_app, tmp_path, builder="text", **overrides):
    files = {
        **SOURCES,
        "conf.py": 'extensions = ["sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "."\n',
        "index.rst": PAGE,
    }
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text, encoding="utf-8")
    app = make_app(builder, srcdir=tmp_path, freshenv=True, confoverrides=overrides)
    app.build()
    return app


def signatures(text):
    """Return the class and member signature lines of a text build."""
    return [
        line.strip()
        for line in text.splitlines()
        if re.match(r"(\S.*class | {6}\S)", line)
    ]


@pytest.mark.parametrize("show_default", [True, False])
def test_attribute_prefixes(make_app, tmp_path, show_default):
    app = build(make_app, tmp_path, matlab_show_property_default_value=show_default)
    assert app.warning.getvalue() == ""
    lines = signatures((app.outdir / "index.txt").read_text(encoding="utf-8"))
    kingdom = 'constant Kingdom = "animalia"' if show_default else "constant Kingdom"
    small, large = ("Small (1)", "Large (10)") if show_default else ("Small", "Large")
    assert lines == [
        "abstract class zoo.Animal",
        "Food",
        "read-only Id",
        kingdom,
        "abstract Legs",
        "dependent Name",
        "read-only Pen",
        "abstract move(where)",
        "sealed name()",
        "abstract rest()",
        "abstract sleep()",
        "abstract speak(loud)",
        "abstract wake()",
        "sealed class zoo.Size",
        "Size(rank)",
        "Rank",
        large,
        small,
        "Unknown",
    ]


def test_abstract_method_help_and_inventory(make_app, tmp_path):
    app = build(make_app, tmp_path)
    text = (app.outdir / "index.txt").read_text(encoding="utf-8")
    assert "SPEAK Make a sound." in text
    assert "MOVE Move somewhere. It moves." in text
    assert "SLEEP Below it." in text
    assert "MOVE inline" not in text
    assert "after rest" not in text
    dom = app.env.get_domain("mat")
    types = {name: objtype for name, _, objtype, *_ in dom.get_objects()}
    assert types["+zoo/Animal.m.speak"] == "method"
    assert types["+zoo/Animal.m.Legs"] == "attribute"


def test_api_check_skips_abstract_methods(make_app, tmp_path):
    app = build(make_app, tmp_path, "matlab-api-check")
    data = json.loads((app.outdir / "api-check.json").read_text(encoding="utf-8"))
    refs = {f["reference"] for f in data["findings"]}
    assert not any(ref.endswith((".speak", ".move", ".sleep")) for ref in refs)
    # the abstract property is public API and has help
    assert data["summary"]["checked"]["property"] == 6
