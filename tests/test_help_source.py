"""A warning about help text names the file and the line of the help in it:
``<file>:docstring of <reference>:<line>`` (a Simulink file has no text lines,
so it is the line within the description); a sidecar doc is its own file.
"""

import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from sphinx.util import console

from sphinxcontrib import mat_sidecars
from sphinxcontrib.mat_types import MatObject

strip_escape_sequences = cast(Any, console).strip_escape_sequences

SLX = Path(__file__).parent / "simulink" / "fixtures" / "R2026b" / "slx"
CONF = (
    'extensions = ["sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "src"\n'
    "nitpicky = True\n"
)
DEMO = """\
function out = demo(x)
% DEMO Short summary line.
%
% Calls :mat:func:`noDemo` here.
arguments
    x (1,1) double % the input value
end
out = x;
end
"""
LEAD = """\
% LEAD Help before the function.
%
% Calls :mat:func:`noLead` here.
function lead
end
"""
SHAPE = """\
classdef Shape
    % SHAPE A shape.
    %
    % Calls :mat:func:`noClass` here.
    properties
        % The width.
        %
        % Calls :mat:func:`noProp` here.
        Width = 1
    end
    methods
        function obj = area(obj)
            % AREA Compute.
            %
            % Calls :mat:func:`noMethod` here.
        end
    end
end
"""
MODEL = """\
Model {
  Name "m"
  Description "Intro.\\n\\nCalls :mat:func:`noModel` here."
  System {
    Name "m"
  }
}
"""


def build(make_app, tmp_path, files, index, conf=""):
    for name, content in files.items():
        target = tmp_path / "src" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (tmp_path / "conf.py").write_text(CONF + conf)
    (tmp_path / "index.rst").write_text(f"Index\n=====\n\n{index}")
    app = make_app(srcdir=tmp_path, freshenv=True)
    app.build(force_all=True)
    app.cleanup()
    found = strip_escape_sequences(app.warning.getvalue())
    return [line for line in found.splitlines() if "WARNING" in line]


def missing(src, location, name):
    return f"{src}:{location}: WARNING: mat:func reference target not found: {name}"


def test_function_help_is_at_its_file_line(make_app, tmp_path):
    index = ".. mat:autofunction:: demo\n\n.. mat:autofunction:: lead\n"
    found = build(make_app, tmp_path, {"demo.m": DEMO, "lead.m": LEAD}, index)
    src = tmp_path / "src"
    assert found[0].startswith(
        missing(src / "demo.m", "docstring of demo.m:4", "noDemo")
    )
    # help before the function line
    assert found[1].startswith(
        missing(src / "lead.m", "docstring of lead.m:3", "noLead")
    )
    assert len(found) == 2, found


def test_class_member_help_is_at_its_file_line(make_app, tmp_path):
    index = ".. mat:autoclass:: Shape\n   :members:\n"
    found = build(make_app, tmp_path, {"Shape.m": SHAPE}, index)
    shape = tmp_path / "src" / "Shape.m"
    assert [line.split(": WARNING")[0] for line in found] == [
        f"{shape}:docstring of Shape.m:4",
        f"{shape}:docstring of Shape.m.Width:8",
        f"{shape}:docstring of Shape.m.area:15",
    ]


def test_help_of_a_method_file_is_in_that_file(make_app, tmp_path):
    # A method of a class folder with a file of its own: its help is there.
    files = {
        "@Cf/Cf.m": "classdef Cf\n% CF help\nmethods\n    meth(obj)\nend\nend\n",
        "@Cf/meth.m": (
            "function meth(obj)\n% METH help\n%\n% More.\n%\n"
            "% Calls :mat:func:`noMeth` and :mat:func:`near` here.\n"
            "%\n% .. image:: pic.png\nend\n"
        ),
        "@Cf/private/near.m": "function near\n% NEAR help\nend\n",
        "@Cf/pic.png": "",
    }
    index = (
        ".. mat:autoclass:: Cf\n   :members:\n\n"
        ".. mat:autofunction:: @Cf/private/near.m\n"
    )
    found = build(make_app, tmp_path, files, index)
    meth = tmp_path / "src" / "@Cf" / "meth.m"
    # Sphinx normalizes the whole location as a path: "\\" on Windows, also in
    # the reference.
    assert (
        found[0]
        .replace("\\", "/")
        .startswith(missing(meth.as_posix(), "docstring of @Cf/Cf.m.meth:6", "noMeth"))
    )
    # names and paths in it are still found from the class folder
    assert len(found) == 1, found
    html = (tmp_path / "_build" / "html" / "index.html").read_text(encoding="utf-8")
    assert 'src="_images/pic.png"' in html


