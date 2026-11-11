"""Every builder finishes a small project without an exception or a warning,
and the HTML-format builders leave redirects that lead somewhere (G4-T10).

The project sets what a builder needs to be quiet (``version``, ``copyright``,
``man_pages``), so a warning here is the extension's.
"""

import re
import shutil
from pathlib import Path

import pytest

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


@pytest.mark.xfail(
    strict=True,
    reason="G4-T10: json writes mat/ redirects to <page>/ but the page is <page>.fjson",
)
def test_json_redirects_point_at_files_that_exist(make_app, tmp_path):
    app, _, _ = build(make_app, tiny_project(tmp_path), "json")
    out = Path(app.outdir)
    redirects = [
        *(out / "mat" / "name").glob("*.html"),
        *(out / "mat" / "ref").glob("*.html"),
    ]
    assert redirects
    for redirect in redirects:
        url = re.search(r'url=([^"#]*)', redirect.read_text(encoding="utf-8")).group(1)  # type: ignore[union-attr]
        target = (redirect.parent / url).resolve()
        if url.endswith("/"):
            target = target / "index.html"
        assert target.is_file(), (redirect.name, url)
