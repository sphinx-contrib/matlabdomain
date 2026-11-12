"""File-type handler registry (plan.md Section 2.6)."""

import subprocess
import sys

import pytest

from sphinxcontrib import mat_handlers, mat_naming
from sphinxcontrib.mat_types import MatApplication


def test_registered_handlers(tmp_path):
    assert mat_handlers.extensions() == (".m", ".mlapp", ".slx", ".mdl")
    assert mat_handlers.block_extensions() == (".slx", ".mdl")
    (tmp_path / "f.m").write_text("function f\nend\n")
    (tmp_path / "app.mlapp").write_bytes(b"")
    (tmp_path / "x.txt").write_text("")
    (tmp_path / "dir.m").mkdir()

    m = mat_handlers.handler_for(tmp_path / "f.m")
    assert isinstance(m, mat_handlers.MFileHandler)
    assert m.classify(tmp_path / "f.m") == "function"
    assert m.classify("s.m", "x = 1;") == "script"
    mlapp = mat_handlers.handler_for(tmp_path / "app.mlapp")
    assert isinstance(mlapp, mat_handlers.MlappHandler)
    assert mlapp.classify(tmp_path / "app.mlapp") == "application"
    assert mlapp.classify(tmp_path / "missing.mlapp") == "unknown"
    for missing in ("missing.m", "x.txt", "dir.m", "F.M"):
        assert mat_handlers.handler_for(tmp_path / missing) is None


def test_document_directives():
    m, mlapp, slx, *_ = mat_handlers.handlers()
    assert [m.document(k) for k in ("script", "function", "class")] == [
        "mat:autoscript",
        "mat:autofunction",
        "mat:autoclass",
    ]
    assert mlapp.document("application") == "mat:autoapplication"
    assert m.document("application") is None
    assert [slx.document(k) for k in ("model", "library", "subsystem")] == [
        "mat:autosimulink_model",
        "mat:autosimulink_library",
        "mat:autosimulink_subsystem_reference",
    ]
    assert slx.document("function") is None


def test_extension_has_one_handler():
    with pytest.raises(ValueError, match=r"\.m already has a handler"):
        mat_handlers.register(mat_handlers.MFileHandler())


def test_base_handler_needs_classify_and_parse(tmp_path):
    handler = mat_handlers.Handler()
    with pytest.raises(NotImplementedError):
        handler.read(tmp_path / "x.ext")
    with pytest.raises(NotImplementedError):
        handler.parse(tmp_path / "x.ext", "x", "./")


def test_naming_does_not_import_the_parser():
    code = (
        "import sys, sphinxcontrib.mat_naming\n"
        "print(sorted(m for m in sys.modules if m.startswith('sphinxcontrib.')))"
    )
    out = subprocess.run(
        [sys.executable, "-X", "gil=1", "-c", code],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "mat_tree_sitter_parser" not in out
    assert "mat_types" not in out
    assert "mat_handlers" in out


class SimscapeHandler(mat_handlers.Handler):
    """A stand-in for a future ``.ssc`` handler."""

    extension = ".ssc"
    kinds = ("component",)

    def classify(self, path, text=None):
        return "component"

    def parse(self, path, stem, folder, encoding=None):
        return MatApplication(stem, folder, f"Simscape component {stem}.")


@pytest.fixture
def ssc_registered(monkeypatch):
    monkeypatch.setattr(mat_handlers, "_HANDLERS", dict(mat_handlers._HANDLERS))
    mat_handlers.register(SimscapeHandler())


def test_new_handler_is_additive(make_app, tmp_path, ssc_registered):
    assert mat_naming.parse_reference("lib/+pkg/valve.ssc.p") == (
        "lib/+pkg/valve.ssc",
        ["p"],
    )
    (tmp_path / "+pkg").mkdir()
    (tmp_path / "+pkg" / "valve.ssc").write_text("component valve\nend\n")
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "."\n'
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n.. mat:autoapplication:: pkg.valve\n"
    )
    app = make_app(srcdir=tmp_path)
    app.build()

    (record,) = app.env.domaindata["mat"]["index"].values()
    assert (record["reference"], record["type"], record["matlab_name"]) == (
        "+pkg/valve.ssc",
        "component",
        "pkg.valve",
    )
    html = (app.outdir / "index.html").read_text()
    assert 'id="mat-+pkg/valve.ssc"' in html
    assert "Simscape component valve." in html
    assert "WARNING" not in app.warning.getvalue()