def test_simulink_help_is_at_its_line_in_the_description(make_app, tmp_path):
    index = ".. mat:autosimulink_model:: m\n"
    found = build(make_app, tmp_path, {"m.mdl": MODEL}, index)
    src = tmp_path / "src" / "m.mdl"
    assert found[0].startswith(missing(src, "docstring of m.mdl:3", "noModel"))
    assert len(found) == 1, found


def test_sidecar_help_is_at_its_file_line(make_app, tmp_path):
    pytest.importorskip("myst_parser")
    (tmp_path / "src").mkdir()
    shutil.copyfile(SLX / "probeModel.slx", tmp_path / "src" / "probeModel.slx")
    shutil.copyfile(SLX / "probeSub.slx", tmp_path / "src" / "probeSub.slx")
    files = {
        "probeModel.md": "# Title\n\nText {mat:func}`noMd` here.\n",
        "probeSub.rst": "Title\n=====\n\nText :mat:func:`noRst` here.\n",
    }
    index = (
        ".. mat:autosimulink_model:: probeModel\n\n"
        ".. mat:autosimulink_subsystem_reference:: probeSub\n"
    )
    found = build(
        make_app,
        tmp_path,
        files,
        index,
        'extensions = ["sphinxcontrib.matlab", "myst_parser"]\n',
    )
    src = tmp_path / "src"
    assert [line.split(": WARNING")[0] for line in found] == [
        f"{src / 'probeModel.md'}:3",
        f"{src / 'probeSub.rst'}:4",
    ], found


# --- lines that processing adds ------------------------------------------------

HANDLERS = """\
def setup(app):
    app.connect("autodoc-process-docstring", process)


def process(app, what, name, obj, options, lines):
    if MODE == "replace":
        lines[:] = [line.replace("here", "there") for line in lines]
    else:
        lines.insert(0, "Inserted.")
        lines.insert(1, "")
"""


@pytest.mark.parametrize("mode", ["replace", "insert"])
def test_processed_help_keeps_its_lines(make_app, tmp_path, mode):
    """Lines a handler changes or adds leave the others at their file lines."""
    index = ".. mat:autofunction:: demo\n"
    found = build(
        make_app, tmp_path, {"demo.m": DEMO}, index, f'MODE = "{mode}"\n' + HANDLERS
    )
    src = tmp_path / "src" / "demo.m"
    assert found[0].startswith(missing(src, "docstring of demo.m:4", "noDemo"))


NAPOLEON = """\
function napo(x)
% NAPO Summary.
%
% Args:
%     x: the input,
%         on two lines
%
% Calls :mat:func:`noNapo` here.
end
"""


def test_napoleon_sections_keep_the_lines_after_them(make_app, tmp_path):
    index = ".. mat:autofunction:: napo\n"
    found = build(
        make_app,
        tmp_path,
        {"napo.m": NAPOLEON},
        index,
        'extensions = ["sphinxcontrib.matlab", "sphinx.ext.napoleon"]\n',
    )
    src = tmp_path / "src" / "napo.m"
    assert found[0].startswith(missing(src, "docstring of napo.m:8", "noNapo"))


def test_parsed_help_knows_its_file_line(tmp_path):
    path = tmp_path / "Mixed.m"
    path.write_text(
        "classdef Mixed\n"  # 1
        "    % MIXED Class help.\n"  # 2
        "    properties\n"  # 3
        "        a % inline help\n"  # 4
        "        % Help above b.\n"  # 5
        "        b\n"  # 6
        "    end\n"  # 7
        "    events\n"  # 8
        "        Changed % event help\n"  # 9
        "    end\n"  # 10
        "    enumeration\n"  # 11
        "        Red (1) % red help\n"  # 12
        "    end\n"  # 13
        "    methods\n"  # 14
        "        function f(obj)\n"  # 15
        "            % F help.\n"  # 16
        "        end\n"  # 17
        "    end\n"  # 18
        "end\n",
        encoding="utf-8",
    )
    obj = cast(Any, MatObject.parse_mfile(path, "Mixed", "x"))
    assert obj.docstring_line == 2
    assert {n: p["docstring_line"] for n, p in obj.properties.items()} == {
        "a": 4,
        "b": 5,
    }
    assert obj.events["Changed"]["docstring_line"] == 9
    assert obj.enumerations["Red"]["docstring_line"] == 12
    assert obj.methods["f"].docstring_line == 16


def test_help_source_form():
    assert mat_sidecars.help_source("f.m", "/p/f.m") == "/p/f.m:docstring of f.m"
    assert mat_sidecars.help_source("f.m") == "docstring of f.m"
    for source in ("/p/f.m:docstring of f.m", "C:\\p\\f.m:docstring of f.m"):
        assert mat_sidecars.help_reference(source) == "f.m"
    assert mat_sidecars.help_reference("docstring of f.m") == "f.m"
    assert mat_sidecars.help_reference("/p/index.rst") is None
    assert mat_sidecars.help_reference(None) is None
