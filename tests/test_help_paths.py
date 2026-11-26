"""Relative paths in help text resolve from the folder of the code file:
images, figures, downloads, ``literalinclude``, ``include`` and hyperlinks.
"""

from pathlib import Path
from typing import Any, cast

from sphinx.util import console
from test_sidecars import png, write

from sphinxcontrib import mat_sidecars

strip_escape_sequences = cast(Any, console).strip_escape_sequences

CONF = (
    'extensions = ["sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "../src"\n'
    'matlab_src_sidecar_suffixes = [".rst"]\n'
    "nitpicky = True\n"
)
SCALE = """\
function y = scale(x)
% SCALE Scale a value.
%
% .. image:: img/plot.png
%
% .. figure:: img/missing.png
%
%    A missing figure.
%
% A download: :download:`the data <data/values.csv>`.
%
% .. literalinclude:: data/snippet.txt
%
% .. include:: data/part.txt
%
% Links: `the notes <notes.rst>`_, `the helper <helper.m>`_,
% `the values <data/values.csv>`_, `gone <gone.pdf>`_,
% `a site <https://example.com>`_, `MATLAB <matlab:doc scale>`_,
% `an absolute path </abs.txt>`_ and `a section <#scale>`_.
y = x;
end
"""
FILES = {
    "src/+demo/scale.m": SCALE,
    "src/+demo/helper.m": "function helper\n% HELPER Help.\nend\n",
    "src/+demo/notes.rst": "Notes\n=====\n\nThe notes.\n",
    "src/+demo/img/plot.png": png(),
    "src/+demo/data/values.csv": "1,2\n",
    "src/+demo/data/snippet.txt": "SNIPPET LINE\n",
    "src/+demo/data/part.txt": "Included text from part.\n",
    "docs/conf.py": CONF,
    "docs/index.rst": "Index\n=====\n\n.. toctree::\n\n   api/demo\n   api/notes\n",
    "docs/api/demo.rst": (
        "Demo\n====\n\n.. mat:autofunction:: +demo/scale.m\n\n"
        ".. mat:autofunction:: +demo/helper.m\n"
    ),
    "docs/api/notes.rst": ".. mat:autosidecar:: +demo/notes.rst\n",
}


def build(make_app, root):
    app = make_app("html", srcdir=root / "docs")
    app.build()
    text = (Path(app.outdir) / "api" / "demo.html").read_text(encoding="utf-8")
    found = strip_escape_sequences(app.warning.getvalue())
    return app, text, [line for line in found.splitlines() if "WARNING" in line]


def test_help_paths_are_relative_to_the_code_file(make_app, tmp_path):
    write(tmp_path, FILES)
    app, page, found = build(make_app, tmp_path)

    assert len(found) == 1, found
    assert "image file not readable" in found[0]
    assert "+demo/img/missing.png" in found[0]
    outdir = Path(app.outdir)
    assert (outdir / "_images" / "plot.png").is_file()
    assert 'src="../_images/plot.png"' in page
    assert ">SNIPPET<" in page
    assert "Included text from part." in page

    downloads = sorted(p.name for p in (outdir / "_downloads").rglob("*.*"))
    assert downloads == ["values.csv"]
    assert page.count("_downloads/") == 2
    assert 'href="notes.html"' in page
    assert ">the notes<" in page
    assert 'href="#mat-+demo/helper.m"' in page
    assert ">the helper<" in page
    # Left as they are (docutils drops the space of an embedded URI).
    for target in ("gone.pdf", "https://example.com", "matlab:docscale", "/abs.txt"):
        assert f'href="{target}"' in page
    assert 'href="#scale"' in page


def test_help_uri_links_are_not_dependencies(make_app, tmp_path):
    files = {
        **FILES,
        "src/+demo/scale.m": (
            "function scale\n% SCALE Scale.\n%\n"
            "% Mail someone@example.org or `MATLAB <matlab:doc>`_.\nend\n"
        ),
    }
    write(tmp_path, files)
    app, page, _ = build(make_app, tmp_path)
    assert 'href="mailto:' in page
    deps = {str(p) for paths in app.env.dependencies.values() for p in paths}
    assert not any("mailto:" in p or "matlab:" in p for p in deps), deps
    # Nothing changed: the second build reads no document again.
    app = make_app("html", srcdir=tmp_path / "docs")
    app.build()
    assert "0 added, 0 changed, 0 removed" in strip_escape_sequences(
        app.status.getvalue()
    )


def test_help_include_is_not_read_beside_the_page(make_app, tmp_path):
    files = {**FILES, "docs/api/data/snippet.txt": "PAGE SNIPPET\n"}
    del files["src/+demo/data/snippet.txt"]
    write(tmp_path, files)
    _, page, found = build(make_app, tmp_path)
    assert any("snippet.txt" in line and "+demo" in line for line in found), found
    assert "PAGE" not in page


def test_page_content_stays_relative_to_the_page(make_app, tmp_path):
    files = {
        **FILES,
        "docs/api/page.txt": "PAGE TEXT\n",
        "docs/api/demo.rst": (
            "Demo\n====\n\n.. mat:autofunction:: +demo/helper.m\n\n"
            "   .. literalinclude:: page.txt\n\n"
            "   .. image:: page.png\n\n"
            "   `page text <page.txt>`_\n"
        ),
        "docs/api/page.png": png(),
    }
    write(tmp_path, files)
    _, page, found = build(make_app, tmp_path)
    assert found == []
    assert ">PAGE<" in page
    assert 'src="../_images/page.png"' in page
    assert 'href="page.txt"' in page


def test_help_paths_on_another_drive_are_left_alone(make_app, tmp_path, monkeypatch):
    monkeypatch.setattr(mat_sidecars._Relative, "source_path", lambda *_: None)
    write(tmp_path, FILES)
    _, page, _ = build(make_app, tmp_path)
    assert "_downloads/" not in page
    assert 'href="data/values.csv"' in page
