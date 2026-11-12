"""Every builder finishes a small project without an exception or a warning,
and the HTML-format builders leave redirects that lead somewhere (G4-T10).

The project sets what a builder needs to be quiet (``version``, ``copyright``,
``man_pages``), so a warning here is the extension's.
"""

import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from sphinx.util.inventory import InventoryFile

SLX = Path(__file__).parent / "simulink" / "fixtures" / "R2026b" / "slx"
BUILDERS = (
    "html",
    "dirhtml",
    "singlehtml",
    "epub",
    "latex",
    "text",
    "man",
    "xml",
    "json",
    "pickle",
    "linkcheck",
    "matlab-api-check",
)
CONF = """\
extensions = ["sphinxcontrib.matlab"]
project = "tiny"
author = "me"
version = "1"
release = "1"
copyright = "me"
matlab_src_code_project_root = "src"
primary_domain = "mat"
nitpicky = True
man_pages = [("index", "tiny", "tiny", ["me"], 1)]
linkcheck_ignore = [r"https?://.*"]
"""
FUNCTION = """\
function out = scale(x)
% SCALE Multiply a value by two.
%
% Inputs:
%   x - the value
%
% Outputs:
%   out - twice x
%
% Example:
%   scale(2)
out = 2 * x;
end
"""
CLASS = """\
classdef Box
% BOX A box.
%
% Example:
%   b = Box(1);
    properties
        % Side Length of a side.
        Side = 1
    end
    methods
        function obj = Box(side)
        % BOX Make a box.
        %
        % Inputs:
        %   side - the side
            obj.Side = side;
        end
    end
end
"""
INDEX = """\
Tiny
====

.. mat:autofunction:: scale

.. mat:autoclass:: Box
   :members:

.. mat:autosimulink_model:: probeModel
"""


def tiny_project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "scale.m").write_text(FUNCTION)
    (tmp_path / "src" / "Box.m").write_text(CLASS)
    shutil.copyfile(SLX / "probeModel.slx", tmp_path / "src" / "probeModel.slx")
    (tmp_path / "conf.py").write_text(CONF)
    (tmp_path / "index.rst").write_text(INDEX)
    return tmp_path


def build(make_app, srcdir, builder):
    app = make_app(buildername=builder, srcdir=srcdir)
    app.build()
    warnings = app.warning.getvalue()  # type: ignore[attr-defined]
    status = app.statuscode
    app.cleanup()
    return app, status, warnings


@pytest.mark.parametrize("builder", BUILDERS)
def test_builder_finishes_a_tiny_project_without_warning(make_app, tmp_path, builder):
    _, status, warnings = build(make_app, tiny_project(tmp_path), builder)
    assert status == 0
    assert warnings == ""
    assert "Traceback" not in warnings


@pytest.mark.parametrize("builder", ["json", "pickle"])
def test_builders_without_html_pages_get_no_stable_addresses(
    make_app, tmp_path, builder
):
    """Stable addresses are for builders that write ``.html`` pages (G4-F9)."""
    app, status, warnings = build(make_app, tiny_project(tmp_path), builder)
    out = Path(app.outdir)
    suffix = {"json": ".fjson", "pickle": ".fpickle"}[builder]
    assert status == 0
    assert warnings == ""
    assert not (out / "mat").exists()
    assert not (out / "404.html").exists()
    assert not (out / "_static" / "mat_urls.js").exists()
    with (out / "objects.inv").open("rb") as f:
        inventory = InventoryFile.load(cast(Any, f), "", lambda _base, uri: uri)
    entries = inventory["mat:function"]
    assert entries
    for _, _, uri, _ in entries.values():
        assert "mat/" not in uri
        # The one page is the root document, whose address is the page itself.
        assert uri.startswith("#mat-"), uri
    assert (out / f"index{suffix}").is_file()
